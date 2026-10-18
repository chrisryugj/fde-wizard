"""리그: 뼈 + IK + 가중치(직접 계산) + 리그 시각화 메시. blender -b -P build_rig.py → build/rig.blend"""
import sys
import os
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P  # noqa: E402
import build_model  # noqa: E402
from parts_body import arm_points  # noqa: E402
from parts_bear import build_bear  # noqa: E402
from lib import coll, smoothstep, catmull, emission, bm_obj, hex2lin  # noqa: E402

B = P.BODY
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EYE_OFF = (0, -0.06, 0)


def bake(ob):
    mw = ob.matrix_world.copy()
    ob.parent = None
    if ob.type == 'MESH':
        ob.data.transform(mw)
        ob.matrix_world = Matrix.Identity(4)


def center(ob):
    vs = [v.co for v in ob.data.vertices]
    return sum(vs, Vector()) / len(vs)


def bone_table(parts, hat_spine, grip):
    T = {}

    def add(name, head, tail, parent=None, deform=True, roll_up=None):
        T[name] = (Vector(head), Vector(tail), parent, deform, roll_up)
    add('root', (0, 0, 0), (0, 0.35, 0), None, False)
    add('hips', (0, 0, 0.43), (0, 0, 0.56), 'root')
    add('spine', (0, 0, 0.56), (0, 0, 0.74), 'hips')
    add('chest', (0, 0, 0.74), (0, 0, 0.96), 'spine')
    add('neck', (0, 0, 0.96), (0, 0, 1.10), 'chest')
    add('head', (0, 0, 1.10), (0, 0, 1.80), 'neck')
    hs = catmull(hat_spine, 31)
    for i, (a, b) in enumerate(((0, 9), (9, 19), (19, 30))):
        add(f'hat.{i + 1}', hs[a], hs[b], 'head' if i == 0 else f'hat.{i}')
    for tag in ('L', 'R'):
        for base in ('eye', 'eye_happy'):
            c = center(parts[f'eye.{tag}'])
            add(f'{base}.{tag}', c, c + Vector(EYE_OFF), 'head', roll_up=(0, 0, 1))
        c = center(parts[f'brow.{tag}'])
        add(f'brow.{tag}', c, c + Vector(EYE_OFF), 'head', roll_up=(0, 0, 1))
    c = center(parts['mouth'])
    add('mouth', c, c + Vector(EYE_OFF), 'head', roll_up=(0, 0, 1))
    add('mouth_open', c, c + Vector(EYE_OFF), 'head', roll_up=(0, 0, 1))
    for side, tag in ((-1, 'R'), (1, 'L')):
        sh, el, wr, d = arm_points(side)
        el = el + Vector((0, 0.02, 0))  # 팔꿈치를 살짝 뒤로: IK 굽힘 방향 고정
        add(f'shoulder.{tag}', (side * 0.06, 0, 0.93), sh, 'chest')
        add(f'upper_arm.{tag}', sh, el, f'shoulder.{tag}')
        add(f'forearm.{tag}', el, wr, f'upper_arm.{tag}')
        add(f'hand.{tag}', wr, wr + d * 0.12, f'forearm.{tag}')
        add(f'hand_ik.{tag}', wr, wr + Vector((0, 0.09, 0)), 'root')
        add(f'elbow_pole.{tag}', el + Vector((0, 0.5, 0)), el + Vector((0, 0.58, 0)), 'root')
        hx = side * B['hip'][0]
        add(f'thigh.{tag}', (hx, 0, 0.43), (hx, -0.015, 0.26), 'hips')
        add(f'shin.{tag}', (hx, -0.015, 0.26), (hx, 0, 0.085), f'thigh.{tag}')
        add(f'foot.{tag}', (hx, 0, 0.085), (hx, -0.14, 0.04), f'shin.{tag}')
        add(f'foot_ik.{tag}', (hx, 0, 0.085), (hx, 0.09, 0.085), 'root')
        add(f'knee_pole.{tag}', (hx, -0.5, 0.26), (hx, -0.42, 0.26), 'root')
    add('staff', grip, grip + Vector((0, 0, 0.3)), 'root')  # 위치만 손을 따라간다(add_ik)
    add('cape.1', (0, 0.10, 0.99), (0, 0.17, 0.72), 'chest')
    add('cape.2', (0, 0.17, 0.72), (0, 0.22, 0.46), 'cape.1')
    add('cape.3', (0, 0.22, 0.46), (0, 0.27, 0.20), 'cape.2')
    clip = Vector(P.BADGE['clip'])
    add('badge', clip, clip + Vector((0, 0, -0.16)), 'chest')
    return T


def make_armature(T, c):
    arm = bpy.data.armatures.new('rig')
    rig = bpy.data.objects.new('rig', arm)
    c.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    for name, (h, t, parent, deform, roll_up) in T.items():
        b = eb.new(name)
        b.head, b.tail = h, t
        b.use_deform = True  # 시각화 메시도 아마추어 변형으로 따라가게(컨트롤 이름 그룹은 캐릭터에 없다)
        if roll_up:
            b.align_roll(Vector(roll_up))
    for name, (h, t, parent, deform, roll_up) in T.items():
        if parent:
            eb[name].parent = eb[parent]
            eb[name].use_connect = (eb[parent].tail - eb[name].head).length < 1e-4 and not name.startswith('hand_ik')
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'XYZ'
    return rig


def add_ik(rig):
    for tag in ('L', 'R'):
        for bone, target, pole in ((f'forearm.{tag}', f'hand_ik.{tag}', f'elbow_pole.{tag}'),
                                   (f'shin.{tag}', f'foot_ik.{tag}', f'knee_pole.{tag}')):
            k = rig.pose.bones[bone].constraints.new('IK')
            k.target, k.subtarget = rig, target
            k.pole_target, k.pole_subtarget = rig, pole
            k.chain_count = 2
            calibrate_pole(rig, bone, k)
    cl = rig.pose.bones['staff'].constraints.new('COPY_LOCATION')
    cl.target, cl.subtarget = rig, 'hand.R'
    hb = rig.data.bones['hand.R']
    sb = rig.data.bones['staff']
    cl.head_tail = (sb.head_local - hb.head_local).dot((hb.tail_local - hb.head_local).normalized()) / hb.length


def calibrate_pole(rig, bone, k):
    """쉬는 자세가 그대로 나오는 극 각도를 찾는다."""
    rest = rig.data.bones[bone].head_local.copy()

    def err(a):
        k.pole_angle = math.radians(a)
        bpy.context.view_layer.update()
        return (rig.pose.bones[bone].head - rest).length
    best = min(range(-180, 180, 3), key=err)
    best = min([best + d * 0.25 for d in range(-12, 13)], key=err)
    k.pole_angle = math.radians(best)
    bpy.context.view_layer.update()
    print(f'pole {bone}: {best:.2f}° err {err(best):.5f}')


# ---------------------------------------------------------------- 가중치
def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def limb(bones, T, power=8):
    segs = [(n, T[n][0], T[n][1]) for n in bones]

    def f(p):
        ws = {n: max(seg_dist(p, a, b), 1e-4) ** -power for n, a, b in segs}
        s = sum(ws.values())
        return {n: w / s for n, w in ws.items()}
    return f


def torso_w(p):
    wh = smoothstep(0.60, 0.48, p.z)
    wc = smoothstep(0.70, 0.86, p.z)
    ws = max(0.0, 1 - wh - wc)
    s = wh + wc + ws
    return {'hips': wh / s, 'spine': ws / s, 'chest': wc / s}


def cape_w(T):
    chain = limb(['cape.1', 'cape.2', 'cape.3'], T, 6)

    def f(p):
        wc = smoothstep(0.82, 0.96, p.z)
        out = {k: v * (1 - wc) for k, v in chain(p).items()}
        out['chest'] = wc
        return out
    return f


def rule(name, T):
    one = lambda b: (lambda p: {b: 1.0})  # noqa: E731
    for tag in ('L', 'R'):
        if name in (f'eye.{tag}', f'eye_hi0.{tag}', f'eye_hi1.{tag}', f'lid.{tag}'):
            return one(f'eye.{tag}')
        if name == f'eye_happy.{tag}':
            return one(f'eye_happy.{tag}')
        if name == f'brow.{tag}':
            return one(f'brow.{tag}')
        if name == f'sleeve.{tag}':
            return limb([f'shoulder.{tag}', f'upper_arm.{tag}', f'forearm.{tag}'], T)
        if name == f'cuff.{tag}':
            return limb([f'forearm.{tag}', f'hand.{tag}'], T)
        if name in (f'hand.{tag}', f'thumb.{tag}'):
            return one(f'hand.{tag}')
        if name == f'leg.{tag}':
            return limb(['hips', f'thigh.{tag}', f'shin.{tag}'], T)
        if name == f'shoe.{tag}':
            return one(f'foot.{tag}')
    if name == 'mouth':
        return one('mouth')
    if name in ('mouth_open', 'tongue'):
        return one('mouth_open')
    if name == 'neck':
        return one('neck')
    if name in ('cape', 'cape_trim'):
        return cape_w(T)
    if name == 'hat_cone':
        return limb(['hat.1', 'hat.2', 'hat.3'], T, 5)
    if name.startswith('hat_star'):
        return limb(['hat.1', 'hat.2', 'hat.3'], T, 14)
    if name.startswith('hat_'):
        return one('hat.1')
    if name.startswith('staff_'):
        return one('staff')
    if name.startswith('badge_'):
        return one('badge')
    if name.startswith(('torso', 'collar', 'lapel', 'tie', 'button', 'clasp', 'strap')):
        return torso_w
    return one('head')  # 머리, 얼굴, 머리카락, 귀, 코


def skin(ob, rig, fn):
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {}
    for v in ob.data.vertices:
        for bname, w in fn(v.co).items():
            if w < 1e-3:
                continue
            g = groups.get(bname) or ob.vertex_groups.new(name=bname)
            groups[bname] = g
            g.add([v.index], w, 'REPLACE')
    m = ob.modifiers.new('Armature', 'ARMATURE')
    m.object = rig
    ob.modifiers.move(len(ob.modifiers) - 1, 0)
    ob.parent = rig


# ---------------------------------------------------------------- 시각화(제작영상 리그 장면용)
def octa(bm, h, t, w=0.11):
    d = t - h
    L = d.length
    y = d.normalized()
    x = y.orthogonal().normalized()
    z = y.cross(x)
    m = h + d * 0.12
    vh, vt = bm.verts.new(h), bm.verts.new(t)
    ring = [bm.verts.new(m + (x * math.cos(a) + z * math.sin(a)) * L * w) for a in
            (0, math.pi / 2, math.pi, math.pi * 1.5)]
    for i in range(4):
        bm.faces.new((vh, ring[i], ring[(i + 1) % 4]))
        bm.faces.new((ring[(i + 1) % 4], ring[i], vt))
    return [vh, vt] + ring


def ring(bm, center, axis, r, minor=0.006, n=40):
    axis = Vector(axis).normalized()
    x = axis.orthogonal().normalized()
    y = axis.cross(x)
    vs = []
    rows = []
    for i in range(n):
        a = 2 * math.pi * i / n
        cdir = x * math.cos(a) + y * math.sin(a)
        row = []
        for k in range(6):
            b = 2 * math.pi * k / 6
            row.append(bm.verts.new(Vector(center) + cdir * (r + minor * math.cos(b)) + axis * minor * math.sin(b)))
        rows.append(row)
        vs += row
    for i in range(n):
        for k in range(6):
            bm.faces.new((rows[i][k], rows[i][(k + 1) % 6], rows[(i + 1) % n][(k + 1) % 6], rows[(i + 1) % n][k]))
    return vs


def build_viz(rig, T, c):
    """뼈(주황 팔면체) + IK 컨트롤(하늘색 고리) + 루트(노랑) 메시. 각 정점은 자기 뼈 하나에 100%."""
    out = {}
    specs = {
        'bones': ('rig_bones', '#FF9A3C', [n for n in T if n.split('.')[0] in (
            'hips', 'spine', 'chest', 'neck', 'head', 'shoulder', 'upper_arm', 'forearm', 'hand', 'thigh', 'shin',
            'foot', 'hat', 'cape', 'staff')]),
    }
    for key, (oname, color, names) in specs.items():
        bm = bmesh.new()
        owner = {}
        for n in names:
            h, t = T[n][0], T[n][1]
            for v in octa(bm, h, t):
                owner[v] = n
        ob = bm_viz(bm, oname, c, owner, rig, color)
        out[key] = ob
    bm = bmesh.new()
    owner = {}
    for tag in ('L', 'R'):
        for v in ring(bm, T[f'hand_ik.{tag}'][0], (0, 0, 1), 0.075):
            owner[v] = f'hand_ik.{tag}'
        for v in ring(bm, T[f'foot_ik.{tag}'][0] + Vector((0, -0.03, -0.075)), (0, 0, 1), 0.11):
            owner[v] = f'foot_ik.{tag}'
        for v in ring(bm, T[f'elbow_pole.{tag}'][0], (0, 1, 0), 0.03):
            owner[v] = f'elbow_pole.{tag}'
    out['ik'] = bm_viz(bm, 'rig_ik', c, owner, rig, '#38D9FF')
    bm = bmesh.new()
    owner = {}
    for v in ring(bm, (0, 0, 0.01), (0, 0, 1), 0.62, minor=0.009, n=64):
        owner[v] = 'root'
    for v in ring(bm, (0, 0, 0.47), (0, 0, 1), 0.33, minor=0.008, n=4):
        owner[v] = 'hips'
    out['root'] = bm_viz(bm, 'rig_root', c, owner, rig, '#FFD23F')
    return out


ORDER = {'root': 0.0, 'hips': 0.04, 'spine': 0.12, 'chest': 0.2, 'neck': 0.28, 'head': 0.34, 'shoulder': 0.38,
         'upper_arm': 0.44, 'forearm': 0.5, 'hand': 0.56, 'thigh': 0.44, 'shin': 0.5, 'foot': 0.56, 'hat': 0.64,
         'cape': 0.66, 'badge': 0.7, 'staff': 0.74, 'hand_ik': 0.86, 'foot_ik': 0.86, 'elbow_pole': 0.9}


def viz_material(name, color):
    """order < reveal 인 곳만 보이고, 막 드러나는 앞머리는 더 밝게 번쩍."""
    from shader import node
    m = bpy.data.materials.new(f'viz_{name}')
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, 'ShaderNodeOutputMaterial')
    em = node(nt, 'ShaderNodeEmission')
    em.inputs['Color'].default_value = (*hex2lin(color), 1)
    tr = node(nt, 'ShaderNodeBsdfTransparent')
    mix = node(nt, 'ShaderNodeMixShader')
    at = node(nt, 'ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='order')
    rv = node(nt, 'ShaderNodeValue', label='reveal', name='reveal')
    rv.outputs[0].default_value = 2.0
    d = node(nt, 'ShaderNodeMath', operation='SUBTRACT')
    nt.links.new(rv.outputs[0], d.inputs[0])
    nt.links.new(at.outputs['Fac'], d.inputs[1])
    vis = node(nt, 'ShaderNodeMath', operation='GREATER_THAN')
    nt.links.new(d.outputs[0], vis.inputs[0])
    vis.inputs[1].default_value = 0.0
    fl = node(nt, 'ShaderNodeMapRange')
    nt.links.new(d.outputs[0], fl.inputs['Value'])
    fl.inputs['From Min'].default_value = 0.0
    fl.inputs['From Max'].default_value = 0.08
    fl.inputs['To Min'].default_value = 12.0
    fl.inputs['To Max'].default_value = 3.0
    nt.links.new(fl.outputs['Result'], em.inputs['Strength'])
    nt.links.new(vis.outputs[0], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return m


def bm_viz(bm, name, c, owner, rig, color):
    idx = {}
    bm.verts.index_update()
    for v, n in owner.items():
        idx.setdefault(n, []).append(v.index)
    ob = bm_obj(bm, name, c, smooth=False)
    for n, ids in idx.items():
        ob.vertex_groups.new(name=n).add(ids, 1.0, 'REPLACE')
    at = ob.data.attributes.new('order', 'FLOAT', 'POINT')
    vals = [0.0] * len(ob.data.vertices)
    for n, ids in idx.items():
        for i in ids:
            vals[i] = ORDER[n.split('.')[0]] + (0.02 if n.endswith('.2') else 0.04 if n.endswith('.3') else 0.0)
    at.data.foreach_set('value', vals)
    m = ob.modifiers.new('Armature', 'ARMATURE')
    m.object = rig
    ob.parent = rig
    ob.data.materials.append(viz_material(name, color))
    ob.hide_render = True
    return ob


def default_pose(rig):
    for n in ('eye_happy.L', 'eye_happy.R', 'mouth_open'):
        rig.pose.bones[n].scale = (0.001, 0.001, 0.001)


def build():
    parts, M = build_model.build()
    hat_root = parts.pop('hat_root')
    staff_root = parts.pop('staff_root')
    hat_spine = [hat_root.matrix_world @ Vector(p) for p in P.HAT['spine']]
    sh, el, wr, d = arm_points(-1)
    grip = wr + d * (B['hand'][2] * 0.85)
    bpy.context.view_layer.update()  # 갓 만든 부품(공무원증 등)의 matrix_world 갱신 — 안 하면 원점으로 구워진다
    for ob in list(parts.values()):
        bake(ob)
    for e in (hat_root, staff_root):
        bpy.data.objects.remove(e)
    c = coll('RIG')
    T = bone_table(parts, hat_spine, grip)
    rig = make_armature(T, c)
    for name, ob in parts.items():
        if ob.type == 'MESH':
            skin(ob, rig, rule(name, T))
    stray = [o.name for o in bpy.data.collections['CHAR'].all_objects if o.type == 'MESH' and o.parent is not rig]
    if stray:  # 부품 목록에서 빠진 자식은 부모만 굽힐 때 원점으로 떨어진다(눈 하이라이트 사고)
        raise RuntimeError(f'리그에 안 붙은 캐릭터 부품: {stray}')
    add_ik(rig)
    viz = build_viz(rig, T, c)
    default_pose(rig)
    bear = build_bear()
    bpy.context.view_layer.update()
    for ob in bear.values():
        bake(ob)
    return parts, rig, viz, bear, T


if __name__ == '__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
    # 실험은 RIG_OUT 으로 따로 저장 — 렌더 중인 샷이 실험판 rig.blend 를 집어가지 않게
    bpy.ops.wm.save_as_mainfile(filepath=os.environ.get('RIG_OUT') or os.path.join(ROOT, 'build', 'rig.blend'))
    print('RIG_SAVED')
