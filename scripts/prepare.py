"""Keep downloadable dependencies outside iCloud-managed Documents."""
import hashlib,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CACHE=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'adeps-test'
def key(path):return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
node_cache=CACHE/key(ROOT/'package-lock.json')
python_cache=CACHE/('python-'+key(ROOT/'requirements.txt'))
if '--python-path' in sys.argv:
    print(python_cache/'bin/python');sys.exit(0)
if sys.version_info<(3,11):raise SystemExit('Python 3.11以降が必要です。')
node_cache.mkdir(parents=True,exist_ok=True)
if not (node_cache/'.ready').exists() or not (node_cache/'node_modules/.bin/vite').exists():
    print('Web画面のライブラリをローカルキャッシュに準備します。',flush=True)
    for name in ['package.json','package-lock.json']:(node_cache/name).write_bytes((ROOT/name).read_bytes())
    subprocess.run(['npm','ci'],cwd=node_cache,check=True)
    (node_cache/'.ready').write_text('installed from exact lockfile\n')
link=ROOT/'node_modules';destination=node_cache/'node_modules'
if link.is_symlink():
    if link.resolve()!=destination.resolve():link.unlink()
elif link.exists():
    # A pre-existing manual install is retained, never deleted.
    backup=ROOT/('node_modules.previous-'+str(int(time.time())))
    link.rename(backup)
    print('既存のライブラリは保存し、ローカルキャッシュを使用します。',flush=True)
if not link.is_symlink():link.symlink_to(destination,target_is_directory=True)
if not (python_cache/'.ready').exists():
    print('解析ライブラリをローカルキャッシュに準備します。',flush=True)
    subprocess.run([sys.executable,'-m','venv',str(python_cache)],check=True)
    subprocess.run([str(python_cache/'bin/python'),'-m','pip','install','-r',str(ROOT/'requirements.txt')],check=True)
    (python_cache/'.ready').write_text('installed from exact requirements\n')
print('起動の準備ができました。',flush=True)
