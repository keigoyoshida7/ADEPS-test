"""CPU-only protocol/API checks; no Max process, audio or real UDP required."""
import http.client
import json
import threading
import unittest
from unittest.mock import patch

import server


BANK='a'*64
OTHER_BANK='b'*64


class FakeSocket:
    def __init__(self):
        self.sent=[];self.ready=True;self.selected='reference';self.bank=BANK
        self.response='normal';self.bridge=None
    def bind(self,address):self.bound=address
    def settimeout(self,value):self.timeout=value
    def close(self):self.closed=True
    def sendto(self,packet,address):
        name,args=server.comparison_osc_read(packet)
        self.sent.append((name,args,address))
        if self.response=='silent':return
        if name.endswith('/ping'):
            seq=args[0]+1 if self.response=='wrong_sequence' else args[0]
            reply=server.comparison_osc_message('/adeps-compare/status',seq,int(self.ready),self.selected,self.bank)
        elif name.endswith('/select'):
            if self.response=='bank_changed':self.bank=OTHER_BANK
            if self.bank!=args[1]:reply=server.comparison_osc_message('/adeps-compare/error','select','bank_changed')
            elif self.response=='wrong_method':reply=server.comparison_osc_message('/adeps-compare/ack','select','linear_default',self.bank)
            elif self.response=='wrong_hash':reply=server.comparison_osc_message('/adeps-compare/ack','select',args[0],OTHER_BANK)
            else:
                self.selected=args[0]
                reply=server.comparison_osc_message('/adeps-compare/ack','select',self.selected,self.bank)
        else:reply=server.comparison_osc_message('/adeps-compare/ack','mute','',self.bank)
        self.bridge.accept_packet(reply,('127.0.0.1',9999 if self.response=='wrong_port' else 8874))


class ComparisonBridgeTests(unittest.TestCase):
    def setUp(self):
        self.now=10.;self.socket=FakeSocket()
        self.bridge=server.MaxComparisonBridge(sock=self.socket,start_receiver=False,clock=lambda:self.now,reply_timeout=.002)
        self.socket.bridge=self.bridge
    def tearDown(self):self.bridge.close()

    def test_ping_requires_nonce_and_loopback_source_then_expires(self):
        self.assertEqual(self.socket.bound,('127.0.0.1',8875))
        self.assertFalse(self.bridge.status()['max_reply'])
        for invalid in ('wrong_sequence','wrong_port','silent'):
            self.socket.response=invalid
            result=self.bridge.command('ping')
            self.assertEqual(result['outcome'],'timeout')
            self.assertFalse(result['max_reply'])
            self.assertFalse(result['ready'])
        self.socket.response='normal'
        result=self.bridge.command('ping')
        self.assertTrue(result['acknowledged']);self.assertTrue(result['ready'])
        self.assertEqual(result['selected_method'],'reference')
        self.assertEqual(result['input_sha256'],BANK)
        self.now+=8
        result=self.bridge.status()
        self.assertFalse(result['max_reply']);self.assertFalse(result['ready'])
        self.assertEqual(result['selected_method'],'');self.assertEqual(result['input_sha256'],'')

    def test_select_rechecks_ready_and_hash_and_sends_hash_to_controller(self):
        result=self.bridge.command('select','plus',BANK)
        self.assertTrue(result['acknowledged'])
        self.assertEqual(result['selected_method'],'plus')
        self.assertEqual([row[0] for row in self.socket.sent],['/adeps-compare/ping','/adeps-compare/select'])
        self.assertEqual(self.socket.sent[-1][1],['plus',BANK])
        self.assertTrue(all(row[2]==('127.0.0.1',8874) for row in self.socket.sent))
        self.socket.bank=OTHER_BANK;self.socket.sent=[]
        with self.assertRaisesRegex(ValueError,'does not match'):
            self.bridge.command('select','reference',BANK)
        self.assertEqual(len(self.socket.sent),1)
        self.socket.ready=False;self.socket.sent=[]
        with self.assertRaisesRegex(ValueError,'not ready'):
            self.bridge.command('select','reference',OTHER_BANK)
        self.assertEqual(len(self.socket.sent),1)

    def test_wrong_selection_ack_never_becomes_confirmed_selection(self):
        for failure in ('wrong_method','wrong_hash'):
            self.socket.response=failure
            result=self.bridge.command('select','plus',BANK)
            self.assertFalse(result['acknowledged'])
            self.assertEqual(result['outcome'],'timeout')
            self.assertEqual(result['selected_method'],'reference')
        self.assertFalse(self.bridge.accept_packet(server.comparison_osc_message('/adeps-compare/ack','select','plus',BANK),('127.0.0.1',8874)))

    def test_controller_bank_race_error_is_preserved(self):
        self.socket.response='bank_changed'
        result=self.bridge.command('select','plus',BANK)
        self.assertFalse(result['acknowledged'])
        self.assertEqual(result['outcome'],'remote_error')
        self.assertEqual(result['error'],'bank_changed')
        self.assertEqual(result['selected_method'],'')
        self.assertEqual(result['input_sha256'],'')
        self.assertFalse(result['ready'])

    def test_mute_is_argumentless_and_never_reports_audible_silence(self):
        result=self.bridge.command('mute')
        self.assertTrue(result['acknowledged'])
        self.assertEqual(self.socket.sent[-1][:2],('/adeps-compare/mute',[]))
        self.assertNotIn('muted',result)
        self.assertEqual(result['audio_output'],'manual_in_Max_unverified')

    def test_whitelist_and_input_checks_precede_udp_side_effects(self):
        for command in ('play','unmute','gain','start',True,None):
            with self.assertRaises(ValueError):self.bridge.command(command)
        for method in ('../../file','/adeps-test/select','',3,None):
            with self.assertRaises(ValueError):self.bridge.command('select',method,BANK)
        for digest in (None,'A'*64,'a'*63,3):
            with self.assertRaises(ValueError):self.bridge.command('select','plus',digest)
        with self.assertRaises(ValueError):self.bridge.command('ping','plus',BANK)
        with self.assertRaises(ValueError):self.bridge.command('mute',expected_input_sha256=BANK)
        self.assertEqual(self.socket.sent,[])
        self.assertEqual(len(server.COMPARISON_METHODS),10)

    def test_parser_rejects_wrong_types_trailing_bytes_and_nonzero_padding(self):
        valid=server.comparison_osc_message('/adeps-compare/status',4,1,'plus',BANK)
        self.assertEqual(server.comparison_osc_read(valid)[1],[4,1,'plus',BANK])
        for packet in (valid+b'\0\0\0\0',b'#bundle\0',b'/adeps-compare/ping\0xx',b'',b'x'*4097):
            with self.assertRaises((ValueError,UnicodeError)):
                server.comparison_osc_read(packet)
        with self.assertRaises(ValueError):server.comparison_osc_message('/adeps-compare/select','x\0y')
        with self.assertRaises(ValueError):server.comparison_osc_message('/adeps-compare/select',True)


class ComparisonHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join()
    def request(self,method='GET',path='/api/max-compare',data=None,origin='http://127.0.0.1:5178'):
        connection=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=2)
        headers={'Origin':origin}
        if data is not None:headers['Content-Type']='application/json'
        connection.request(method,path,body=json.dumps(data) if data is not None else None,headers=headers)
        response=connection.getresponse();body=json.loads(response.read());status=response.status
        connection.close();return status,body

    def test_http_get_and_commands_have_honest_ack_status_codes(self):
        sock=FakeSocket();bridge=server.MaxComparisonBridge(sock=sock,start_receiver=False,reply_timeout=.002);sock.bridge=bridge
        try:
            with patch.object(server,'comparison_bridge',bridge):
                code,body=self.request();self.assertEqual(code,200);self.assertFalse(body['max_reply'])
                code,body=self.request('POST',data={'command':'select','method':'plus','expected_input_sha256':BANK})
                self.assertEqual(code,200);self.assertTrue(body['acknowledged']);self.assertEqual(body['selected_method'],'plus')
                sock.response='silent'
                code,body=self.request('POST',data={'command':'ping'})
                self.assertEqual(code,504);self.assertFalse(body['acknowledged'])
                sock.response='bank_changed'
                code,body=self.request('POST',data={'command':'select','method':'reference','expected_input_sha256':BANK})
                self.assertEqual(code,409);self.assertEqual(body['error'],'bank_changed')
        finally:bridge.close()

    def test_unknown_fields_nonlocal_origin_and_missing_bridge_cannot_send(self):
        sock=FakeSocket();bridge=server.MaxComparisonBridge(sock=sock,start_receiver=False,reply_timeout=.002);sock.bridge=bridge
        try:
            with patch.object(server,'comparison_bridge',bridge):
                code,_=self.request('POST',data={'command':'mute','gain':1});self.assertEqual(code,400)
                code,_=self.request('POST',data={'command':'mute'},origin='https://keigoyoshida7.github.io');self.assertEqual(code,400)
                self.assertEqual(sock.sent,[])
            with patch.object(server,'comparison_bridge',None):
                self.assertEqual(self.request()[0],503)
                self.assertEqual(self.request('POST',data={'command':'ping'})[0],503)
        finally:bridge.close()

    def test_legacy_max_endpoint_is_unchanged(self):
        from unittest.mock import Mock
        old=Mock();old.command.return_value={'legacy':True}
        with patch.object(server,'bridge',old):
            code,body=self.request('POST','/api/max',{'command':'select','channel':3})
            self.assertEqual((code,body),(200,{'legacy':True}))
            old.command.assert_called_once_with('select',3)


if __name__=='__main__':unittest.main()
