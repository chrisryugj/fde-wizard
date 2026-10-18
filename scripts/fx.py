"""마법 효과: 반짝이 폭발·꼬리, 한글 룬 마법진, 펑 연기. 모두 키프레임(시드 고정)."""
import math
import os
import random
import bpy
import bmesh
from mathutils import Vector

from lib import coll, emission, principled, bm_obj, ellipsoid, hex2lin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, 'build', 'tex', 'GmarketSans-Bold.ttf')
FX_COLORS = {'gold': ('#FFD23F', 9.0), 'white': ('#FFF4D2', 12.0), 'cyan': ('#7FE3FF', 9.0), 'pink': ('#FF9BC8', 8.0)}


def fx_mat(key):
    color, strength = FX_COLORS[key]
    return emission(f'fx_{key}', color, strength)


def font():
    f = bpy.data.fonts.get('Gmarket')
    if f:
        return f
    if not os.path.exists(FONT):  # 폰트를 안 받았으면 블렌더 기본 글꼴(한글도 나온다, 모양만 다름. 기본 글꼴은 이름을 못 바꾼다)
        return bpy.data.fonts.load('<builtin>', check_existing=True)
    f = bpy.data.fonts.load(FONT)
    f.name = 'Gmarket'
    return f


def twinkle_mesh(name, c, r=0.05, inner=0.22):
    """네 갈래 반짝 별(정면 -Y)."""
    bm = bmesh.new()
    ring = []
    for k in range(8):
        a = math.pi / 2 + k * math.pi / 4
        rr = r if k % 2 == 0 else r * inner
        ring.append(bm.verts.new((rr * math.cos(a), 0.0, rr * math.sin(a))))
    f = bm.verts.new((0, -r * 0.18, 0))
    b = bm.verts.new((0, r * 0.18, 0))
    for k in range(8):
        bm.faces.new((ring[k], ring[(k + 1) % 8], f))
        bm.faces.new((ring[(k + 1) % 8], ring[k], b))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_obj(bm, name, c, smooth=False)


def face_camera(ob, cam):
    t = ob.constraints.new('TRACK_TO')
    t.target = cam
    t.track_axis = 'TRACK_NEGATIVE_Y'
    t.up_axis = 'UP_Z'


def key_scale(ob, f, s, interp=None):
    ob.scale = (s, s, s) if not isinstance(s, tuple) else s
    ob.keyframe_insert('scale', frame=f)


def key_loc(ob, f, p):
    ob.location = p
    ob.keyframe_insert('location', frame=f)


def rand_dir(rnd, up_bias=0.3):
    while True:
        v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if 0.05 < v.length <= 1:
            v.normalize()
            v.z += up_bias
            return v.normalized()


def burst(name, origin, frame, cam, n=40, speed=(0.9, 2.2), life=(14, 30), size=(0.025, 0.06),
          colors=('gold', 'white', 'gold', 'cyan'), seed=1, up_bias=0.35, gravity=-0.6, c=None):
    """frame 에 origin 에서 사방으로 튀었다 사라지는 반짝이."""
    c = c or coll('FX')
    rnd = random.Random(seed)
    obs = []
    for i in range(n):
        kind = rnd.random()
        s = rnd.uniform(*size)
        if kind < 0.6:
            ob = twinkle_mesh(f'{name}_{i}', c, r=1.0)
            face_camera(ob, cam)
        else:
            ob = ellipsoid(f'{name}_{i}', (0, 0, 0), (0.45, 0.45, 0.45), c, cuts=2, levels=1)
        ob.data.materials.append(fx_mat(rnd.choice(colors)))
        ob.visible_shadow = False
        d = rand_dir(rnd, up_bias)
        v = rnd.uniform(*speed)
        L = rnd.randint(*life)
        p0 = Vector(origin)
        key_scale(ob, frame - 1, 0.0)
        for t in range(0, L + 1, 2):
            tt = t / 30
            drag = (1 - math.exp(-tt * 4)) / 4
            p = p0 + d * v * drag + Vector((0, 0, gravity * tt * tt * 0.5))
            key_loc(ob, frame + t, p)
            env = min(1.0, t / 3) * (1 - (t / L) ** 2)
            key_scale(ob, frame + t, s * max(env, 0.0) * (1 + 0.25 * math.sin(t * 1.3 + i)))
        key_scale(ob, frame + L + 1, 0.0)
        obs.append(ob)
    return obs


def trail(name, path_fn, f0, f1, cam, every=1, seed=7, colors=('gold', 'white'), size=(0.015, 0.035), c=None):
    """path_fn(f) 위치를 따라 프레임마다 떨어지는 반짝이 꼬리."""
    c = c or coll('FX')
    rnd = random.Random(seed)
    obs = []
    for f in range(f0, f1 + 1, every):
        ob = twinkle_mesh(f'{name}_{f}', c, r=1.0) if rnd.random() < 0.5 else \
            ellipsoid(f'{name}_{f}', (0, 0, 0), (0.45, 0.45, 0.45), c, cuts=2, levels=1)
        if ob.type == 'MESH' and ob.constraints.get('Track To') is None and len(ob.data.vertices) < 20:
            face_camera(ob, cam)
        ob.data.materials.append(fx_mat(rnd.choice(colors)))
        ob.visible_shadow = False
        p = Vector(path_fn(f)) + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.03
        s = rnd.uniform(*size)
        L = rnd.randint(10, 18)
        key_scale(ob, f - 1, 0.0)
        key_loc(ob, f, p)
        key_scale(ob, f, s)
        key_loc(ob, f + L, p + Vector((0, 0, rnd.uniform(-0.06, 0.12))))
        key_scale(ob, f + L, 0.0)
        obs.append(ob)
    return obs


def flat_ring(bm, r, w, n=96, z=0.0):
    outer = [bm.verts.new((math.cos(2 * math.pi * k / n) * (r + w / 2), math.sin(2 * math.pi * k / n) * (r + w / 2), z)) for k in range(n)]
    inner = [bm.verts.new((math.cos(2 * math.pi * k / n) * (r - w / 2), math.sin(2 * math.pi * k / n) * (r - w / 2), z)) for k in range(n)]
    for k in range(n):
        bm.faces.new((outer[k], outer[(k + 1) % n], inner[(k + 1) % n], inner[k]))


def line(bm, a, b, w, z=0.0):
    a, b = Vector((a[0], a[1], z)), Vector((b[0], b[1], z))
    d = (b - a).normalized()
    nrm = Vector((-d.y, d.x, 0)) * w / 2
    vs = [bm.verts.new(a + nrm), bm.verts.new(b + nrm), bm.verts.new(b - nrm), bm.verts.new(a - nrm)]
    bm.faces.new(vs)


def magic_circle(name, center, radius, f_in, f_out, words, color='gold', spin=0.6, c=None):
    """바닥에 깔리는 마법진: 고리 셋 + 육각별 + 한글 룬. f_in 에 튀어나와 f_out 에 사라진다."""
    c = c or coll('FX')
    root = bpy.data.objects.new(name, None)
    c.objects.link(root)
    root.location = center
    mat = emission(f'{name}_mat', FX_COLORS[color][0], 0.0)
    em = mat.node_tree.nodes['Emission'].inputs['Strength']
    bm = bmesh.new()
    flat_ring(bm, radius, 0.022)
    flat_ring(bm, radius * 0.80, 0.014)
    flat_ring(bm, radius * 0.40, 0.012)
    pts = [(math.cos(math.pi / 2 + k * math.pi / 3) * radius * 0.80, math.sin(math.pi / 2 + k * math.pi / 3) * radius * 0.80) for k in range(6)]
    for k in range(6):
        line(bm, pts[k], pts[(k + 2) % 6], 0.012)
    for k in range(24):
        a = 2 * math.pi * k / 24
        line(bm, (math.cos(a) * radius * 0.93, math.sin(a) * radius * 0.93), (math.cos(a) * radius * 0.97, math.sin(a) * radius * 0.97), 0.008)
    rings = bm_obj(bm, f'{name}_rings', c, smooth=False)
    rings.visible_shadow = False
    rings.data.materials.append(mat)
    rings.parent = root
    # 룬: 글자를 고리 사이에 눕혀 둘러 놓는다
    chars = [ch for w in words for ch in (w + '·')]
    n = len(chars)
    for i, ch in enumerate(chars):
        cu = bpy.data.curves.new(f'{name}_rune{i}', 'FONT')
        cu.body = ch
        cu.font = font()
        cu.size = radius * 0.12
        cu.align_x, cu.align_y = 'CENTER', 'CENTER'
        cu.extrude = 0.002
        ob = bpy.data.objects.new(f'{name}_rune{i}', cu)
        c.objects.link(ob)
        a = 2 * math.pi * i / n
        rr = radius * 0.895
        ob.location = (math.cos(a) * rr, math.sin(a) * rr, 0.002)
        ob.rotation_euler = (0, 0, a - math.pi / 2)
        ob.data.materials.append(mat)
        ob.visible_shadow = False
        ob.parent = root
    # 등장·회전·퇴장
    key_scale(root, f_in - 1, 0.0)
    key_scale(root, f_in + 5, 1.12)
    key_scale(root, f_in + 10, 1.0)
    key_scale(root, f_out, 1.0)
    key_scale(root, f_out + 8, 0.0)
    root.rotation_euler = (0, 0, 0)
    root.keyframe_insert('rotation_euler', frame=f_in - 1)
    root.rotation_euler = (0, 0, spin * (f_out + 8 - f_in) / 30)
    root.keyframe_insert('rotation_euler', frame=f_out + 8)
    for fc in fcurves_of(root):
        if fc.data_path == 'rotation_euler':
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    for f, v in ((f_in - 1, 0.0), (f_in + 4, FX_COLORS[color][1] * 1.4), (f_in + 14, FX_COLORS[color][1] * 0.8),
                 (f_out, FX_COLORS[color][1] * 0.8), (f_out + 8, 0.0)):
        em.default_value = v
        em.keyframe_insert('default_value', frame=f)
    return root


def fcurves_of(idblock):
    ad = idblock.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    try:
        return list(act.fcurves)
    except AttributeError:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out += list(bag.fcurves)
        return out


def poof(name, center, frame, size=0.35, n=10, seed=3, color='#FFFFFF', c=None):
    """만화식 펑 연기: 구름 공들이 부풀며 흩어졌다 사라진다."""
    c = c or coll('FX')
    rnd = random.Random(seed)
    mat = principled(f'{name}_mat', color, rough=0.9, emit=color, emit_strength=0.35)
    obs = []
    for i in range(n):
        d = rand_dir(rnd, 0.2)
        r = size * rnd.uniform(0.35, 0.6)
        ob = ellipsoid(f'{name}_{i}', (0, 0, 0), (1, 1, 1), c, cuts=3, levels=1)
        ob.data.materials.append(mat)
        p0 = Vector(center) + d * size * 0.2
        p1 = Vector(center) + d * size * rnd.uniform(0.7, 1.1)
        key_scale(ob, frame - 1, 0.0)
        key_loc(ob, frame - 1, p0)
        key_scale(ob, frame + 3, r * 1.1)
        key_loc(ob, frame + 14, p1)
        key_scale(ob, frame + 9, r)
        key_scale(ob, frame + 16 + i % 4, 0.0)
        obs.append(ob)
    return obs


def text3d(name, body, size, mat, c=None, extrude=0.01, align='CENTER'):
    c = c or coll('FX')
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.font = font()
    cu.size = size
    cu.align_x, cu.align_y = align, 'CENTER'
    cu.extrude = extrude
    cu.bevel_depth = extrude * 0.3
    ob = bpy.data.objects.new(name, cu)
    c.objects.link(ob)
    ob.data.materials.append(mat)
    return ob
