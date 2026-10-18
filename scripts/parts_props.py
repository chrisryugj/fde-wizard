"""소품: 망토, 마법사 모자, 지팡이, 공무원증."""
import math
import os
import bpy
import bmesh
from mathutils import Vector, Matrix

import params as P
from lib import (sweep, ellipsoid, principled, emission, set_mat, bm_obj, subsurf, bvh, hit,
                 smoothstep, lerp, catmull, hex2lin)
from shader import node

C = P.COLORS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def prop_materials():
    return {
        'cape': principled('cape', C['cape'], rough=0.6, spec=0.3, sheen=0.4),
        'lining': principled('lining', C['lining'], rough=0.5, spec=0.3, sheen=0.3),
        'gold': principled('gold', C['trim'], rough=0.28, metal=1.0),
        'star': principled('star', C['star'], rough=0.35, spec=0.5, emit=C['star'], emit_strength=0.6),
        'wood': principled('wood', C['wood'], rough=0.55, spec=0.3),
        'crystal': emission('crystal', C['crystal'], 6.0),
        'strap': principled('strap', C['strap'], rough=0.5, spec=0.3),
        'silver': principled('silver', '#D8DEE8', rough=0.25, metal=1.0),
        'card_edge': principled('card_edge', '#FFFFFF', rough=0.3, spec=0.5),
    }


# ---------------------------------------------------------------- 망토
def build_cape(c, M):
    K = P.CAPE
    rows = K['rows']
    n_t, n_s = 16, 28
    # 행(높이, rx, ry, 중심y, 시작 방위, 끝 방위, 주름)을 세로로 보간
    cols = list(zip(*rows))
    samp = [catmull([Vector((v, 0, 0)) for v in col], n_t) for col in cols]
    bm = bmesh.new()
    grid = []
    for i in range(n_t):
        z, rx, ry, cy, a0, a1, fold = (samp[k][i].x for k in range(7))
        row = []
        for j in range(n_s + 1):
            s = j / n_s
            az = math.radians(lerp(a0, a1, s))
            f = 1 + fold * math.sin(az * K['folds'])
            row.append(bm.verts.new((rx * f * math.sin(az), cy - ry * f * math.cos(az), z)))
        grid.append(row)
    for i in range(n_t - 1):
        for j in range(n_s):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    hem = [v.co.copy() for v in grid[-1]]
    ob = bm_obj(bm, 'cape', c)
    # 바깥이 +법선이 되도록(가운데 뒤쪽 면 법선이 +Y)
    me = ob.data
    mid = me.polygons[len(me.polygons) // 2]
    if mid.normal.y < 0:
        me.flip_normals()
    so = ob.modifiers.new('Solidify', 'SOLIDIFY')
    so.thickness = 0.018
    so.offset = -1
    so.material_offset = 1
    so.material_offset_rim = 2
    subsurf(ob, 2)
    set_mat(ob, M['cape'], M['lining'], M['gold'])
    trim = sweep('cape_trim', hem, 0.014, c, sides=8, segs=60, tip=False, cap0=True)
    set_mat(trim, M['gold'])
    # 앞 여밈 장식: 어깨 앞 둥근 고리 둘 + 사슬
    clasps = {}
    for side, tag in ((-1, 'R'), (1, 'L')):
        cl = ellipsoid(f'clasp.{tag}', (0, 0, 0), (0.032, 0.014, 0.032), c, cuts=3)
        cl.location = (side * 0.165, -0.115, 0.955)
        set_mat(cl, M['gold'])
        clasps[f'clasp.{tag}'] = cl
    chain = sweep('clasp_chain', [(-0.15, -0.135, 0.95), (0.0, -0.20, 0.905), (0.15, -0.135, 0.95)], 0.006, c,
                  sides=6, segs=16, tip=False)
    set_mat(chain, M['gold'])
    return {'cape': ob, 'cape_trim': trim, 'clasp_chain': chain, **clasps}


# ---------------------------------------------------------------- 모자
def star_mesh(name, c, r=0.05, depth=0.02, inner=0.45, levels=1):
    bm = bmesh.new()
    ring = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * inner
        ring.append(bm.verts.new((rr * math.cos(a), 0.0, rr * math.sin(a))))
    f = bm.verts.new((0, -depth, 0))
    b = bm.verts.new((0, depth, 0))
    for k in range(10):
        bm.faces.new((ring[k], ring[(k + 1) % 10], f))
        bm.faces.new((ring[(k + 1) % 10], ring[k], b))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = bm_obj(bm, name, c)
    if levels:
        subsurf(ob, levels)
    return ob


def build_hat(c, M):
    T = P.HAT
    root = bpy.data.objects.new('hat_root', None)
    c.objects.link(root)
    spine = [Vector(p) for p in T['spine']]
    cone = sweep('hat_cone', spine,
                 lambda u: T['base_r'] * (1 + 0.06 * math.sin(math.pi * min(1, u * 3))) * (1 - u) ** 0.85,
                 c, sides=24, segs=44, tip=True, cap0=False, up=lambda p, u: (0, 1, 0))  # 밑뚜껑이 있으면 다듬기로 밑이 둥글게 말려 올라가 앞머리가 챙 위로 비친다
    set_mat(cone, M['cape'])
    # 챙: 고리판, 가장자리는 살짝 들리고 물결
    bm = bmesh.new()
    rings = []
    nr, na = 5, 56
    for i in range(nr):
        t = i / (nr - 1)
        rr = lerp(T['base_r'] * 0.45, T['brim_r'], t)  # 원뿔 밑면이 다듬기로 오므라들어도 챙에 틈이 안 생기게
        ring = []
        for k in range(na):
            a = 2 * math.pi * k / na
            z = T['brim_curl'] * t * t + T['brim_wave'] * t * t * math.sin(3 * a + 0.6)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        rings.append(ring)
    for i in range(nr - 1):
        for k in range(na):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % na], rings[i + 1][(k + 1) % na], rings[i + 1][k]))
    brim = bm_obj(bm, 'hat_brim', c)
    so = brim.modifiers.new('Solidify', 'SOLIDIFY')
    so.thickness = 0.036
    so.offset = 0
    subsurf(brim, 2)
    set_mat(brim, M['cape'])
    band = sweep('hat_band', [(0, 0, 0.005), (0, 0.004, 0.075)], T['base_r'] * 1.02, c, sides=32, segs=4,
                 tip=False, cap0=False, levels=1)
    set_mat(band, M['gold'])
    buckle = star_mesh('hat_buckle', c, r=0.055, depth=0.022)
    buckle.location = (0, -T['base_r'] * 1.06, 0.04)
    set_mat(buckle, M['star'])
    parts = {'hat_cone': cone, 'hat_brim': brim, 'hat_band': band, 'hat_buckle': buckle}
    # 원뿔 표면에 작은 별 — 원뿔 중심선에서 바깥으로 쏴서 붙인다
    tree = bvh(cone)
    for i, (u, az, r) in enumerate(T['stars']):
        p = catmull(spine, 50)[int(u * 49)]
        d = Vector((math.sin(math.radians(az)), -math.cos(math.radians(az)), 0.15)).normalized()
        loc, nor, _, _ = tree.ray_cast(p + d * 0.6, -d)
        if loc is None:
            continue
        st = star_mesh(f'hat_star{i}', c, r=r, depth=r * 0.35)
        st.location = loc + nor * 0.006
        st.rotation_euler = d.to_track_quat('-Y', 'Z').to_euler()
        set_mat(st, M['star'])
        parts[f'hat_star{i}'] = st
    for ob in parts.values():
        ob.parent = root
    root.matrix_world = Matrix.Translation(T['pos']) @ Matrix.Rotation(math.radians(T['tilt'][0]), 4, 'X') \
        @ Matrix.Rotation(math.radians(T['tilt'][1]), 4, 'Y')
    parts['hat_root'] = root
    return parts


# ---------------------------------------------------------------- 지팡이
def build_staff(c, M, grip):
    S = P.STAFF
    root = bpy.data.objects.new('staff_root', None)
    c.objects.link(root)
    L = S['length']
    shaft = sweep('staff_shaft', [(0, 0, 0), (0, 0, L * 0.5), (0, 0, L)],
                  lambda u: lerp(S['r'][0], S['r'][1], u) * (1 + 0.08 * math.sin(u * 40)), c, sides=10, segs=60,
                  tip=False, levels=1)
    set_mat(shaft, M['wood'])
    ring = sweep('staff_ring', [(S['ring_r'] * math.cos(a), 0, L + S['ring_r'] + 0.02 + S['ring_r'] * math.sin(a))
                                for a in [math.radians(-90 + 360 * k / 24) for k in range(25)]],
                 0.013, c, sides=8, segs=48, tip=False, cap0=False)
    set_mat(ring, M['gold'])
    cup = ellipsoid('staff_cup', (0, 0, L + 0.01), (0.04, 0.04, 0.03), c, cuts=3)
    set_mat(cup, M['gold'])
    gem = star_mesh('staff_gem', c, r=S['gem_r'], depth=S['gem_r'] * 0.42, inner=0.5)
    gem.location = (0, 0, L + S['ring_r'] + 0.02)
    set_mat(gem, M['crystal'])
    parts = {'staff_shaft': shaft, 'staff_ring': ring, 'staff_cup': cup, 'staff_gem': gem}
    for ob in parts.values():
        ob.parent = root
    root.location = (grip.x, grip.y, grip.z - L * S['grip'])
    parts['staff_root'] = root
    return parts


# ---------------------------------------------------------------- 공무원증
def card_material():
    m = bpy.data.materials.get('card_face') or bpy.data.materials.new('card_face')
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    path = os.path.join(ROOT, 'build', 'tex', 'card.png')
    if os.path.exists(path):  # scripts/make_card.py 가 만든다. 없으면 흰 카드
        img = node(nt, 'ShaderNodeTexImage')
        img.image = bpy.data.images.load(path, check_existing=True)
        nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.25
    b.inputs['Coat Weight'].default_value = 0.6
    return m


def build_badge(c, M, torso):
    G = P.BADGE
    tree = bvh(torso)
    parts = {}

    def on_torso(x, z, push):
        loc, nor = hit(tree, (x, -2.0, z), (0, 1, 0))
        return loc + nor * push
    clip = Vector(G['clip'])
    for side, tag in ((-1, 'R'), (1, 'L')):
        pts = [Vector((side * 0.06, 0.10, 1.01)), Vector((side * 0.105, -0.05, 1.0)),
               on_torso(side * 0.075, 0.86, 0.012), on_torso(side * 0.04, 0.74, 0.012), clip + Vector((side * 0.004, 0, 0.01))]
        st = sweep(f'strap.{tag}', pts, G['strap_w'], c, sides=8, segs=30, aspect=0.22, tip=False,
                   up=lambda p, u: Vector((p.x, p.y, 0)).normalized())
        set_mat(st, M['strap'])
        parts[f'strap.{tag}'] = st
    cl = ellipsoid('badge_clip', (0, 0, 0), (0.016, 0.01, 0.022), c, cuts=2)
    cl.location = clip
    set_mat(cl, M['silver'])
    w, h, t = G['size']
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * w, v.co.y * t, v.co.z * h))
    body = bm_obj(bm, 'badge_card', c, smooth=False)
    bev = body.modifiers.new('Bevel', 'BEVEL')
    bev.width = 0.01
    bev.segments = 3
    body.location = (clip.x, clip.y - 0.004, clip.z - h / 2 - 0.012)
    set_mat(body, M['card_edge'])
    # 앞면: UV 가 붙은 판
    me = bpy.data.meshes.new('badge_face')
    me.from_pydata([(-w / 2 * 0.94, 0, -h / 2 * 0.95), (w / 2 * 0.94, 0, -h / 2 * 0.95),
                    (w / 2 * 0.94, 0, h / 2 * 0.95), (-w / 2 * 0.94, 0, h / 2 * 0.95)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, co in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = co
    face = bpy.data.objects.new('badge_face', me)
    c.objects.link(face)
    face.parent = body
    face.location = (0, -t / 2 - 0.0012, 0)
    set_mat(face, card_material())
    parts.update({'badge_clip': cl, 'badge_card': body, 'badge_face': face})
    return parts
