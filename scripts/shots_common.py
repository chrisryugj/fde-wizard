"""샷 공용: 무대, 패스(컬러/클레이/와이어/뼈), 위치 조회, 곰돌이 루트."""
import math
import bpy
from mathutils import Vector, Matrix

import params as P
import stage
from lib import principled, coll

GEM = P.STAFF['length'] * (1 - P.STAFF['grip']) + P.STAFF['ring_r'] + 0.02


def rig():
    return bpy.data.objects['rig']


def char_objects():
    return [o for o in bpy.data.collections['CHAR'].all_objects if o.type in ('MESH', 'FONT')]


def viz_objects():
    return [bpy.data.objects[n] for n in ('rig_bones', 'rig_ik', 'rig_root')]


def studio(lens=70, bg=None, light=1.0, fps=30, w=1920, h=1080, samples=64, props=True):
    s = bpy.context.scene
    s.render.fps = fps
    stage.render_settings(w, h, samples=samples)
    s.render.image_settings.compression = 15
    stage.world(strength=0.55 * light)
    cyc = stage.cyclorama(bg)
    L = stage.lights(scale=light)
    cam = stage.camera(lens=lens)
    stage.bloom(threshold=2.5, strength=0.45, size=0.6)
    for o in viz_objects():
        o.hide_render = True
    for o in bpy.data.objects:
        if o.name.startswith('staff_'):
            o.visible_shadow = False
    if props:
        import set_props
        set_props.studio_props()
    return cam, L, cyc


def gem_pos(f):
    bpy.context.scene.frame_set(f)
    r = rig()
    return r.matrix_world @ r.pose.bones['staff'].matrix @ Vector((0, GEM, 0))


def bone_pos(name, f, along=0.5):
    bpy.context.scene.frame_set(f)
    r = rig()
    pb = r.pose.bones[name]
    return r.matrix_world @ (pb.head + (pb.tail - pb.head) * along)


def key_cam(cam, f, target, dist, az, el, lens=None):
    stage.orbit(cam, target, dist, az, el)
    cam.keyframe_insert('location', frame=f)
    cam.keyframe_insert('rotation_euler', frame=f)
    if lens:
        cam.data.lens = lens
        cam.data.keyframe_insert('lens', frame=f)


def hide_bear(hide=True):
    for o in list(bpy.data.collections['BEAR'].all_objects):  # 목록을 먼저 떠야 숨김이 다 먹는다
        o.hide_render = hide


def bear_root():
    """곰돌이 부품을 빈 객체 하나에 묶는다(원점=발밑)."""
    root = bpy.data.objects.get('bear_root')
    if root:
        return root
    root = bpy.data.objects.new('bear_root', None)
    bpy.data.collections['BEAR'].objects.link(root)
    for o in list(bpy.data.collections['BEAR'].objects):
        if o is not root and o.parent is None:
            o.parent = root
    return root


# ---------------------------------------------------------------- 패스
_orig = {}


def _swap(mats_fn):
    for o in char_objects():
        if o.name not in _orig:
            _orig[o.name] = [s.material for s in o.material_slots]
        mats = mats_fn(o)
        o.data.materials.clear()
        for m in mats:
            o.data.materials.append(m)


def restore():
    for o in char_objects():
        if o.name in _orig:
            o.data.materials.clear()
            for m in _orig[o.name]:
                o.data.materials.append(m)
        for m in [m for m in o.modifiers if m.name == 'Wire']:
            o.modifiers.remove(m)
        o.hide_render = False
    for o in viz_objects():
        o.hide_render = True
    for o in list(bpy.data.objects):  # 뼈 패스에서 숨긴 소품 되살리기(곰돌이는 샷이 정한 대로)
        if o.get('_hidden_by_bones'):
            o.hide_render = False
    s = bpy.context.scene
    s.render.film_transparent = False
    s.render.use_compositing = True
    cyc = bpy.data.objects.get('cyclorama')
    if cyc:
        cyc.hide_render = False


def clay_mat():
    return principled('clay', '#9E9A94', rough=0.55, spec=0.4)


def wire_mat():
    return principled('wire', '#3A3835', rough=0.7, spec=0.2)


def pass_beauty():
    restore()


def pass_clay():
    restore()
    _swap(lambda o: [clay_mat()])


def pass_wire():
    restore()
    _swap(lambda o: [clay_mat(), wire_mat()])
    for o in char_objects():
        if o.type != 'MESH':
            continue
        w = o.modifiers.new('Wire', 'WIREFRAME')
        w.thickness = 0.0035
        w.use_replace = False
        w.use_even_offset = True
        w.material_offset = 1
        w.offset = 1.0


def pass_bones():
    restore()
    keep = set(viz_objects())
    for o in list(bpy.data.objects):
        if o.type in ('MESH', 'FONT', 'CURVE') and o not in keep:
            o.hide_render = True
    for o in keep:
        o.hide_render = False
    s = bpy.context.scene
    s.render.film_transparent = True
    s.render.use_compositing = False
    cyc = bpy.data.objects.get('cyclorama')
    if cyc:
        cyc.hide_render = True


PASSES = {'beauty': pass_beauty, 'clay': pass_clay, 'wire': pass_wire, 'bones': pass_bones}


def reveal_bones(f0, f1):
    """뼈 시각화가 order 순서로 드러나게(reveal 0 → 1.05)."""
    for n in ('rig_bones', 'rig_ik', 'rig_root'):
        m = bpy.data.objects[n].data.materials[0]
        v = m.node_tree.nodes['reveal'].outputs[0]
        v.default_value = -0.02
        v.keyframe_insert('default_value', frame=f0)
        v.default_value = 1.05
        v.keyframe_insert('default_value', frame=f1)


FULL = dict(target=(0, 0, 1.24), dist=7.9, lens=50, room=1.10)  # room: 발 아래 자막 자리만큼 뒤로


def cam_full(cam, f, az=-18, el=5, dx=0.0, dist=None, dz=0.0):
    t = FULL['target']
    key_cam(cam, f, (t[0] + dx, t[1], t[2] + dz), (dist or FULL['dist']) * FULL['room'], az, el, lens=FULL['lens'])


def flash_light(pos_fn, f_peak, energy=2500, color='#FFD86B', rise=3, decay=16, radius=0.15):
    """마법 순간 빛 번쩍: 보석 위치를 따라가는 점광원."""
    from lib import hex2lin
    ld = bpy.data.lights.new('flash', 'POINT')
    ld.color = hex2lin(color)
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new('flash', ld)
    bpy.context.scene.collection.objects.link(ob)
    for f in range(f_peak - rise - 1, f_peak + decay + 2, 2):
        ob.location = pos_fn(f)
        ob.keyframe_insert('location', frame=f)
    for f, e in ((f_peak - rise - 1, 0), (f_peak, energy), (f_peak + decay // 3, energy * 0.35), (f_peak + decay, 0)):
        ld.energy = e
        ld.keyframe_insert('energy', frame=f)
    return ob


def dim_lights(L, keys):
    """keys: [(프레임, 배율)] — 기본 조명 세기를 함께 낮췄다 올린다."""
    for ob in L.values():
        base = ob.data.energy
        for f, k in keys:
            ob.data.energy = base * k
            ob.data.keyframe_insert('energy', frame=f)
        ob.data.energy = base


def shake(cam, f0, n=8, amp=0.035, seed=5):
    import random
    rnd = random.Random(seed)
    s = bpy.context.scene
    for f in range(f0, f0 + n + 1):
        s.frame_set(f)
        base = cam.location.copy()
        k = amp * (1 - (f - f0) / n)
        cam.location = base + Vector((rnd.uniform(-k, k), rnd.uniform(-k, k) * 0.3, rnd.uniform(-k, k)))
        cam.keyframe_insert('location', frame=f)
