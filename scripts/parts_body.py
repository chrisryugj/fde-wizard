"""몸: 정장 몸통(셔츠 V존은 셰이더), 넥타이, 라펠, 단추, 팔·손, 다리·구두."""
import math
from mathutils import Vector

import params as P
from lib import sweep, ellipsoid, principled, set_mat, bvh, hit, smoothstep, lerp, hex2lin
from shader import node, sock, mix_color, rest_coords

C = P.COLORS
B = P.BODY


def suit_material():
    """몸통 재질: 남색 정장 + 앞쪽 V 영역만 흰 셔츠."""
    m = principled('suit_torso', C['suit'], rough=0.7, spec=0.25, sheen=0.25)
    nt = m.node_tree
    sep = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(rest_coords(nt), sep.inputs[0])
    # V 폭 = (z - 바닥) * 기울기, |x| 가 그보다 작으면 셔츠
    zb = node(nt, 'ShaderNodeMath', operation='SUBTRACT')
    nt.links.new(sep.outputs['Z'], zb.inputs[0])
    zb.inputs[1].default_value = B['v_bottom']
    vw = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(zb.outputs[0], vw.inputs[0])
    vw.inputs[1].default_value = B['v_slope']
    ax = node(nt, 'ShaderNodeMath', operation='ABSOLUTE')
    nt.links.new(sep.outputs['X'], ax.inputs[0])
    d = node(nt, 'ShaderNodeMath', operation='SUBTRACT')
    nt.links.new(vw.outputs[0], d.inputs[0])
    nt.links.new(ax.outputs[0], d.inputs[1])
    edge = node(nt, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    nt.links.new(d.outputs[0], edge.inputs['Value'])
    edge.inputs['From Min'].default_value = 0.0
    edge.inputs['From Max'].default_value = 0.006
    front = node(nt, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    nt.links.new(sep.outputs['Y'], front.inputs['Value'])
    front.inputs['From Min'].default_value = 0.0
    front.inputs['From Max'].default_value = -0.08
    k = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(edge.outputs['Result'], k.inputs[0])
    nt.links.new(front.outputs['Result'], k.inputs[1])
    col = mix_color(nt, k.outputs[0], (*hex2lin(C['suit']), 1), (*hex2lin(C['shirt']), 1))
    nt.links.new(col, nt.nodes['Principled BSDF'].inputs['Base Color'])
    rough = node(nt, 'ShaderNodeMapRange')
    nt.links.new(k.outputs[0], rough.inputs['Value'])
    rough.inputs['To Min'].default_value = 0.7
    rough.inputs['To Max'].default_value = 0.45
    nt.links.new(rough.outputs['Result'], nt.nodes['Principled BSDF'].inputs['Roughness'])
    return m


def tie_material():
    """남색 넥타이 + 흰 잔점(사진 속 넥타이 무늬)."""
    m = principled('tie', C['tie'], rough=0.35, spec=0.5, sheen=0.2)
    nt = m.node_tree
    sep = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(rest_coords(nt), sep.inputs[0])
    comb = node(nt, 'ShaderNodeCombineXYZ')
    nt.links.new(sep.outputs['X'], comb.inputs['X'])
    nt.links.new(sep.outputs['Z'], comb.inputs['Y'])
    sc = node(nt, 'ShaderNodeVectorMath', operation='SCALE')
    nt.links.new(comb.outputs[0], sc.inputs[0])
    sc.inputs['Scale'].default_value = 1 / B['tie_dot_gap']
    fr = node(nt, 'ShaderNodeVectorMath', operation='FRACTION')
    nt.links.new(sc.outputs[0], fr.inputs[0])
    sub = node(nt, 'ShaderNodeVectorMath', operation='SUBTRACT')
    nt.links.new(fr.outputs[0], sub.inputs[0])
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    ln = node(nt, 'ShaderNodeVectorMath', operation='LENGTH')
    nt.links.new(sub.outputs[0], ln.inputs[0])
    dot = node(nt, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    nt.links.new(ln.outputs['Value'], dot.inputs['Value'])
    dot.inputs['From Min'].default_value = 0.17
    dot.inputs['From Max'].default_value = 0.12
    col = mix_color(nt, dot.outputs['Result'], (*hex2lin(C['tie']), 1), (*hex2lin(C['tie_dot']), 1))
    nt.links.new(col, nt.nodes['Principled BSDF'].inputs['Base Color'])
    return m


def torso_shape(q, p):
    x, y, z = q
    x *= 1 - 0.13 * smoothstep(0.2, 1.0, p.z) + 0.05 * smoothstep(-0.2, -1.0, p.z)
    y *= 1 - 0.10 * smoothstep(0.3, 1.0, p.z)
    z *= lerp(1.0, 0.72, smoothstep(-0.55, -1.0, p.z))
    return (x, y, z)


def arm_points(side):
    sx, sy, sz = B['shoulder']
    a = math.radians(B['arm_angle'])
    d = Vector((side * math.sin(a), 0.0, -math.cos(a)))
    sh = Vector((side * sx, sy, sz))
    el = sh + d * B['upper']
    wr = el + d * B['fore']
    return sh, el, wr, d


def build_body(c, M):
    parts = {}
    torso = ellipsoid('torso', B['torso_center'], B['torso_r'], c, cuts=6, levels=2, fn=torso_shape)
    set_mat(torso, suit_material())
    parts['torso'] = torso
    tree = bvh(torso)
    neck = sweep('neck', [(0, 0.0, B['neck_z'][0]), (0, 0.0, B['neck_z'][1])], B['neck_r'], c,
                 sides=12, segs=4, tip=False, levels=2)
    set_mat(neck, M['skin'])
    parts['neck'] = neck

    def front(x, z, push):
        loc, nor = hit(tree, (x, -2.0, z), (0, 1, 0))
        if loc is None:  # 몸통 꼭대기 근처는 위·앞에서 비스듬히
            o = Vector((x, -1.5, z + 1.5))
            loc, nor = hit(tree, o, Vector((x * 0.5, 0.0, z - 0.15)) - o)
        return loc + nor * push

    # 셔츠 깃(작은 흰 삼각)
    shirt = principled('shirt', C['shirt'], rough=0.45, spec=0.3)
    for side, tag in ((-1, 'R'), (1, 'L')):
        pts = [front(side * 0.035, 1.0, 0.012), front(side * 0.075, 0.972, 0.012), front(side * 0.06, 0.93, 0.01)]
        col = sweep(f'collar.{tag}', pts, lambda u: 0.022 * (1 - 0.6 * u), c, sides=8, segs=10, aspect=0.35, tip=True)
        set_mat(col, shirt)
        parts[f'collar.{tag}'] = col
        # 라펠: V 가장자리를 따라 살짝 도톰한 띠
        z0, z1 = B['v_bottom'], B['torso_center'][2] + B['torso_r'][2] * 0.82
        lap = [front(side * (B['v_slope'] * (lerp(z1, z0, u / 6) - z0) + 0.012), lerp(z1, z0, u / 6), 0.006) for u in range(7)]
        lp = sweep(f'lapel.{tag}', lap, lambda u: 0.022 * (1 - 0.5 * u), c, sides=8, segs=20, aspect=0.4, tip=False)
        set_mat(lp, principled('lapel', C['suit_hi'], rough=0.6, spec=0.3, sheen=0.25))
        parts[f'lapel.{tag}'] = lp

    # 넥타이: 매듭 → 좁은 목 → 넓어지다 뾰족한 끝
    tz = [0.975, 0.95, 0.88, 0.80, 0.735, 0.71]
    tie_pts = [front(0.0, z, 0.016) for z in tz]
    tie = sweep('tie', tie_pts, lambda u: lerp(0.017, 0.040, smoothstep(0.0, 0.85, u)) * (1.0 if u < 0.9 else 1 - (u - 0.9) * 6),
                c, sides=8, segs=24, aspect=0.28, tip=True, up=lambda p, u: (0, -1, 0))
    tmat = tie_material()
    set_mat(tie, tmat)
    knot = ellipsoid('tie_knot', (0, 0, 0), (0.026, 0.018, 0.022), c, cuts=3)
    knot.location = front(0.0, 0.982, 0.02)
    set_mat(knot, tmat)
    parts['tie'], parts['tie_knot'] = tie, knot
    # 단추 둘
    for i, z in enumerate((0.64, 0.55)):
        b = ellipsoid(f'button{i}', (0, 0, 0), (0.016, 0.008, 0.016), c, cuts=2)
        b.location = front(0.0, z, 0.002)
        set_mat(b, principled('button', C['button'], rough=0.3, spec=0.6))
        parts[f'button{i}'] = b

    # 팔(A 포즈) + 셔츠 소매 끝 + 손
    sleeve_mat = principled('sleeve', C['suit'], rough=0.7, spec=0.25, sheen=0.25)
    for side, tag in ((-1, 'R'), (1, 'L')):
        sh, el, wr, d = arm_points(side)
        r0, r1 = B['sleeve_r']
        arm = sweep(f'sleeve.{tag}', [sh - d * 0.06, sh + d * 0.06, el, wr - d * 0.012],
                    lambda u: lerp(r0, r1, u), c, sides=12, segs=18, tip=False)
        set_mat(arm, sleeve_mat)
        cuff = sweep(f'cuff.{tag}', [wr - d * 0.03, wr + d * 0.012], r1 * 0.86, c, sides=12, segs=4, tip=False)
        set_mat(cuff, shirt)
        hand = ellipsoid(f'hand.{tag}', (0, 0, 0), B['hand'], c, cuts=3)
        hand.location = wr + d * (B['hand'][2] * 0.85)
        hand.rotation_euler = (0, side * math.radians(B['arm_angle']), 0)
        set_mat(hand, M['skin'])
        thumb = ellipsoid(f'thumb.{tag}', (0, 0, 0), (0.019, 0.019, 0.032), c, cuts=2)
        thumb.parent = hand
        thumb.location = (-side * 0.012, -0.038, 0.012)
        thumb.rotation_euler = (0.5, 0, side * 0.3)
        set_mat(thumb, M['skin'])
        parts.update({f'sleeve.{tag}': arm, f'cuff.{tag}': cuff, f'hand.{tag}': hand, f'thumb.{tag}': thumb})

    # 다리 + 구두
    trouser = principled('trouser', C['suit'], rough=0.7, spec=0.25, sheen=0.25)
    for side, tag in ((-1, 'R'), (1, 'L')):
        hx, hy, hz = B['hip']
        leg = sweep(f'leg.{tag}', [(side * hx, hy, hz + 0.06), (side * hx, hy, 0.25), (side * hx, hy, 0.10)],
                    lambda u: lerp(B['leg_r'][0], B['leg_r'][1], u), c, sides=12, segs=10, tip=False)
        set_mat(leg, trouser)
        sx_, sy_, sz_ = B['shoe']
        shoe = ellipsoid(f'shoe.{tag}', (0, 0, 0), B['shoe'], c, cuts=4,
                         fn=lambda q, p: (q.x, q.y, q.z * (0.55 if p.z < 0 else 1.0)))
        shoe.location = (side * hx, B['shoe_fwd'], sz_ * 0.55)
        set_mat(shoe, principled('shoe', C['shoe'], rough=0.3, spec=0.6, coat=0.4))
        parts[f'leg.{tag}'], parts[f'shoe.{tag}'] = leg, shoe
    return parts
