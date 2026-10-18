"""모델을 새로 짓고 여러 각도로 렌더해 tmp/prev_*.png 로 저장.
blender -b -P preview.py -- head|body [views...]"""
import sys
import os
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_model  # noqa: E402
import stage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
mode = argv[0] if argv else 'head'
views = argv[1:] or ['front', 'q34', 'side', 'back', 'top34']

bpy.ops.wm.read_factory_settings(use_empty=True)
build_model.build()
stage.render_settings(900, 900, samples=32)
stage.world()
stage.cyclorama()
stage.lights()
cam = stage.camera(lens=85)

if mode == 'head':
    target, dist = (0, 0, 1.60), 4.4
else:
    target, dist = (0, 0, 1.15), 8.0
VIEWS = {
    'front': (0, 4), 'q34': (-35, 8), 'q34r': (35, 8), 'side': (-90, 4),
    'sider': (90, 4), 'back': (180, 8), 'top34': (-25, 32), 'low': (-20, -8), 'face': (0, 2), 'bust': (0, 0), 'chest': (0, 0),
}
for v in views:
    az, el = VIEWS[v]
    if v == 'face':
        stage.orbit(cam, (0, 0, 1.42), 2.5, 0, 2)
    elif v == 'bust':
        stage.orbit(cam, (0, 0, 1.30), 4.6, -18, 6)
    elif v == 'chest':
        stage.orbit(cam, (0, -0.1, 0.78), 2.2, -10, 4)
    else:
        stage.orbit(cam, target, dist, az, el)
    stage.render(os.path.join(ROOT, 'tmp', f'prev_{mode}_{v}.png'))
