"""Loopback-only scientific test API; no Dante/AFC writes or audio output."""
import json,time,struct,socket,threading,traceback,io,base64
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse
from numerics import run_demo,to_jsonable
from capture import run_capture
from measurements import analyze_bundle,sample_zip

def osc_string(value):
    b=value.encode()+b'\0';return b+b'\0'*((-len(b))%4)
def osc_message(address,value):return osc_string(address)+osc_string(',i')+struct.pack('>i',value)
def osc_read(packet):
    pos=0
    def string():
        nonlocal pos
        end=packet.index(b'\0',pos);v=packet[pos:end].decode();pos=(end+4)&~3;return v
    address=string();types=string()
    if types!=',i' or pos+4>len(packet):raise ValueError('unsupported OSC')
    return address,struct.unpack('>i',packet[pos:pos+4])[0]

class MaxBridge:
    def __init__(self):
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.sock.bind(('127.0.0.1',8873));self.last_reply=0;self.pending={};self.sequence=0;self.selected=None
        threading.Thread(target=self.receive,daemon=True).start()
    def receive(self):
        while True:
            packet,source=self.sock.recvfrom(4096)
            try:
                address,seq=osc_read(packet)
                if source[0]=='127.0.0.1' and source[1]==8872 and address=='/adeps-test/pong' and seq in self.pending and time.monotonic()-self.pending.pop(seq)<7:self.last_reply=time.monotonic()
            except (ValueError,UnicodeError,struct.error):pass
    def status(self):
        age=time.monotonic()-self.last_reply if self.last_reply else None
        return {'service':'adeps-test','api':'connected','max_reply':age is not None and age<7,'reply_age_seconds':round(age,1) if age is not None else None,'selected_channel':self.selected,'dante':'unverified','audio_output':'controlled_manually_in_Max','destination':'127.0.0.1:8872','reply_port':8873}
    def command(self,kind,channel=None):
        if kind=='ping':
            self.sequence=(self.sequence+1)%2147483647;self.pending={self.sequence:time.monotonic()};msg=osc_message('/adeps-test/ping',self.sequence)
        elif kind=='select':
            if type(channel)!=int or not 1<=channel<=12:raise ValueError('channelは1〜12です。')
            self.selected=channel;msg=osc_message('/adeps-test/select',channel)
        elif kind=='mute':msg=osc_string('/adeps-test/mute')+osc_string(',')
        else:raise ValueError('未対応のコマンドです。')
        self.sock.sendto(msg,('127.0.0.1',8872));return self.status()

bridge=None

# Separate, loopback-only transport for the prepared ten-file FOA comparison
# bank. It cannot start playback, unmute, set gain, or choose a network target.
COMPARISON_METHODS=frozenset(('reference','linear_default','linear_tuned','linear_noise',
    'adeps_current','adeps_tuned','spatial_only','consistency_only','plus','plus_no_denoiser'))

def comparison_osc_message(address,*arguments):
    tags=',';payload=b''
    for value in arguments:
        if type(value)==int:
            tags+='i';payload+=struct.pack('>i',value)
        elif isinstance(value,str) and '\0' not in value and len(value.encode('utf-8'))<=256:
            tags+='s';payload+=osc_string(value)
        else:raise ValueError('Unsupported comparison OSC argument.')
    return osc_string(address)+osc_string(tags)+payload

def comparison_osc_read(packet):
    if not isinstance(packet,bytes) or len(packet)>4096:raise ValueError('Invalid OSC packet size.')
    position=0
    def string():
        nonlocal position
        end=packet.index(b'\0',position);padded=(end+4)&~3
        if padded>len(packet) or any(packet[end:padded]):raise ValueError('Invalid OSC padding.')
        value=packet[position:end].decode('utf-8');position=padded
        if len(value.encode('utf-8'))>256:raise ValueError('OSC string too long.')
        return value
    address=string();tags=string()
    if not address.startswith('/adeps-compare/') or not tags.startswith(',') or len(tags)>8:
        raise ValueError('Unsupported comparison OSC message.')
    arguments=[]
    for tag in tags[1:]:
        if tag=='s':arguments.append(string())
        elif tag=='i' and position+4<=len(packet):
            arguments.append(struct.unpack('>i',packet[position:position+4])[0]);position+=4
        else:raise ValueError('Unsupported comparison OSC type.')
    if position!=len(packet):raise ValueError('Trailing comparison OSC data.')
    return address,arguments

def comparison_hash(value,allow_empty=False):
    return isinstance(value,str) and ((allow_empty and value=='') or
        (len(value)==64 and all(c in '0123456789abcdef' for c in value)))

class MaxComparisonBridge:
    """Report only nonce-matched status and command-matched Node acknowledgments.

    ready means all ten files were verified and their Max buffers acknowledged.
    It does not establish DSP, gain, output routing, or audible playback state.
    """
    def __init__(self,*,sock=None,start_receiver=True,clock=time.monotonic,reply_timeout=.8):
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM) if sock is None else sock
        self.sock.bind(('127.0.0.1',8875));self.sock.settimeout(.5)
        self.clock=clock;self.reply_timeout=reply_timeout
        self.condition=threading.Condition(threading.RLock());self.command_lock=threading.Lock()
        self.sequence=0;self.pending=None;self.last_reply=None;self.last_status=None
        self.ready=False;self.selected='';self.input_sha256='';self.closed=False
        if start_receiver:threading.Thread(target=self.receive,daemon=True).start()
    def close(self):
        self.closed=True;self.sock.close()
    def receive(self):
        while not self.closed:
            try:packet,source=self.sock.recvfrom(4096)
            except socket.timeout:continue
            except OSError:return
            self.accept_packet(packet,source)
    def accept_packet(self,packet,source):
        if source!=('127.0.0.1',8874):return False
        try:address,args=comparison_osc_read(packet)
        except (ValueError,UnicodeError,struct.error):return False
        with self.condition:
            request=self.pending;now=self.clock()
            if not request or now-request['sent_at']>self.reply_timeout:return False
            if address=='/adeps-compare/status':
                if (request['kind']!='ping' or len(args)!=4 or type(args[0])!=int or args[0]!=request['sequence']
                    or type(args[1])!=int or args[1] not in (0,1) or args[2] not in COMPARISON_METHODS|{''}
                    or not comparison_hash(args[3],allow_empty=True) or (args[1]==1 and not args[3])):return False
                self.ready=bool(args[1]);self.selected=args[2];self.input_sha256=args[3];self.last_status=now
            elif address=='/adeps-compare/ack':
                if len(args)!=3 or args[0]!=request['kind'] or not comparison_hash(args[2],allow_empty=True):return False
                if request['kind']=='select':
                    if args[1]!=request['method'] or args[2]!=request['expected_input_sha256']:return False
                    self.selected=args[1];self.input_sha256=args[2]
                elif request['kind']=='mute':
                    if args[1]!='':return False
                    # Mute acknowledgment means the instruction was dispatched;
                    # no claim of measured silence or Max DSP/gain state.
                    if args[2]!=self.input_sha256:
                        self.ready=False;self.selected='';self.input_sha256=args[2];self.last_status=None
                else:return False
            elif address=='/adeps-compare/error':
                if len(args)!=2 or args[0]!=request['kind'] or not isinstance(args[1],str):return False
                # Errors can signal a changed/unloaded bank. Require a fresh
                # status before presenting any previous readiness or selection.
                self.ready=False;self.selected='';self.input_sha256='';self.last_status=None
                request.update(done=True,outcome='remote_error',error=args[1]);self.last_reply=now
                self.condition.notify_all();return True
            else:return False
            request.update(done=True,outcome='acknowledged');self.last_reply=now
            self.condition.notify_all();return True
    def status(self):
        with self.condition:
            now=self.clock();age=now-self.last_reply if self.last_reply is not None else None
            status_age=now-self.last_status if self.last_status is not None else None
            fresh=age is not None and 0<=age<7
            loaded=self.ready and status_age is not None and 0<=status_age<7
            return {'service':'adeps-compare','api':'connected','max_reply':fresh,'ready':bool(fresh and loaded),
                'selected_method':self.selected if fresh else '', 'input_sha256':self.input_sha256 if fresh else '',
                'reply_age_seconds':round(age,3) if age is not None else None,
                'status_age_seconds':round(status_age,3) if status_age is not None else None,
                'ready_definition':'Ten files verified and all ten Max buffer loads acknowledged.',
                'audio_output':'manual_in_Max_unverified','destination':'127.0.0.1:8874','reply_port':8875}
    def _exchange(self,kind,method=None,expected_input_sha256=None):
        with self.condition:
            request={'kind':kind,'method':method,'expected_input_sha256':expected_input_sha256,
                     'sent_at':self.clock(),'done':False,'outcome':'timeout'}
            if kind=='ping':
                self.sequence=self.sequence%2147483646+1;request['sequence']=self.sequence
                packet=comparison_osc_message('/adeps-compare/ping',self.sequence)
            elif kind=='select':packet=comparison_osc_message('/adeps-compare/select',method,expected_input_sha256)
            else:packet=comparison_osc_message('/adeps-compare/mute')
            self.pending=request
            try:
                self.sock.sendto(packet,('127.0.0.1',8874))
                self.condition.wait_for(lambda:request['done'],timeout=self.reply_timeout)
            finally:self.pending=None
            result={**self.status(),'command':kind,'acknowledged':request['outcome']=='acknowledged','outcome':request['outcome']}
            if 'error' in request:result['error']=request['error']
            return result
    def command(self,kind,method=None,expected_input_sha256=None):
        if kind not in ('ping','select','mute'):raise ValueError('Only ping, select and mute comparison commands are supported.')
        if kind=='select':
            if not isinstance(method,str) or method not in COMPARISON_METHODS:raise ValueError('Unknown comparison method.')
            if not comparison_hash(expected_input_sha256):raise ValueError('expected_input_sha256 must be a lowercase SHA256.')
        elif method is not None or expected_input_sha256 is not None:raise ValueError('Only select accepts a method and expected_input_sha256.')
        with self.command_lock:
            if kind=='select':
                # Recheck the actual bank immediately before selection. The
                # controller also validates this hash atomically on receipt.
                ping=self._exchange('ping')
                if not ping['acknowledged']:
                    ping['command']='select';ping['error']='Max comparison status was not acknowledged.';return ping
                if not ping['ready']:raise ValueError('The Max comparison bank is not ready.')
                if ping['input_sha256']!=expected_input_sha256:raise ValueError('The Max comparison bank does not match expected_input_sha256.')
            return self._exchange(kind,method,expected_input_sha256)

comparison_bridge=None
class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):pass
    def send(self,data,status=200,ctype='application/json; charset=utf-8'):
        payload=data if isinstance(data,bytes) else json.dumps(to_jsonable(data),ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/status':self.send(bridge.status())
        elif path=='/api/max-compare':
            self.send(comparison_bridge.status() if comparison_bridge else {'error':'Max comparison bridge is unavailable.'},200 if comparison_bridge else 503)
        elif path=='/api/example-ir':self.send(sample_zip(),ctype='application/zip')
        else:self.send({'error':'Not found'},404)
    def do_POST(self):
        try:
            origin=self.headers.get('Origin','')
            if origin and origin not in ['http://127.0.0.1:5178','http://localhost:5178','http://127.0.0.1:8871']:raise ValueError('Local UI origin required')
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<=32_000_000:raise ValueError('アップロード上限は32 MBです。')
            raw=self.rfile.read(size);path=urlparse(self.path).path
            if path=='/api/ir':result=analyze_bundle(raw)
            elif path in ('/api/neural-audio', '/api/spatial-audio', '/api/spatial-source'):
                config=json.loads(self.headers.get('X-ADEPS-Config','{}'))
                if not isinstance(config,dict):raise ValueError('JSON object required')
                if path=='/api/neural-audio':
                    from neural_audio import run_audio
                    result,archive=run_audio(raw,config)
                else:
                    from spatial import run_spatial_audio,run_spatial_source
                    result,archive=(run_spatial_source if path=='/api/spatial-source' else run_spatial_audio)(raw,config)
                result.update(zip_base64=base64.b64encode(archive).decode(),filename='ADEPS_test_FOA_comparison.zip')
            else:
                cfg=json.loads(raw)
                if not isinstance(cfg,dict):raise ValueError('JSON object required')
                if path=='/api/playback':
                    allowed={'lambda_relative','reflection','fault_gain_db','fault_delay_ms','max_column_norm','speaker_positions','microphone_positions','geometry_profile'}
                    cfg={k:v for k,v in cfg.items() if k in allowed}
                    for key in ['speaker_positions','microphone_positions']:
                        if key in cfg and len(cfg[key])>64:raise ValueError('配置は64点までです。')
                    result=run_demo(**cfg)
                elif path=='/api/capture':result=run_capture(cfg)
                elif path=='/api/neural':
                    from neural import run_neural
                    result=run_neural(cfg)
                elif path=='/api/diffusion-studio':
                    from diffusion_studio import run_studio
                    result,archive=run_studio(cfg)
                    result.update(zip_base64=base64.b64encode(archive).decode(),filename='ADEPS_test_diffusion_studio.zip')
                elif path=='/api/paper-studio':
                    from paper_studio import run_paper_studio
                    result,archive=run_paper_studio(cfg)
                    result.update(zip_base64=base64.b64encode(archive).decode(),filename='ADEPS_test_full_prior_studio.zip')
                elif path=='/api/spatial':
                    from spatial import run_spatial
                    result=run_spatial(cfg)
                elif path in ('/api/neural-example','/api/spatial-example'):
                    from neural_audio import example_zip
                    result={'zip_base64':base64.b64encode(example_zip()).decode(),'filename':'ADEPS_test_array_audio_example.zip'}
                elif path=='/api/max':result=bridge.command(cfg.get('command'),cfg.get('channel'))
                elif path=='/api/max-compare':
                    if comparison_bridge is None:self.send({'error':'Max comparison bridge is unavailable.'},503);return
                    if set(cfg)-{'command','method','expected_input_sha256'}:raise ValueError('Unexpected comparison command fields.')
                    result=comparison_bridge.command(cfg.get('command'),cfg.get('method'),cfg.get('expected_input_sha256'))
                    self.send(result,200 if result['acknowledged'] else 504 if result['outcome']=='timeout' else 409);return
                else:self.send({'error':'Not found'},404);return
            self.send(result)
        except (ValueError,KeyError,TypeError,IndexError,EOFError) as exc:self.send({'error':str(exc)},400)
        except Exception as exc:
            traceback.print_exc();self.send({'error':f'解析を完了できませんでした: {type(exc).__name__}: {exc}'},422)

if __name__=='__main__':
    bridge=MaxBridge()
    comparison_bridge=MaxComparisonBridge()
    print('ADEPS-test analysis API: http://127.0.0.1:8871 (Max replies UDP 8873 / comparison UDP 8875)',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8871),Handler).serve_forever()
