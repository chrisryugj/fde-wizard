"""웹용 내보내기: 리그+캐릭터+곰돌이 → out/web/fde_wizard.glb, 셰이더 값 → out/web/shader.json
동작(대기·손인사·인사·주문·걷기·짠)과 포즈 8개를 글TF 애니메이션으로 굽는다(IK·스프링 포함).
blender -b build/rig.blend -P scripts/export_web.py"""
import sys
import os
import json
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P  # noqa: E402
import poses  # noqa: E402
import anim  # noqa: E402
from shots_making import cast_keys, walk_keys  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'out', 'web')
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
scene.render.fps = 30
rig = bpy.data.objects['rig']

# ---------------------------------------------------------------- 메시: 웹용으로 가볍게
char = [o for o in bpy.data.collections['CHAR'].all_objects if o.type == 'MESH']
bear = [o for o in bpy.data.collections['BEAR'].all_objects if o.type == 'MESH']
for o in char + bear:
    for m in o.modifiers:
        if m.type == 'SUBSURF':
            m.levels = m.render_levels = 1
for n in ('rig_bones', 'rig_ik', 'rig_root'):
    bpy.data.objects[n].hide_set(True)
bear_root = bpy.data.objects.new('bear_root', None)
bpy.data.collections['BEAR'].objects.link(bear_root)
for o in bear:
    o.parent = bear_root
bear_root.location = (0.85, -0.2, 1.25)  # 곰돌이가 떠 있는 자리(웹에서 위치·등장을 다시 잡는다)


# ---------------------------------------------------------------- 동작
def new_action(name):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act
    return act


def clip(name, keys, frames, springs=True):
    new_action(name)
    anim.timeline(rig, keys)
    if springs:
        anim.bake_springs(rig, 1, frames, anim.DEFAULT_CHAINS)
    return name


def loop(keys, end):
    """마지막 프레임을 첫 키와 같게 — 반복할 때 튀지 않게."""
    f, pose, extra, interp = keys[0]
    return keys + [(end, pose, extra, interp)]


made = []
made.append(clip('idle', loop([(1, 'idle', {'hips_off': (0, 0, -0.004), 'chest': (3, 0, 0)}, 'BEZIER'),
                               (31, 'idle', {'hips_off': (0, 0, 0.008), 'chest': (1, 0, 0)}, 'BEZIER'),
                               (44, 'idle', {'hips_off': (0, 0, 0.004), 'blink': 0.0}, 'BEZIER'),
                               (46, 'idle', {'hips_off': (0, 0, 0.003), 'blink': 1.0}, 'BEZIER'),
                               (49, 'idle', {'hips_off': (0, 0, 0.002), 'blink': 0.0}, 'BEZIER')], 61), 61))
wave = [(1, 'idle', None, 'BEZIER'), (8, 'idle', {'squash': 0.04, 'hips_off': (0, 0, -0.02)}, 'BEZIER'),
        (14, 'wave', {'hand.L': (0, 0, -15), 'eye_big': 0.3}, 'BEZIER')]
for i in range(4):
    wave.append((20 + i * 7, 'wave', {'hand.L': (0, 0, -65 if i % 2 == 0 else -10), 'head': (0, 4, -8 - 3 * (i % 2))}, 'BEZIER'))
wave += [(50, 'idle', {'happy': 1.0}, 'BEZIER'), (60, 'idle', None, 'BEZIER')]
made.append(clip('wave', wave, 60))
made.append(clip('bow', [
    (1, 'idle', None, 'BEZIER'), (6, 'idle', {'happy': 1.0}, 'BEZIER'), (16, 'bow', None, 'BEZIER'),
    (22, 'bow', {'hat_slip': (30, 0.05)}, 'BEZIER'),
    (27, 'bow', {'hat_slip': (58, 0.10), 'happy': 0.0, 'eye_big': 1.0, 'brow': 0.02, 'open': 0.5}, 'BEZIER'),
    (32, 'idle', {'hips_off': (0, 0, 0.05), 'squash': -0.05, 'eye_big': 1.0, 'brow': 0.02, 'open': 0.6,
                  'hat_off': (0, -0.05, 0.12), 'hat.1': (-10, 0, 0)}, 'BEZIER'),
    (38, 'idle', {'hat_off': (0, 0, -0.01), 'squash': 0.04}, 'BEZIER'),
    (44, 'thumbs', None, 'BEZIER'), (60, 'thumbs', None, 'BEZIER'), (72, 'idle', None, 'BEZIER')], 72))
made.append(clip('cast', cast_keys(1) + [
    (44, 'cast', None, 'BEZIER'), (52, 'idle', {'eye_big': 0.6, 'hat.1': (0, 0, 8)}, 'BEZIER'),
    (55, 'idle', {'hat.1': (0, 0, -8), 'eye_big': 0.8}, 'BEZIER'), (58, 'idle', {'hat.1': (6, 0, 6)}, 'BEZIER'),
    (62, 'idle', {'hat.1': (0, 0, 0), 'squash': 0.05}, 'BEZIER'),
    (70, 'tada', {'staff_dir': (-0.2, -0.2, 1)}, 'BEZIER'), (86, 'tada', None, 'BEZIER'),
    (96, 'idle', {'happy': 1.0}, 'BEZIER'), (105, 'idle', None, 'BEZIER')], 105))
made.append(clip('walk', loop(walk_keys(1, cycles=2, period=20), 41), 41))
made.append(clip('tada', [(1, 'idle', None, 'BEZIER'), (8, 'idle', {'squash': 0.08, 'hips_off': (0, 0, -0.04)}, 'BEZIER'),
                          (14, 'tada', {'squash': -0.05, 'hips_off': (0, 0, 0.06)}, 'BEZIER'),
                          (20, 'tada', None, 'BEZIER'), (40, 'tada', None, 'BEZIER'), (50, 'idle', None, 'BEZIER')], 50))
for p in ('rest', 'idle', 'wave', 'bow', 'cast', 'thumbs', 'tada', 'think'):  # 포즈 선반: 두 프레임짜리 정지 동작
    made.append(clip(f'pose_{p}', [(1, p, None, 'CONSTANT'), (2, p, None, 'CONSTANT')], 2, springs=False))
rig.animation_data.action = None
poses.apply(rig, 'idle')
scene.frame_set(1)

# ---------------------------------------------------------------- 셰이더 값(웹에서 같은 무늬를 다시 그린다)
C = P.COLORS


def node_default(mat, kind):
    for n in bpy.data.materials[mat].node_tree.nodes:
        if n.bl_idname == kind:
            return n


blush = node_default('skin_face', 'ShaderNodeVectorMath')  # 볼터치 중심(SUBTRACT 의 두 번째 입력)
shader = {
    'skin': C['skin'], 'blush': C['blush'], 'scalp': C['scalp'],
    'blush_center': list(blush.inputs[1].default_value), 'blush_r': P.FACE['blush_r'], 'blush_k': 0.55,
    'scalp_tilt': 0.35, 'scalp_from': P.HEAD['scalp_z'][0], 'scalp_to': P.HEAD['scalp_z'][1],
    'suit': C['suit'], 'shirt': C['shirt'], 'v_bottom': P.BODY['v_bottom'], 'v_slope': P.BODY['v_slope'],
    'tie': C['tie'], 'tie_dot': C['tie_dot'], 'tie_gap': P.BODY['tie_dot_gap'],
    'eye': C['eye'], 'iris': C['iris'],
    'clips': made,
}
json.dump(shader, open(os.path.join(OUT, 'shader.json'), 'w'), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 내보내기
bpy.ops.object.select_all(action='DESELECT')
for o in char + bear + [rig, bear_root]:
    o.hide_set(False)
    o.select_set(True)
bpy.context.view_layer.objects.active = rig
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for o in char + bear:
    me = o.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    tris += len(me.loop_triangles)
    o.evaluated_get(dg).to_mesh_clear()
print('TRIS', tris)
path = os.path.join(OUT, 'fde_wizard.glb')
bpy.ops.export_scene.gltf(
    filepath=path, export_format='GLB', use_selection=True, export_apply=True,
    export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
    export_optimize_animation_size=False, export_anim_slide_to_zero=True,
    export_skins=True, export_all_influences=False, export_morph=False, export_yup=True,
    export_cameras=False, export_lights=False, export_extras=False)
print('GLB', path, os.path.getsize(path) // 1024, 'KB', 'clips', len(made))
