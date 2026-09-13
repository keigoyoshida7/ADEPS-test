"""Bundle the same scientific modules used by the local engine for WebAssembly."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
(root/'public/python').mkdir(parents=True,exist_ok=True)
for name in ('numerics','capture','measurements','neural','neural_audio','spatial','spatial_model','diffusion_studio'):
    shutil.copyfile(root/f'backend/{name}.py',root/f'public/python/{name}.py')
for name in ('ADEPS_REVIEW.md','NEURAL_PROTOCOL.md','SPATIAL_MODEL.md','DIFFUSION_STUDIO.md'):
    shutil.copyfile(root/f'docs/{name}',root/f'public/info/{name}')
