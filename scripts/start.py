"""User-invoked local launcher. Starts only this project's servers."""
import json,os,signal,socket,subprocess,sys,time,urllib.request,webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def probe(url):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:return r.read()
    except Exception:return None
def free(port, udp=False):
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM if udp else socket.SOCK_STREAM) as s:
        try:s.bind(('127.0.0.1',port));return True
        except OSError:return False
children=[]
def stop(signum,frame):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGHUP,stop)
try:
    status=probe('http://127.0.0.1:8871/api/status')
    if status and json.loads(status).get('service')=='adeps-test':print('ADEPS-test analysis engine is already running.')
    else:
        if not free(8871) or not free(8873,udp=True):raise RuntimeError('Port 8871 or 8873 is occupied. No existing process was stopped.')
        children.append(subprocess.Popen([sys.executable,'backend/server.py'],cwd=ROOT,start_new_session=True))
    page=probe('http://127.0.0.1:5178/')
    if not page or b'ADEPS-test' not in page:
        if not free(5178):raise RuntimeError('Port 5178 is occupied by another app. No existing process was stopped.')
        children.append(subprocess.Popen(['npm','run','dev:local'],cwd=ROOT,start_new_session=True))
    for i in range(360):
        if any(p.poll() is not None for p in children):raise RuntimeError('A server stopped. See its message above.')
        ready=probe('http://127.0.0.1:5178/lab-api/status')
        if ready and json.loads(ready).get('service')=='adeps-test':break
        time.sleep(.5)
    else:raise RuntimeError('Startup timed out.')
    print('\nADEPS-test: http://127.0.0.1:5178/\nPress Control-C here to stop the servers started by this launcher.',flush=True)
    if '--no-open' not in sys.argv:webbrowser.open('http://127.0.0.1:5178/')
    if children:
        while all(p.poll() is None for p in children):time.sleep(1)
except KeyboardInterrupt:pass
except RuntimeError as exc:
    print(f"起動できませんでした: {exc}",file=sys.stderr)
    sys.exit(1)
finally:
    for p in children:
        if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
    for p in children:
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL)
