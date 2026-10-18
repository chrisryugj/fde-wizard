"""공공AX 영상 세트: 노을 별하늘, 떠 있는 광진구청 섬, 미니 구청, 소품(문서 탑·데이터 카드·유령·법령 책·동네 지도·작은 섬)."""
import math
import random
import bpy
import bmesh
from mathutils import Vector

from lib import coll, principled, emission, bm_obj, ellipsoid, sweep, subsurf, hex2lin
from shader import node, sock, mix_color
from set_props import box
import fx


# ---------------------------------------------------------------- 하늘
def sky(top='#121A4A', mid='#3B3E8F', horizon='#F4A96A', stars=1.0, strength=1.0):
    w = bpy.data.worlds.get('W') or bpy.data.worlds.new('W')
    bpy.context.scene.world = w
    nt = w.node_tree
    nt.nodes.clear()
    out = node(nt, 'ShaderNodeOutputWorld')
    bg = node(nt, 'ShaderNodeBackground')
    tc = node(nt, 'ShaderNodeTexCoord')
    sep = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    zz = node(nt, 'ShaderNodeMapRange')
    nt.links.new(sep.outputs['Z'], zz.inputs['Value'])
    zz.inputs['From Min'].default_value = -1.0
    zz.inputs['From Max'].default_value = 1.0
    ramp = node(nt, 'ShaderNodeValToRGB')
    nt.links.new(zz.outputs['Result'], ramp.inputs['Fac'])
    els = ramp.color_ramp.elements  # 0.5 = 지평선
    els[0].position, els[0].color = 0.30, (*hex2lin('#231E55'), 1)
    els[1].position, els[1].color = 0.74, (*hex2lin(top), 1)
    for pos, col in ((0.46, '#6B4C93'), (0.50, horizon), (0.525, '#C46F8E'), (0.575, mid)):
        e = els.new(pos)
        e.color = (*hex2lin(col), 1)
    # 별: 보로노이 점 중 밝은 것만
    vor = node(nt, 'ShaderNodeTexVoronoi', feature='F1')
    vor.inputs['Scale'].default_value = 160.0
    nt.links.new(tc.outputs['Generated'], vor.inputs['Vector'])
    st = node(nt, 'ShaderNodeMapRange')
    nt.links.new(vor.outputs['Distance'], st.inputs['Value'])
    st.inputs['From Min'].default_value = 0.0
    st.inputs['From Max'].default_value = 0.045
    st.inputs['To Min'].default_value = 6.0 * stars
    st.inputs['To Max'].default_value = 0.0
    hi = node(nt, 'ShaderNodeMapRange')
    nt.links.new(sep.outputs['Z'], hi.inputs['Value'])
    hi.inputs['From Min'].default_value = 0.04
    hi.inputs['From Max'].default_value = 0.20
    mul = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(st.outputs['Result'], mul.inputs[0])
    nt.links.new(hi.outputs['Result'], mul.inputs[1])
    add = node(nt, 'ShaderNodeMix', data_type='RGBA', blend_type='ADD')
    nt.links.new(ramp.outputs['Color'], sock(add.inputs, 'A', 'RGBA'))
    nt.links.new(mul.outputs[0], sock(add.inputs, 'Factor', 'VALUE'))
    sock(add.inputs, 'B', 'RGBA').default_value = (1.0, 0.95, 0.85, 1)
    nt.links.new(sock(add.outputs, 'Result', 'RGBA'), bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    return w


# ---------------------------------------------------------------- 섬 + 구청
def island(c=None, r=2.7):
    c = c or coll('SET')
    stone = principled('plaza', '#DCD2C1', rough=0.75, spec=0.25)
    rim = principled('rim', '#C9BBA6', rough=0.7)
    grass = principled('grass', '#7DBE7A', rough=0.8, sheen=0.4)
    rock = principled('rock', '#7A6A5E', rough=0.9)
    top = sweep('plaza', [(0, 0, -0.12), (0, 0, 0.0)], r, c, sides=64, segs=4, tip=False, levels=1)
    top.data.materials.append(stone)
    ring = sweep('plaza_rim', [(r * math.cos(a), r * math.sin(a), 0.02) for a in
                               [2 * math.pi * k / 64 for k in range(65)]], 0.06, c, sides=8, segs=130, tip=False, cap0=False)
    ring.data.materials.append(rim)
    lawn = sweep('lawn', [(0, 0, -0.30), (0, 0, -0.12)], r + 0.08, c, sides=64, segs=4, tip=False, levels=1)
    lawn.data.materials.append(grass)
    rnd = random.Random(2)
    under = ellipsoid('under', (0, 0, -0.32), (r * 1.0, r * 1.0, 1.9), c, cuts=6,
                      fn=lambda q, p: (q.x * (1 + 0.08 * math.sin(p.x * 9 + p.y * 7)), q.y * (1 + 0.08 * math.cos(p.y * 8)),
                                       min(q.z, 0.0) * (1 + 0.15 * math.sin(p.x * 5 + p.y * 3))))
    under.data.materials.append(rock)
    # 바닥 무늬: 동심원 타일 선
    tile = principled('tile_line', '#D8CDBB', rough=0.8)
    for k, rr in enumerate((0.9, 1.7, 2.4)):
        t = sweep(f'tile{k}', [(rr * math.cos(a), rr * math.sin(a), 0.003) for a in [2 * math.pi * j / 64 for j in range(65)]],
                  0.012, c, sides=6, segs=130, aspect=0.25, tip=False, cap0=False, levels=0)
        t.data.materials.append(tile)
    for i in range(7):  # 덤불
        a = rnd.uniform(0, 2 * math.pi)
        if -2.2 < a < -0.9:
            continue
        b = ellipsoid(f'bush{i}', (math.cos(a) * (r - 0.25), math.sin(a) * (r - 0.25), 0.12), (0.22, 0.22, 0.18), c, cuts=3)
        b.data.materials.append(grass)
    return top


def windows_mat(name, wall='#F3EEE4', glass='#2A3A66', lit='#FFD98A', lit_strength=0.0):
    """벽돌 무늬로 창 격자를 만들고, 불 켜짐(창 발광) 세기를 노드 값으로 둔다."""
    m = principled(name, wall, rough=0.7)
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tc = node(nt, 'ShaderNodeTexCoord')
    sp = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sp.inputs[0])
    xy = node(nt, 'ShaderNodeMath', operation='ADD')
    nt.links.new(sp.outputs['X'], xy.inputs[0])
    nt.links.new(sp.outputs['Y'], xy.inputs[1])
    cb = node(nt, 'ShaderNodeCombineXYZ')
    nt.links.new(xy.outputs[0], cb.inputs['X'])
    nt.links.new(sp.outputs['Z'], cb.inputs['Y'])
    br = node(nt, 'ShaderNodeTexBrick')
    nt.links.new(cb.outputs[0], br.inputs['Vector'])
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Brick Width'].default_value = 0.16
    br.inputs['Row Height'].default_value = 0.15
    br.inputs['Mortar Size'].default_value = 0.045
    br.inputs['Color1'].default_value = (1, 1, 1, 1)
    br.inputs['Color2'].default_value = (1, 1, 1, 1)
    br.inputs['Mortar'].default_value = (0, 0, 0, 1)
    br.offset = 0.0
    br.squash = 1.0
    inv = node(nt, 'ShaderNodeMath', operation='SUBTRACT')
    inv.inputs[0].default_value = 1.0
    nt.links.new(br.outputs['Fac'], inv.inputs[1])
    col = mix_color(nt, inv.outputs[0], (*hex2lin(wall), 1), (*hex2lin(glass), 1))
    nt.links.new(col, b.inputs['Base Color'])
    b.inputs['Emission Color'].default_value = (*hex2lin(lit), 1)
    v = node(nt, 'ShaderNodeValue', name='lit', label='lit')
    v.outputs[0].default_value = lit_strength
    mul = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(inv.outputs[0], mul.inputs[0])
    nt.links.new(v.outputs[0], mul.inputs[1])
    nt.links.new(mul.outputs[0], b.inputs['Emission Strength'])
    return m


def gu_office(loc=(0.0, 2.05, 0.0), c=None, scale=1.0, sign='광진구청'):
    """미니 구청: 본관 + 지붕 + 현관 + 간판 + 깃대."""
    c = c or coll('SET')
    x, y, z = loc
    s = scale
    m = windows_mat('office_wall')
    body = box('office', c, (1.9 * s, 0.7 * s, 0.95 * s), (x, y, z + 0.475 * s), 0, m, 0.02)
    roof = box('office_roof', c, (2.05 * s, 0.82 * s, 0.08 * s), (x, y, z + 0.99 * s), 0,
               principled('roof', '#3F5A8A', rough=0.6), 0.02)
    porch = box('office_porch', c, (0.6 * s, 0.25 * s, 0.4 * s), (x, y - 0.42 * s, z + 0.2 * s), 0,
                principled('porch', '#DCD3C4', rough=0.7), 0.01)
    door = box('office_door', c, (0.32 * s, 0.02 * s, 0.3 * s), (x, y - 0.55 * s, z + 0.15 * s), 0,
               principled('door', '#2E4B7A', rough=0.4, coat=0.5), 0.005)
    plate = box('office_sign', c, (0.9 * s, 0.03 * s, 0.17 * s), (x, y - 0.37 * s, z + 0.82 * s), 0,
                principled('signplate', '#1E3A8A', rough=0.4), 0.01)
    t = fx.text3d('office_signtext', sign, 0.11 * s, emission('signtxt', '#FFFFFF', 1.5), c, extrude=0.004)
    t.location = (x, y - 0.39 * s, z + 0.82 * s)
    t.rotation_euler = (math.pi / 2, 0, 0)
    pole = sweep('flagpole', [(x + 1.15 * s, y - 0.2, z), (x + 1.15 * s, y - 0.2, z + 1.5 * s)], 0.015, c, sides=8, segs=4, tip=False)
    pole.data.materials.append(principled('pole', '#D8DEE8', rough=0.3, metal=1.0))
    flag = box('flag', c, (0.36 * s, 0.01, 0.22 * s), (x + 1.34 * s, y - 0.2, z + 1.36 * s), 0,
               principled('flagc', '#FFD23F', rough=0.6), 0.003)
    return [body, roof, porch, door, plate, t, pole, flag]


# ---------------------------------------------------------------- 데이터 카드·문서 낱장
def sheet(name, c, mat, w=0.30, h=0.40):
    return box(name, c, (w, 0.004, h), (0, 0, 0), 0, mat, 0.002)


def data_card(name, c, color='#7FE3FF'):
    """빛나는 데이터 카드: 테두리 + 표 줄 세 개."""
    frame = principled('card_glass', '#173062', rough=0.3, emit='#1F4A9A', emit_strength=0.6)
    line = emission(f'cardline_{color}', color, 5.0)
    root = box(name, c, (0.26, 0.012, 0.18), (0, 0, 0), 0, frame, 0.012)
    for i, zz in enumerate((0.045, 0.0, -0.045)):
        ln = box(f'{name}_l{i}', c, (0.20 if i == 0 else 0.15, 0.004, 0.014), (0 if i == 0 else -0.025, -0.009, zz), 0, line, 0.002)
        ln.parent = root
    edge = box(f'{name}_e', c, (0.27, 0.004, 0.006), (0, -0.008, 0.086), 0, line, 0.0)
    edge.parent = root
    return root


def portal(name, loc, c=None, r=0.55, color='cyan'):
    """세로로 선 빛 고리(문서가 지나가면 데이터가 된다)."""
    c = c or coll('FX')
    em = fx.fx_mat(color)
    ring = sweep(name, [(r * math.cos(a), 0, r * math.sin(a)) for a in [2 * math.pi * k / 48 for k in range(49)]],
                 0.035, c, sides=8, segs=96, tip=False, cap0=False)
    ring.data.materials.append(em)
    inner = ellipsoid(f'{name}_disc', (0, 0, 0), (r * 0.95, 0.004, r * 0.95), c, cuts=4)
    inner.data.materials.append(emission(f'{name}_discmat', '#9FE8FF', 0.6))
    inner.parent = ring
    ring.location = loc
    ring.visible_shadow = False
    inner.visible_shadow = False
    return ring


# ---------------------------------------------------------------- 유령(환각) + 두루마리
def ghost(name='ghost', c=None):
    c = c or coll('FX')
    white = principled('ghost_mat', '#F4F6FF', rough=0.4, emit='#DDE6FF', emit_strength=0.25)
    dark = principled('ghost_eye', '#1B1F3A', rough=0.2, coat=0.8)
    body = ellipsoid(name, (0, 0, 0), (0.24, 0.22, 0.30), c, cuts=5,
                     fn=lambda q, p: (q.x, q.y, q.z if p.z > -0.2 else q.z + 0.05 * math.sin(math.atan2(p.y, p.x) * 6)))
    body.data.materials.append(white)
    parts = [body]
    for side in (-1, 1):
        e = ellipsoid(f'{name}_eye{side}', (side * 0.075, -0.2, 0.06), (0.03, 0.012, 0.042), c, cuts=2)
        e.data.materials.append(dark)
        e.parent = body
        a = ellipsoid(f'{name}_arm{side}', (side * 0.25, -0.02, -0.04), (0.07, 0.05, 0.045), c, cuts=2)
        a.data.materials.append(white)
        a.parent = body
        parts += [e, a]
    m = ellipsoid(f'{name}_mouth', (0.0, -0.215, -0.03), (0.035, 0.01, 0.02), c, cuts=2)
    m.data.materials.append(principled('ghost_mouth', '#5A1F3A', rough=0.4))
    m.parent = body
    parts.append(m)
    return body, parts


def scroll(name, text, c=None, w=0.5, h=0.34):
    c = c or coll('FX')
    paper = principled('scroll_paper', '#FFF6DE', rough=0.7)
    wood = principled('scroll_rod', '#9C6B44', rough=0.5)
    sh = box(name, c, (w, 0.006, h), (0, 0, 0), 0, paper, 0.004)
    for z in (h / 2, -h / 2):
        rod = sweep(f'{name}_rod{z > 0}', [(-w / 2 - 0.04, 0, z), (w / 2 + 0.04, 0, z)], 0.022, c, sides=10, segs=4, tip=False)
        rod.data.materials.append(wood)
        rod.parent = sh
    t = fx.text3d(f'{name}_t', text, 0.065, principled('ink', '#3A2A60', rough=0.5), c, extrude=0.002)
    t.location = (0, -0.006, 0.03)
    t.rotation_euler = (math.pi / 2, 0, 0)
    t.parent = sh
    return sh


def law_book(name='lawbook', c=None, w=0.72, d=0.52, t=0.14):
    """가로로 누운 큰 법령 책: 아래 표지+속지는 고정, 위 표지는 hinge 빈 객체로 연다."""
    c = c or coll('FX')
    cover = principled('book_cover', '#8C1D2C', rough=0.45, coat=0.4)
    pages = principled('book_pages', '#FBF5E6', rough=0.8)
    gold = bpy.data.materials.get('gold') or principled('gold', '#F2BE45', rough=0.28, metal=1.0)
    root = bpy.data.objects.new(name, None)
    c.objects.link(root)
    base = box(f'{name}_base', c, (w, d, 0.03), (0, 0, 0.015), 0, cover, 0.01)
    blk = box(f'{name}_pages', c, (w * 0.96, d * 0.94, t - 0.05), (0, 0, 0.03 + (t - 0.05) / 2), 0, pages, 0.006)
    hinge = bpy.data.objects.new(f'{name}_hinge', None)
    c.objects.link(hinge)
    hinge.location = (-w / 2, 0, t - 0.01)
    lid = box(f'{name}_lid', c, (w, d, 0.03), (w / 2, 0, 0.0), 0, cover, 0.01)
    lid.parent = hinge
    title = fx.text3d(f'{name}_title', '법령', 0.18, gold, c, extrude=0.008)
    title.location = (w / 2, 0, 0.018)
    title.parent = hinge
    band = box(f'{name}_band', c, (0.05, d * 1.01, 0.034), (w * 0.18, 0, 0.0), 0, gold, 0.004)
    band.parent = hinge
    for o in (base, blk, hinge):
        o.parent = root
    return root, hinge


# ---------------------------------------------------------------- 동네 지도(광진 디오라마)
def district(name='district', c=None, seed=3, radius=2.3):
    """작은 건물 블록 + 한강 띠 + 아차산 언덕. 블록은 (객체, 최종 높이) 목록으로 돌려 솟아오르게 한다."""
    c = c or coll('SET')
    rnd = random.Random(seed)
    river = box(f'{name}_river', c, (4.1, 0.8, 0.02), (0, -1.62, 0.012), 0.0,
                principled('river', '#5FA8E8', rough=0.15, spec=0.8, coat=0.6), 0.01)
    hills = []
    hmat = principled('hill', '#79B86F', rough=0.8, sheen=0.4)
    for i, (x, y, s) in enumerate(((1.75, 1.15, 0.55), (2.15, 0.55, 0.42), (1.35, 1.65, 0.38))):
        h = ellipsoid(f'{name}_hill{i}', (x, y, 0.0), (s, s, s * 0.7), c, cuts=4,
                      fn=lambda q, p: (q.x, q.y, max(q.z, 0.0)))
        h.data.materials.append(hmat)
        hills.append(h)
    walls = [windows_mat(f'bld{i}', wall=w) for i, w in enumerate(('#F1ECE2', '#E3E8F0', '#F3E4D3', '#E6EFE6'))]
    blocks = []
    for i in range(46):
        for _ in range(30):
            x, y = rnd.uniform(-radius, radius), rnd.uniform(-radius, radius)
            if math.hypot(x, y) > radius or math.hypot(x, y) < 0.75:
                continue
            if y < -1.1:  # 강
                continue
            if math.hypot(x - 1.75, y - 1.15) < 0.75:  # 언덕
                continue
            break
        hgt = rnd.choice((0.18, 0.25, 0.32, 0.45, 0.6, 0.8))
        wv, dv = rnd.uniform(0.16, 0.28), rnd.uniform(0.16, 0.28)
        b = box(f'{name}_b{i}', c, (wv, dv, hgt), (x, y, hgt / 2), rnd.choice((0, 0.0, 0.3)), rnd.choice(walls), 0.008)
        blocks.append((b, hgt))
    return river, hills, blocks


def pin(name, loc, color='#FF5E5E', c=None):
    c = c or coll('FX')
    m = emission(f'pin_{color}', color, 4.0)
    head = ellipsoid(name, (0, 0, 0.22), (0.06, 0.06, 0.06), c, cuts=3)
    head.data.materials.append(m)
    stem = sweep(f'{name}_stem', [(0, 0, 0.0), (0, 0, 0.18)], lambda u: 0.012 + 0.02 * u, c, sides=8, segs=4, tip=False)
    stem.data.materials.append(m)
    stem.parent = head
    head.location = loc
    head.visible_shadow = False
    stem.visible_shadow = False
    return head


def mini_island(name, loc, c=None, seed=1, lit_name='isl'):
    """먼 하늘의 작은 섬 + 작은 집(불 켜질 창)."""
    c = c or coll('SET')
    rnd = random.Random(seed)
    top = sweep(f'{name}_top', [(0, 0, -0.06), (0, 0, 0.0)], 0.55, c, sides=24, segs=3, tip=False, levels=1)
    top.data.materials.append(principled('isl_grass', '#86C27E', rough=0.8))
    und = ellipsoid(f'{name}_under', (0, 0, -0.06), (0.55, 0.55, 0.5), c, cuts=4, fn=lambda q, p: (q.x, q.y, min(q.z, 0)))
    und.data.materials.append(principled('rock', '#7A6A5E', rough=0.9))
    m = windows_mat(f'{lit_name}_{name}', wall=rnd.choice(('#F1ECE2', '#E3E8F0', '#F3E4D3')))
    house = box(f'{name}_house', c, (0.42, 0.32, 0.36), (0, 0, 0.18), rnd.uniform(-0.4, 0.4), m, 0.01)
    roof = box(f'{name}_roof', c, (0.48, 0.38, 0.06), (0, 0, 0.39), house.rotation_euler.z, principled('roof', '#3F5A8A', rough=0.6), 0.01)
    for o in (und, house, roof):
        o.parent = top
    top.location = loc
    return top, m
