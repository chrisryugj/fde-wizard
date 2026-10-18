"""대표 이미지(4:5 세로): 노을 섬 위 '짠!' + 곰돌이 + 반짝이. blender -b build/rig.blend -P hero.py"""
import sys
import os
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poses  # noqa: E402
import fx  # noqa: E402
import shots_ax  # noqa: E402
from shots_common import rig, gem_pos, key_cam, hide_bear  # noqa: E402
from shots_making import bear_rig  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cam, L = shots_ax.ax_stage(samples=128)
s = bpy.context.scene
s.render.resolution_x, s.render.resolution_y = 1080, 1350
r = rig()
hide_bear(False)
poses.apply(r, 'tada', {'happy': 0.0, 'open': 1.0, 'eye_big': 0.45})
for n, path in poses.CHANNELS:
    r.pose.bones[n].keyframe_insert(path, frame=1)
bpy.context.view_layer.update()
root = bear_rig()
root.location = (1.18, -0.45, 1.78)
root.rotation_euler = (0, 0.1, -0.35)
root.scale = (1.35,) * 3
for side in ('L', 'R'):
    bpy.data.objects[f'bear_arm.{side}'].rotation_euler = (0, (1 if side == 'L' else -1) * 2.5, 0)
fx.burst('hb', gem_pos(1) + Vector((0, 0, 0.05)), -6, cam, n=60, seed=5, speed=(0.8, 2.2), size=(0.03, 0.07), gravity=0.0, up_bias=0.6)
key_cam(cam, 1, (0.55, 0, 1.48), 5.9, 26, 5, lens=50)
s.frame_set(1)
out = os.path.join(ROOT, 'out', 'hero_4x5.png')
s.render.filepath = out
bpy.ops.render.render(write_still=True)
print('HERO', out)
