"""Bundle the same scientific modules used by the local engine for WebAssembly."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
(root/'public/python').mkdir(parents=True,exist_ok=True)
for name in ('numerics','capture','measurements'):
    shutil.copyfile(root/f'backend/{name}.py',root/f'public/python/{name}.py')
