"""rig.blend 를 열어 포즈별로 렌더(컬러 + 뼈 시각화). blender -b build/rig.blend -P pose_test.py -- pose..."""
import sys
import os
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage  # noqa: E402
import poses  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
names = argv or ['wave', 'bow', 'cast', 'thumbs', 'tada', 'think']
rig = bpy.data.objects['rig']
for ob in bpy.data.collections['BEAR'].objects:
    ob.hide_render = True
show_viz = os.environ.get('VIZ') == '1'
for n in ('rig_bones', 'rig_ik', 'rig_root'):
    bpy.data.objects[n].hide_render = not show_viz
stage.render_settings(700, 700, samples=24)
stage.world()
stage.cyclorama()
stage.lights()
cam = stage.camera(lens=60)
az = float(os.environ.get('AZ', '-25'))
for n in names:
    poses.apply(rig, n)
    bpy.context.view_layer.update()
    stage.orbit(cam, (0, 0, 1.12), 6.2, az, 6)
    stage.render(os.path.join(ROOT, 'tmp', f'pose_{n}.png'))
