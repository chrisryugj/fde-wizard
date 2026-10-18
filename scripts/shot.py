"""샷 렌더러: blender -b build/rig.blend -P shot.py -- <샷> [--preview] [--pass 이름] [--step N]
결과: renders/<A|B>/<샷>/<패스>/####.png + meta.json"""
import sys
import os
import json
import time
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shots_common as SC  # noqa: E402
import shots_making  # noqa: E402

SHOTS = dict(shots_making.SHOTS)
try:
    import shots_ax  # noqa: E402
    SHOTS.update(shots_ax.SHOTS)
except ImportError as e:
    print('shots_ax not loaded:', e)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
name = argv[0]
preview = '--preview' in argv
only = argv[argv.index('--pass') + 1] if '--pass' in argv else None
step = int(argv[argv.index('--step') + 1]) if '--step' in argv else 1

t0 = time.time()
spec = SHOTS[name](preview=preview)
s = bpy.context.scene
s.frame_start, s.frame_end, s.frame_step = 1, spec['frames'], step
if os.environ.get('SAMPLES'):  # 32 와 64 는 PSNR 48dB 로 눈으로 구분이 안 된다
    s.eevee.taa_render_samples = int(os.environ['SAMPLES'])
if preview:
    s.render.resolution_percentage = 50
    s.eevee.taa_render_samples = 16
video = 'A' if name.startswith('a') else 'B'
base = os.path.join(ROOT, 'renders' + ('_preview' if preview else ''), video, name)
os.makedirs(base, exist_ok=True)
with open(os.path.join(base, 'meta.json'), 'w') as fh:
    json.dump({'frames': spec['frames'], 'passes': spec['passes'], **spec.get('meta', {})}, fh, ensure_ascii=False)
print(f'SETUP {name} {time.time() - t0:.1f}s')
for p in spec['passes']:
    if only and p != only:
        continue
    SC.PASSES[p]()
    s.render.image_settings.color_mode = 'RGBA' if p == 'bones' else 'RGB'
    s.render.filepath = os.path.join(base, p, '')
    t1 = time.time()
    bpy.ops.render.render(animation=True)
    print(f'PASS {name}/{p} {time.time() - t1:.1f}s')
print(f'DONE {name} {time.time() - t0:.1f}s')
