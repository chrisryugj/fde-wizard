"""모델: 부품을 하나씩 만든다. blender -b -P build_model.py 로 build/model.blend 저장."""
import sys
import os
import math
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P  # noqa: E402
from lib import (coll, sweep, ellipsoid, principled, emission, set_mat, bvh, hit, place,  # noqa: E402
                 smoothstep, lerp, hex2lin, add_rest)
from shader import node, sock, mix_color, blob_mask, rest_coords  # noqa: E402
from parts_body import build_body, arm_points  # noqa: E402
from parts_props import prop_materials, build_cape, build_hat, build_staff, build_badge  # noqa: E402

C = P.COLORS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------- 재질
def materials():
    M = {}
    M['skin'] = principled('skin', C['skin'], rough=0.55, sss=0.12, spec=0.3)
    M['hair'] = principled('hair', C['hair'], rough=0.42, spec=0.35)   # 웨이브 마루에 하이라이트가 맺혀 물결이 읽히게
    M['brow'] = principled('brow', C['brow'], rough=0.6)
    M['mouth'] = principled('mouth', C['mouth'], rough=0.5)
    M['eye_hi'] = emission('eye_hi', C['eye_hi'], 2.5)
    # 눈: 위는 거의 검정, 아래로 갈색 홍채가 비친다
    e = principled('eye', C['eye'], rough=0.12, coat=1.0, spec=0.7)
    nt = e.node_tree
    tc = node(nt, 'ShaderNodeTexCoord')
    sep = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = node(nt, 'ShaderNodeValToRGB')
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = (*hex2lin(C['iris']), 1)
    ramp.color_ramp.elements[1].position = 0.52
    ramp.color_ramp.elements[1].color = (*hex2lin(C['eye']), 1)
    nt.links.new(ramp.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    M['eye'] = e
    return M


def face_material(blush_center):
    m = principled('skin_face', C['skin'], rough=0.55, sss=0.12, spec=0.3)
    nt = m.node_tree
    mask = blob_mask(nt, blush_center, P.FACE['blush_r'])
    k = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(mask, k.inputs[0])
    k.inputs[1].default_value = 0.55
    col = mix_color(nt, k.outputs[0], (*hex2lin(C['skin']), 1), (*hex2lin(C['blush']), 1))
    # 두피(머리카락 다발 틈)는 어둡게: 정면 이마 위쪽은 높게, 옆·뒤는 낮게 시작
    sep = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(rest_coords(nt), sep.inputs[0])
    tilt = node(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD')
    nt.links.new(sep.outputs['Y'], tilt.inputs[0])
    tilt.inputs[1].default_value = 0.35
    nt.links.new(sep.outputs['Z'], tilt.inputs[2])
    sc = node(nt, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    nt.links.new(tilt.outputs[0], sc.inputs['Value'])
    sc.inputs['From Min'].default_value, sc.inputs['From Max'].default_value = P.HEAD['scalp_z']
    col = mix_color(nt, sc.outputs['Result'], col, (*hex2lin(C['scalp']), 1))
    nt.links.new(col, nt.nodes['Principled BSDF'].inputs['Base Color'])
    return m


# ---------------------------------------------------------------- 머리
def head_shape(q, p):
    H = P.HEAD
    x, y, z = q
    x *= 1 + H['cheek'] * math.exp(-((p.z + 0.35) / 0.35) ** 2)
    x *= 1 - H['chin_taper'] * smoothstep(-0.45, -1.0, p.z)
    y *= lerp(1.0, H['face_flat'], smoothstep(0.0, -0.6, p.y)) if p.y < 0 else 1.03
    return (x, y, z)


HAIRLINE = [  # |방위각|(rad) → 머리선 높이(단위 구 z). 0=정면, pi/2=귀, pi=뒤. 귀 위는 짧게 쳐서 귀가 다 보이게
    (0.00, 0.55), (0.35, 0.51), (0.62, 0.40), (0.95, 0.22), (1.15, -0.05), (1.30, 0.10), (1.42, 0.22),
    (1.62, 0.26), (1.85, 0.18), (2.05, -0.10), (2.60, -0.45), (3.15, -0.55)]


def interp(table, x):
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            return lerp(y0, y1, smoothstep(x0, x1, x))
    return table[-1][1]


def hair_shape(q, p):
    Hh = P.HAIR
    hq = Vector(head_shape(q, p))
    radial = hq.normalized()
    th = Hh['base'] + Hh['top'] * smoothstep(0.1, 0.95, p.z) + Hh['back'] * smoothstep(0.0, 0.8, p.y)
    th += Hh['swoop_side'] * smoothstep(-0.2, 0.7, Hh['sweep'] * p.x) * smoothstep(0.2, 0.8, p.z)   # 넘기는 쪽이 더 풍성
    hl = interp(HAIRLINE, abs(math.atan2(p.x, -p.y)))
    th -= (Hh['base'] + 0.06) * smoothstep(hl + 0.03, hl - 0.07, p.z)
    return hq + radial * th


def eye_smile(q, p):
    F = P.FACE
    w, h, d = F['eye_w'], F['eye_h'], F['eye_d']
    x, y, z = q
    zb = -h / 2 + F['eye_smile'] * h * (1 - min(1.0, (2 * x / w) ** 2))
    t = smoothstep(-0.01, 0.03, zb - z)
    return (x, y + t * d * 0.9, z)


def surface_points(tree, pts, push):
    out = []
    for (x, z) in pts:
        loc, nor = hit(tree, (x, -2.0, z), (0, 1, 0))
        out.append(loc + nor * push)
    return out


def build_head(c, M):
    H, F = P.HEAD, P.FACE
    head = ellipsoid('head', H['center'], H['radius'], c, cuts=6, levels=2, fn=head_shape)
    tree = bvh(head)
    # 볼 터치 중심은 얼굴 표면 위
    loc, _ = hit(tree, (F['blush_x'], -2, F['blush_z']), (0, 1, 0))
    set_mat(head, face_material((F['blush_x'], loc.y, F['blush_z'])))

    parts = {'head': head}
    for side, tag in ((-1, 'R'), (1, 'L')):
        x = side * F['eye_x']
        loc, nor = hit(tree, (x, -2, F['eye_z']), (0, 1, 0))
        eye = ellipsoid(f'eye.{tag}', (0, 0, 0), (F['eye_w'] / 2, F['eye_d'] / 2, F['eye_h'] / 2), c, cuts=4,
                        fn=eye_smile)
        place(eye, loc, nor, push=-F['eye_d'] * 0.22)
        set_mat(eye, M['eye'])
        parts[f'eye.{tag}'] = eye
        # 하이라이트 두 개(큰 것 위 바깥, 작은 것 아래 안쪽)
        for i, (hx, hz, s) in enumerate(((0.32, 0.36, F['hi_s'][0]), (-0.36, 0.04, F['hi_s'][1]))):
            hw, hh, hd = F['eye_w'] / 2, F['eye_h'] / 2, F['eye_d'] / 2
            lx, lz = hx * hw * side, hz * hh
            ly = -hd * math.sqrt(max(0.0, 1 - (lx / hw) ** 2 - (lz / hh) ** 2)) - 0.002
            hl = ellipsoid(f'eye_hi{i}.{tag}', (0, 0, 0), (hw * s, 0.004, hw * s), c, cuts=2)
            hl.parent = eye
            hl.location = (lx, ly, lz)
            set_mat(hl, M['eye_hi'])
            parts[f'eye_hi{i}.{tag}'] = hl  # 빠지면 리그 굽기 때 부모만 굽혀 바닥 원점에 남는다
        # 윗눈꺼풀 선: 눈 윗테두리를 따라, 바깥 끝은 살짝 길게 빠진다
        w, h = F['eye_w'], F['eye_h']
        lid = []
        for i in range(11):
            u = i / 10
            lx = lerp(-0.46 * w, 0.55 * w, u)
            ax = abs(lx)
            if ax <= w / 2 * F['lid_fit']:
                lz = h / 2 * F['lid_fit'] * math.sqrt(max(0.0, 1 - (ax / (w / 2 * F['lid_fit'])) ** 2)) + 0.003
            else:
                lz = 0.003 + (ax - w / 2 * F['lid_fit']) * F['lid_flick']   # 바깥 끝 날개
            wp = eye.matrix_world @ Vector((side * lx, -F['eye_d'], lz))
            loc2, nor2 = hit(tree, (wp.x, -2.0, wp.z), (0, 1, 0))
            lid.append(loc2 + nor2 * 0.003)
        lidob = sweep(f'lid.{tag}', lid, lambda u: F['lid_r'] * min(1.0, 0.25 + 2.5 * u, 0.2 + 3.5 * (1 - u)),
                      c, sides=8, segs=24, aspect=0.6, tip=False,
                      up=lambda p, u: (p - Vector(H['center'])).normalized())
        set_mat(lidob, M['brow'])
        parts[f'lid.{tag}'] = lidob
        # 눈썹
        xs = [side * lerp(F['brow_x0'], F['brow_x1'], u / 6) for u in range(7)]
        zs = [F['brow_z'] + F['brow_arch'] * math.sin(math.pi * u / 6) - 0.006 * (u / 6) for u in range(7)]
        pts = surface_points(tree, list(zip(xs, zs)), F['brow_r'] * 0.4)
        brow = sweep(f'brow.{tag}', pts, lambda u: F['brow_r'] * (1.05 - 0.4 * u) * min(1.0, 0.35 + 3 * u, 0.35 + 3 * (1 - u)),
                     c, sides=8, segs=16, aspect=0.55, tip=False,
                     up=lambda p, u: (p - Vector(H['center'])).normalized())
        set_mat(brow, M['brow'])
        parts[f'brow.{tag}'] = brow
        # 귀
        ear = ellipsoid(f'ear.{tag}', (0, 0, 0), F['ear'], c, cuts=3)
        ear.location = (side * F['ear_x'], 0.03, F['ear_z'])
        ear.rotation_euler = (0.0, side * 0.15, 0.0)
        set_mat(ear, M['skin'])
        parts[f'ear.{tag}'] = ear
    # 표정 교체 부품: 눈웃음(^^) 호, 벌린 입 — 평소엔 뼈 크기 0 으로 숨긴다
    for side, tag in ((-1, 'R'), (1, 'L')):
        x0 = side * F['eye_x']
        arc = []
        for i in range(9):
            u = i / 8
            dx = lerp(-F['eye_w'] * 0.55, F['eye_w'] * 0.55, u)
            dz = -0.012 + 0.042 * (1 - (2 * u - 1) ** 2)
            arc.append((x0 + dx, F['eye_z'] + dz))
        pts = surface_points(tree, arc, 0.006)
        hap = sweep(f'eye_happy.{tag}', pts, lambda u: 0.0105 * min(1.0, 0.35 + 3 * u, 0.35 + 3 * (1 - u)),
                    c, sides=8, segs=20, aspect=0.7, tip=False)
        set_mat(hap, M['brow'])
        parts[f'eye_happy.{tag}'] = hap
    loc, nor = hit(tree, (0, -2, F['mouth_z'] - 0.012), (0, 1, 0))
    ow = F['mouth_w'] * 0.42   # 벌린 입 폭은 다문 입에 맞춰
    mo = ellipsoid('mouth_open', (0, 0, 0), (ow, 0.016, 0.036), c, cuts=3,
                   fn=lambda q, p: (q.x, q.y, min(q.z, 0.006 + 0.004 * (1 - (q.x / ow) ** 2))))
    place(mo, loc, nor, push=-0.004)
    set_mat(mo, principled('mouth_in', C['mouth_in'], rough=0.5))
    tg = ellipsoid('tongue', (0, 0, 0), (ow * 0.52, 0.012, 0.012), c, cuts=2)
    tg.parent = mo
    tg.location = (0, -0.008, -0.022)
    set_mat(tg, principled('tongue', C['tongue'], rough=0.45))
    parts['mouth_open'], parts['tongue'] = mo, tg
    # 입: 다문 미소
    mx = [lerp(-F['mouth_w'] / 2, F['mouth_w'] / 2, u / 8) for u in range(9)]
    mz = [F['mouth_z'] + F['mouth_curve'] * ((2 * u / 8 - 1) ** 2) for u in range(9)]
    pts = surface_points(tree, list(zip(mx, mz)), F['mouth_r'] * 0.3)
    mouth = sweep('mouth', pts, lambda u: F['mouth_r'] * min(1.0, 0.3 + 4 * u, 0.3 + 4 * (1 - u)),
                  c, sides=8, segs=20, aspect=0.8, tip=False)
    set_mat(mouth, M['mouth'])
    parts['mouth'] = mouth
    # 코
    loc, nor = hit(tree, (0, -2, F['nose_z']), (0, 1, 0))
    nose = ellipsoid('nose', (0, 0, 0), F['nose'], c, cuts=3)
    place(nose, loc, nor, push=-F['nose'][1] * F['nose_push'])
    set_mat(nose, M['skin'])
    parts['nose'] = nose
    return parts


# ---------------------------------------------------------------- 머리카락
def sph(az, el, r):
    hc = Vector(P.HEAD['center'])
    a, e = math.radians(az), math.radians(el)
    return hc + Vector((r * math.cos(e) * math.sin(a), -r * math.cos(e) * math.cos(a), r * math.sin(e)))


def build_hair(c, M, head):
    Hh = P.HAIR
    hc = Vector(P.HEAD['center'])
    up = lambda p, u: (p - hc).normalized()  # noqa: E731
    mass = ellipsoid('hair_mass', P.HEAD['center'], P.HEAD['radius'], c, cuts=8, levels=2, fn=hair_shape)
    set_mat(mass, M['hair'])
    parts = {'hair_mass': mass}
    # 다발: (방위°, 고도°, 띄움) — 띄움은 머리 덩어리 표면에서 바깥으로. 방위 0=정면, +는 캐릭터 왼쪽(+X)
    mtree, htree = bvh(mass), bvh(head)
    hcv = Vector(P.HEAD['center'])

    def on_mass(az, el, lift):
        d = (sph(az, el, 1.0) - hcv).normalized()
        r = 0.0
        for t in (mtree, htree):  # 깎인 앞이마에서는 머리 표면 기준
            loc, _, _, _ = t.ray_cast(hcv, d)
            if loc:
                r = max(r, (loc - hcv).length)
        return hcv + d * (r + lift)
    for name, (pts, w, asp) in P.HAIR_LOCKS.items():
        xyz = [on_mass(a, e, l) for a, e, l in pts]
        ob = sweep(name, xyz, lambda u, w=w: w * (0.6 + 0.4 * math.sin(math.pi * min(1.0, 0.2 + u))) * (1 - u) ** 0.5,
                   c, sides=12, segs=36, aspect=asp, up=up, tip=True)
        set_mat(ob, M['hair'])
        parts[name] = ob
    return parts


def build(target=None):
    c = target or coll('CHAR')
    M = materials()
    parts = {}
    parts.update(build_head(c, M))
    parts.update(build_hair(c, M, parts['head']))
    parts.update(build_body(c, M))
    M.update(prop_materials())
    parts.update(build_cape(c, M))
    parts.update(build_hat(c, M))
    sh, el, wr, d = arm_points(-1)
    parts.update(build_staff(c, M, wr + d * (P.BODY['hand'][2] * 0.85)))
    parts.update(build_badge(c, M, parts['torso']))
    for k in ('head', 'torso', 'tie', 'tie_knot'):
        add_rest(parts[k])
    return parts, M


if __name__ == '__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'build', 'model.blend'))
