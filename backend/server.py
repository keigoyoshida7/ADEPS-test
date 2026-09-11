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
class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):pass
    def send(self,data,status=200,ctype='application/json; charset=utf-8'):
        payload=data if isinstance(data,bytes) else json.dumps(to_jsonable(data),ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/status':self.send(bridge.status())
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
                elif path=='/api/spatial':
                    from spatial import run_spatial
                    result=run_spatial(cfg)
                elif path in ('/api/neural-example','/api/spatial-example'):
                    from neural_audio import example_zip
                    result={'zip_base64':base64.b64encode(example_zip()).decode(),'filename':'ADEPS_test_array_audio_example.zip'}
                elif path=='/api/max':result=bridge.command(cfg.get('command'),cfg.get('channel'))
                else:self.send({'error':'Not found'},404);return
            self.send(result)
        except (ValueError,KeyError,TypeError,IndexError,EOFError) as exc:self.send({'error':str(exc)},400)
        except Exception as exc:
            traceback.print_exc();self.send({'error':f'解析を完了できませんでした: {type(exc).__name__}: {exc}'},422)

if __name__=='__main__':
    bridge=MaxBridge()
    print('ADEPS-test analysis API: http://127.0.0.1:8871 (Max reply UDP 8873)',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8871),Handler).serve_forever()
