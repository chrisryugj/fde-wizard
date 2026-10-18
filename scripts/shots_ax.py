"""공공AX 영상(B): 떠 있는 광진구청 섬에서 마법사 FDE 가 일하는 6막."""
import math
import random
import bpy
from mathutils import Vector, Matrix

import params as P
import stage
import anim
import fx
import set_ax
from lib import coll, principled, emission
from set_props import doc_stack, box
from shots_common import rig, gem_pos, bone_pos, key_cam, hide_bear, flash_light, dim_lights, shake, viz_objects
from shots_making import cast_keys, idle_keys, finish, bear_rig, float_bear, key_bear_wave, pop, reorigin

R = math.radians


def ax_stage(samples=64):
    s = bpy.context.scene
    s.render.fps = 30
    stage.render_settings(1920, 1080, samples=samples)
    s.render.image_settings.compression = 15
    set_ax.sky()
    set_ax.island()
    set_ax.gu_office()
    L = {
        'moon': stage.area('moon', (-4.0, -5.0, 6.0), (0, 0, 1.0), 650, 4.0, '#D5DCFF'),
        'warm': stage.area('warm', (3.6, 4.2, 3.2), (0, 0, 1.2), 950, 2.5, '#FFB273'),
        'fill': stage.area('fill', (4.2, -4.0, 2.0), (0, 0, 1.0), 220, 4.0, '#A9BCFF'),
        'top': stage.area('top', (0.0, -0.6, 5.0), (0, 0, 0), 260, 3.0, '#FFF1DC'),
        'face': stage.area('face', (0.6, -4.0, 1.9), (0, 0, 1.5), 160, 2.0, '#FFE9D6'),
    }
    cam = stage.camera(lens=50)
    stage.bloom(threshold=1.6, strength=0.55, size=0.65)
    for o in viz_objects():
        o.hide_render = True
    for o in bpy.data.objects:
        if o.name.startswith('staff_'):
            o.visible_shadow = False
    return cam, L


def keyed(ob, f, loc=None, scale=None, rot=None):
    if loc is not None:
        ob.location = loc
        ob.keyframe_insert('location', frame=f)
    if scale is not None:
        ob.scale = scale if isinstance(scale, (tuple, list, Vector)) else (scale,) * 3
        ob.keyframe_insert('scale', frame=f)
    if rot is not None:
        ob.rotation_euler = rot
        ob.keyframe_insert('rotation_euler', frame=f)


def bez(p0, p1, p2, t):
    return p0 * (1 - t) ** 2 + p1 * 2 * t * (1 - t) + p2 * t * t


def key_value(socket, f, v):
    socket.default_value = v
    socket.keyframe_insert('default_value', frame=f)


# ---------------------------------------------------------------- B01 출동
def b01_intro(preview=False):
    r = rig()
    cam, L = ax_stage()
    hide_bear(True)
    N = 90
    keys = [(1, 'idle', {'vanish': 1}, 'CONSTANT'), (40, 'idle', {'vanish': 1}, 'CONSTANT'),
            (41, 'idle', {'squash': -0.25, 'hips_off': (0, 0, 0.25), 'eye_big': 1.0}, 'BEZIER'),
            (46, 'idle', {'squash': 0.12, 'hips_off': (0, 0, -0.04)}, 'BEZIER'),
            (51, 'idle', {'squash': -0.03}, 'BEZIER'), (56, 'bow', None, 'BEZIER'), (66, 'bow', None, 'BEZIER'),
            (74, 'wave', {'hand.L': (0, 0, -15)}, 'BEZIER'), (80, 'wave', {'hand.L': (0, 0, -60)}, 'BEZIER'),
            (86, 'wave', {'hand.L': (0, 0, -15)}, 'BEZIER'), (90, 'wave', {'hand.L': (0, 0, -50)}, 'BEZIER')]
    finish(r, N, keys)
    for fc in anim.fcurves(r):
        if 'root' in fc.data_path and fc.data_path.endswith('scale'):
            for kp in fc.keyframe_points:
                if kp.co.x <= 41:
                    kp.interpolation = 'CONSTANT'
    fx.poof('pf', (0, -0.2, 0.5), 40, size=0.55, n=12)
    flash_light(lambda f: Vector((0, -0.6, 1.0)), 40, energy=260, color='#FFE7A6', decay=10)
    fx.burst('b1', (0, 0, 1.0), 40, cam, n=60, seed=41, speed=(1.0, 2.6), size=(0.03, 0.07))
    key_cam(cam, 1, (0, 4.0, 9.5), 12.0, -10, -24, lens=35)
    key_cam(cam, 16, (0, 2.0, 6.0), 10.5, -12, -8, lens=38)
    key_cam(cam, 30, (0, 0, 2.2), 9.0, -15, 6, lens=45)
    key_cam(cam, 40, (0, 0, 1.40), 8.4, -16, 7, lens=50)
    key_cam(cam, N, (0, 0, 1.42), 7.6, -12, 6, lens=50)
    return {'frames': N, 'passes': ['beauty']}


# ---------------------------------------------------------------- B02 서류 산더미 → 데이터
TOWERS = [((1.05, 0.70, 0.0), 26, 'HWP'), ((1.80, 0.10, 0.0), 21, 'PDF'), ((0.45, 1.30, 0.0), 30, 'HWPX'),
          ((1.65, 1.10, 0.0), 24, 'HWP'), ((2.25, -0.55, 0.0), 15, 'XLSX')]


def b02_docs(preview=False):
    r = rig()
    cam, L = ax_stage()
    hide_bear(True)
    N = 240
    keys = idle_keys(1, 18) + [
        (24, 'idle', {'head': (-18, -22, 0), 'chest': (-4, -10, 0), 'eye_big': 1.0, 'brow': 0.018, 'open': 0.4}, 'BEZIER'),
        (40, 'idle', {'head': (-16, -24, 0), 'chest': (-4, -12, 0), 'eye_big': 1.0, 'brow': 0.02, 'open': 0.5}, 'BEZIER'),
        (50, 'idle', {'head': (-4, -6, 0), 'brow': -0.008}, 'BEZIER')]
    keys += [(k[0] + 46, k[1], k[2], k[3]) for k in cast_keys(4)]  # 50 → 76 휘두름
    keys += [(120, 'cast', {'staff_dir': (-0.1, -0.5, 0.86)}, 'BEZIER'), (150, 'cast', {'staff_dir': (-0.45, -0.55, 0.7)}, 'BEZIER'),
             (180, 'cast', None, 'BEZIER'), (192, 'tada', None, 'BEZIER'), (210, 'thumbs', None, 'BEZIER'), (240, 'thumbs', None, 'BEZIER')]
    finish(r, N, keys)
    c = coll('DOCS')
    towers = []
    for i, (base, n, label) in enumerate(TOWERS):
        obs = doc_stack(f'tw{i}', base, layers=n, seed=20 + i, label=label, c=c, thick=1.15)
        layers = [o for o in obs if '_p' in o.name or '_f' in o.name]
        for o in obs:
            reorigin(o)
            pop(o, 8 + i * 3)
        towers.append((obs, layers))
    # 흔들흔들(위층일수록 크게)
    for (obs, layers) in towers:
        for o in obs:
            h = o.location.z
            for f in range(14, 70, 6):
                o.rotation_euler = (0.03 * h * math.sin(f * 0.4), 0.03 * h * math.cos(f * 0.33), o.rotation_euler.z)
                o.keyframe_insert('rotation_euler', frame=f)
    gate = set_ax.portal('gate', (-1.25, -0.25, 1.75), r=0.5)
    keyed(gate, 70, scale=0.001)
    keyed(gate, 78, scale=1.1)
    keyed(gate, 82, scale=1.0)
    keyed(gate, 186, scale=1.0)
    keyed(gate, 194, scale=0.001)
    gate.rotation_euler = (0, 0, R(20))
    paper = principled('paper', '#F7F4EC', rough=0.8, spec=0.2)
    rnd = random.Random(7)
    gp = gate.location.copy()
    cols, rows = 6, 4
    # 탑마다 돌아가며 맨 윗장을 뽑는다
    stacks = [list(reversed(layers)) for (obs, layers) in towers]
    order = []
    while len(order) < cols * rows and any(stacks):
        for st_ in stacks:
            if st_ and len(order) < cols * rows:
                order.append(st_.pop(0))
    used = set()
    for k, lay in enumerate(order):
        ts = 80 + k * 4
        used.add(lay.name)
        src = lay.location.copy() + Vector((0, 0, lay.dimensions.z / 2))
        keyed(lay, ts - 1, scale=1.0)
        keyed(lay, ts + 2, scale=0.001)
        sh = set_ax.sheet(f'pg{k}', c, paper)
        keyed(sh, ts - 1, loc=src, scale=0.001)
        mid = (src + gp) / 2 + Vector((rnd.uniform(-0.3, 0.3), -0.6, 0.9))
        for j, t in enumerate((0.0, 0.25, 0.5, 0.75, 1.0)):
            f = ts + int(t * 16)
            keyed(sh, f, loc=bez(src, mid, gp, t), scale=1.0 if t < 1 else 0.001,
                  rot=(R(rnd.uniform(-40, 40) + 360 * t), R(rnd.uniform(-30, 30)), R(20 + 180 * t)))
        card = set_ax.data_card(f'dc{k}', c, color=('#7FE3FF', '#FFD23F', '#9BE7A8')[k % 3])
        slot = Vector((-2.75 + (k % cols) * 0.40, -0.9, 2.75 - (k // cols) * 0.30))
        keyed(card, ts + 15, loc=gp, scale=0.001, rot=(0, 0, R(20)))
        keyed(card, ts + 18, loc=gp + Vector((-0.15, -0.1, 0.05)), scale=1.25)
        keyed(card, ts + 28, loc=slot, scale=1.35, rot=(0, 0, R(10)))
    # 남은 층·집게·라벨은 위에서부터 반짝이며 사라진다(산더미가 다 비워짐)
    rest = [o for (obs, layers) in towers for o in obs if o.name not in used]
    rest.sort(key=lambda o: -o.location.z)
    for i, o in enumerate(rest):
        f = 176 + int(i * 26 / max(1, len(rest)))
        keyed(o, f - 1, scale=1.0)
        keyed(o, f + 3, scale=0.001)
    for ti, (obs, layers) in enumerate(towers):
        base = TOWERS[ti][0]
        fx.burst(f'vb{ti}', Vector(base) + Vector((0, 0, 1.0)), 184 + ti * 3, cam, n=24, seed=90 + ti,
                 colors=('gold', 'white', 'cyan'), speed=(0.5, 1.4), size=(0.03, 0.06))
    flash_light(gem_pos, 72, energy=300, decay=10)
    fx.burst('b1', gem_pos(72), 72, cam, n=40, seed=51, speed=(0.8, 2.2))
    fx.burst('b2', Vector((-1.9, -0.55, 2.2)), 196, cam, n=50, seed=52, colors=('gold', 'cyan', 'white'))
    key_cam(cam, 1, (0.7, 0, 1.40), 9.2, -24, -3, lens=40)  # 자막 위로 발이 보이게(문서 탑 꼭대기도 안 잘리게 뒤로)
    key_cam(cam, 46, (0.6, 0, 1.42), 9.4, -20, 0, lens=40)
    key_cam(cam, 90, (-0.6, 0, 1.45), 9.2, -6, 7, lens=40)
    key_cam(cam, N, (-0.7, 0, 1.45), 8.8, -2, 7, lens=40)
    return {'frames': N, 'passes': ['beauty']}


# ---------------------------------------------------------------- B03 환각 유령 vs 법령 원문
def b03_law(preview=False):
    r = rig()
    cam, L = ax_stage()
    hide_bear(True)
    N = 240
    keys = idle_keys(1, 14) + [
        (22, 'think', {'head': (-4, 18, 8)}, 'BEZIER'), (50, 'think', {'head': (-4, 22, 12)}, 'BEZIER')]
    keys += [(k[0] + 52, k[1], k[2], k[3]) for k in cast_keys(4)]
    keys += [(100, 'cast', {'staff_dir': (0.5, -0.5, 0.7), 'chest': (-6, 14, 0), 'head': (-4, 20, 0)}, 'BEZIER'),
             (150, 'cast', {'staff_dir': (0.5, -0.5, 0.7), 'chest': (-6, 16, 0), 'head': (-4, 22, 0)}, 'BEZIER'),
             (165, 'idle', {'head': (0, 22, 0), 'eye_big': 0.8}, 'BEZIER'),
             (195, 'thumbs', None, 'BEZIER'), (240, 'thumbs', None, 'BEZIER')]
    finish(r, N, keys)
    c = coll('LAW')
    # 유령 + 두루마리 '그럴듯한 답'
    g, gparts = set_ax.ghost('ghost', c)
    sc = set_ax.scroll('fake', '그럴듯한 답', c)
    sc.parent = g
    sc.location = (0.0, -0.32, -0.12)
    sc.rotation_euler = (R(8), 0, 0)
    gp = Vector((-1.15, -0.35, 1.35))
    keyed(g, 9, loc=gp, scale=0.001)
    fx.poof('gpf', gp, 10, size=0.4)
    keyed(g, 14, scale=1.5)
    keyed(g, 18, scale=1.3)
    for f in range(18, 176, 4):
        wob = 0.06 * math.sin(f * 0.2)
        keyed(g, f, loc=gp + Vector((0.02 * math.sin(f * 0.13), 0, wob)), rot=(0, R(6 * math.sin(f * 0.17)), 0))
    for f, dx in ((152, 0.0), (156, 0.06), (160, -0.06), (164, 0.05), (168, -0.04), (172, 0.0)):
        keyed(g, f, loc=gp + Vector((dx, 0, 0)))
    keyed(g, 176, scale=1.3)
    keyed(g, 182, scale=0.001)
    fx.poof('gpf2', gp, 180, size=0.5, color='#E8ECFF')
    # 법령 책: 소환 → 열림 → 조문 빛줄
    book, hinge = set_ax.law_book('lawbook', c)
    bp = Vector((1.75, -0.55, 1.05))
    keyed(book, 75, loc=bp, scale=0.001, rot=(R(62), 0, R(-14)))
    fx.poof('bpf', bp, 76, size=0.5)
    keyed(book, 80, scale=1.15)
    keyed(book, 84, scale=1.0)
    keyed(hinge, 88, rot=(0, 0, 0))
    keyed(hinge, 100, rot=(0, R(-170), 0))
    gold = emission('article', '#FFD86B', 6.0)
    rnd = random.Random(3)
    for i in range(10):
        ln = box(f'art{i}', c, (rnd.uniform(0.25, 0.45), 0.01, 0.025), (0, 0, 0), 0, gold, 0.004)
        ln.visible_shadow = False
        p0 = bp + Vector((rnd.uniform(-0.9, -0.2), -0.15, rnd.uniform(0.0, 0.2)))
        p1 = p0 + Vector((rnd.uniform(-0.25, 0.1), -0.2, 0.55 + i * 0.07))
        f0 = 100 + i * 3
        keyed(ln, f0 - 1, loc=p0, scale=0.001, rot=(0, 0, R(-14)))
        keyed(ln, f0 + 4, scale=1.0)
        keyed(ln, f0 + 18, loc=p1)
        keyed(ln, 168, scale=1.0)
        keyed(ln, 174, scale=0.001)
    tag = fx.text3d('artno', '제○조 원문', 0.09, gold, c, extrude=0.004)
    tag.visible_shadow = False
    keyed(tag, 109, loc=bp + Vector((-0.55, -0.3, 1.25)), scale=0.001, rot=(R(80), 0, R(-14)))
    keyed(tag, 115, scale=1.0)
    keyed(tag, 168, scale=1.0)
    keyed(tag, 174, scale=0.001)
    # 대조 빛줄기: 책 → 두루마리
    beam = box('beam', c, (1.0, 0.012, 0.012), (0, 0, 0), 0, emission('beam', '#FFF1B8', 8.0), 0.0)
    beam.visible_shadow = False
    a, b = bp + Vector((-0.55, -0.2, 0.3)), gp + Vector((0, -0.32, -0.12))
    mid = (a + b) / 2
    d = b - a
    beam.location = mid
    beam.rotation_euler = d.to_track_quat('X', 'Z').to_euler()
    keyed(beam, 124, scale=(0.001, 1, 1))
    keyed(beam, 132, scale=(d.length, 1, 1))
    keyed(beam, 150, scale=(d.length, 1.4, 1.4))
    keyed(beam, 156, scale=(0.001, 1, 1))
    # 빨간 ✗ + '원문 불일치'
    red = emission('redx', '#FF4D5E', 5.0)
    xs = []
    for i, ang in enumerate((45, -45)):
        bar = box(f'x{i}', c, (0.42, 0.012, 0.06), (0, 0, 0), 0, red, 0.006)
        bar.parent = sc
        bar.location = (0, -0.012, 0.0)
        bar.rotation_euler = (0, R(ang), 0)
        keyed(bar, 147, scale=0.001)
        keyed(bar, 151, scale=1.2)
        keyed(bar, 154, scale=1.0)
        xs.append(bar)
    nm = fx.text3d('mismatch', '원문 불일치', 0.08, red, c, extrude=0.003)
    nm.parent = sc
    nm.location = (0, -0.02, -0.25)
    nm.rotation_euler = (R(90), 0, 0)
    keyed(nm, 150, scale=0.001)
    keyed(nm, 155, scale=1.0)
    # 금빛 카드 '원문 확인 ✓'
    ok = set_ax.data_card('okcard', c, color='#FFD23F')
    okt = fx.text3d('oktext', '원문 일치', 0.06, emission('oktxt', '#FFFFFF', 3.0), c, extrude=0.002)
    okt.parent = ok
    okt.location = (0, -0.012, -0.0)
    okt.rotation_euler = (R(90), 0, 0)
    for o in ok.children:
        if o.name.startswith('okcard_l'):
            o.hide_render = True
    keyed(ok, 182, loc=bp + Vector((-0.5, -0.35, 0.95)), scale=0.001, rot=(0, 0, R(-14)))
    keyed(ok, 188, scale=1.8)
    keyed(ok, 192, scale=1.6)
    fx.burst('okb', bp + Vector((-0.5, -0.35, 0.95)), 186, cam, n=40, seed=61, colors=('gold', 'white'))
    flash_light(gem_pos, 72, energy=260, decay=10)
    key_cam(cam, 1, (-0.4, 0, 1.2), 8.4, -6, 6, lens=45)
    key_cam(cam, 70, (0.0, 0, 1.2), 9.0, -4, 7, lens=45)
    key_cam(cam, N, (0.1, 0, 1.25), 8.3, 2, 7, lens=45)
    return {'frames': N, 'passes': ['beauty']}


# ---------------------------------------------------------------- B04 동네를 데이터로
def b04_map(preview=False):
    r = rig()
    cam, L = ax_stage()
    hide_bear(True)
    for n in [o.name for o in bpy.data.objects if o.name.startswith(('office', 'flag', 'tile', 'bush'))]:
        bpy.data.objects[n].hide_render = True
    N = 240
    keys = idle_keys(1, 50) + [
        (60, 'idle', {'hips_off': (0, 0, 0.05), 'squash': -0.05, 'hand_ik.R': (-0.40, -0.18, 0.95), 'staff_dir': (0, -0.1, 1)}, 'BEZIER'),
        (66, 'idle', {'hips_off': (0, 0, -0.04), 'squash': 0.07, 'hand_ik.R': (-0.42, -0.10, 0.55), 'staff_dir': (0, 0, 1), 'brow': -0.006}, 'BEZIER'),
        (74, 'idle', {'eye_big': 0.5}, 'BEZIER'), (130, 'think', {'head': (-10, -20, 4)}, 'BEZIER'),
        (170, 'thumbs', None, 'BEZIER'), (240, 'thumbs', None, 'BEZIER')]
    finish(r, N, keys)
    c = coll('MAP')
    river, hills, blocks = set_ax.district('gj', c)
    for o in [river] + hills:
        keyed(o, 8, scale=(1, 1, 0.001))
        keyed(o, 22, scale=(1, 1, 1))
    for b, h in blocks:
        dist = math.hypot(b.location.x, b.location.y)
        f = 10 + int(dist * 14)
        reorigin(b)
        base = b.location.copy()
        b.location = Vector((base.x, base.y, 0.0))
        b.data.transform(Matrix.Translation(Vector((0, 0, base.z))))
        keyed(b, f - 1, scale=(1, 1, 0.001))
        keyed(b, f + 5, scale=(1, 1, 1.15))
        keyed(b, f + 8, scale=(1, 1, 1.0))
    # 지팡이로 땅 콩 → 퍼지는 고리
    ring = sweep_ring('wave_ring', 1.0)
    keyed(ring, 65, loc=(0, 0, 0.05), scale=0.001)
    keyed(ring, 90, scale=2.6)
    keyed(ring, 96, scale=2.9)
    mat = ring.data.materials[0]
    s_ = mat.node_tree.nodes['Emission'].inputs['Strength']
    key_value(s_, 65, 8.0)
    key_value(s_, 96, 0.0)
    keyed(ring, 97, scale=0.001)  # 빛이 꺼진 고리가 검은 테두리로 남지 않게
    rnd = random.Random(11)
    picks = rnd.sample(blocks, 14)
    colors = ['#FF5E5E', '#FFD23F', '#7FE3FF']
    for i, (b, h) in enumerate(picks):
        p = set_ax.pin(f'pin{i}', (b.location.x, b.location.y, h + 0.02), colors[i % 3], c)
        f = 74 + i * 4
        keyed(p, f - 1, scale=0.001)
        keyed(p, f + 4, scale=1.4)
        keyed(p, f + 7, scale=1.1)
        if i % 3 == 0:  # 무단투기 다발 지점 = 붉은 열점
            disc = set_ax.ellipsoid(f'heat{i}', (0, 0, 0), (0.35, 0.35, 0.004), c, cuts=3)
            disc.data.materials.append(emission('heat', '#FF6A4D', 2.5))
            disc.visible_shadow = False
            keyed(disc, f, loc=(b.location.x, b.location.y, 0.02), scale=0.001)
            keyed(disc, f + 10, scale=1.0)
    # 떠오르는 상황판 패널(막대가 자란다)
    panel_mat = principled('panel', '#122452', rough=0.3, emit='#1E3C7A', emit_strength=0.5)
    bar_mat = emission('bar', '#FFD23F', 4.0)
    for pi, (px, pz, rz) in enumerate(((-1.55, 2.05, 18), (1.6, 2.15, -18))):
        pn = box(f'panel{pi}', c, (1.0, 0.03, 0.62), (0, 0, 0), 0, panel_mat, 0.02)
        keyed(pn, 140 + pi * 8, loc=(px, 0.3, pz - 0.6), scale=0.001, rot=(0, 0, R(rz)))
        keyed(pn, 150 + pi * 8, loc=(px, 0.3, pz), scale=1.0)
        for j in range(5):
            hh = (0.18, 0.32, 0.26, 0.42, 0.36)[j] if pi == 0 else (0.4, 0.3, 0.22, 0.16, 0.1)[j]
            bar = box(f'bar{pi}_{j}', c, (0.12, 0.02, 1.0), (0, 0, 0), 0, bar_mat if pi == 0 else emission('bar2', '#7FE3FF', 4.0), 0.0)
            bar.parent = pn
            bar.location = (-0.36 + j * 0.18, -0.03, -0.24)
            bar.data.transform(Matrix.Translation(Vector((0, 0, 0.5))))
            keyed(bar, 156 + pi * 8 + j * 3, scale=(1, 1, 0.001))
            keyed(bar, 166 + pi * 8 + j * 3, scale=(1, 1, hh))
    key_cam(cam, 1, (0, -0.2, 0.8), 10.2, -20, 34, lens=40)  # 위에서 내려다볼 때 모자 끝이 화면 위로 안 잘리게
    key_cam(cam, 70, (0, -0.2, 0.75), 10.4, -10, 46, lens=40)
    key_cam(cam, 140, (0, 0.0, 1.0), 9.8, 2, 32, lens=40)
    key_cam(cam, N, (0, 0.0, 1.05), 9.4, 8, 30, lens=40)
    shake(cam, 66, n=6, amp=0.03)
    return {'frames': N, 'passes': ['beauty']}


def sweep_ring(name, r):
    from lib import sweep
    ob = sweep(name, [(r * math.cos(a), r * math.sin(a), 0) for a in [2 * math.pi * k / 64 for k in range(65)]],
               0.02, coll('FX'), sides=6, segs=128, aspect=0.4, tip=False, cap0=False, levels=0)
    ob.data.materials.append(emission(f'{name}_mat', '#9FE8FF', 8.0))
    ob.visible_shadow = False
    return ob


# ---------------------------------------------------------------- B05 마법을 나눠 준다(오픈소스)
ISLANDS = [(-4.6, 3.2, 1.2), (-2.6, 6.0, 2.9), (0.6, 7.2, 1.9), (3.6, 5.6, 3.2), (5.2, 2.6, 1.0), (-6.0, 0.4, 2.6),
           (6.2, -0.4, 2.4), (-1.0, 9.0, 4.0)]


def b05_share(preview=False):
    r = rig()
    cam, L = ax_stage()
    hide_bear(True)
    N = 210
    keys = idle_keys(1, 16) + [
        (24, 'tada', {'staff_dir': (0, 0.1, 1), 'hand_ik.L': (0.40, -0.06, 0.9)}, 'BEZIER'),
        (30, 'tada', {'staff_dir': (0.05, 0.2, 1), 'hand_ik.L': (0.40, -0.06, 0.9), 'squash': -0.03}, 'BEZIER'),
        (120, 'tada', {'staff_dir': (-0.1, 0.25, 1), 'hand_ik.L': (0.40, -0.06, 0.9)}, 'BEZIER'),
        (140, 'idle', {'happy': 1.0}, 'BEZIER'), (160, 'wave', None, 'BEZIER'), (170, 'wave', {'hand.L': (0, 0, -60)}, 'BEZIER'),
        (180, 'wave', {'hand.L': (0, 0, -10)}, 'BEZIER'), (190, 'wave', {'hand.L': (0, 0, -60)}, 'BEZIER'), (210, 'idle', {'happy': 1.0}, 'BEZIER')]
    finish(r, N, keys)
    c = coll('ISLES')
    lands = []
    for i, p in enumerate(ISLANDS):
        top, m = set_ax.mini_island(f'isl{i}', p, c, seed=i)
        top.scale = (1.7,) * 3
        lit = m.node_tree.nodes['lit'].outputs[0]
        lands.append((top, lit, Vector(p)))
        for f in range(1, N + 1, 10):
            keyed(top, f, loc=Vector(p) + Vector((0, 0, 0.08 * math.sin(f * 0.07 + i))))
    rnd = random.Random(5)
    arrivals = []
    for i, (top, lit, p) in enumerate(lands):
        f0 = 32 + i * 9
        src = gem_pos(f0)
        dst = p + Vector((0, 0, 0.5))
        mid = (src + dst) / 2 + Vector((0, 0, 2.2 + rnd.uniform(0, 1.2)))
        st = fx.twinkle_mesh(f'star{i}', coll('FX'), r=0.2)
        fx.face_camera(st, cam)
        st.data.materials.append(fx.fx_mat('gold'))
        st.visible_shadow = False
        T = 22
        keyed(st, f0 - 1, loc=src, scale=0.001)
        for j in range(0, T + 1, 2):
            keyed(st, f0 + j, loc=bez(src, mid, dst, j / T), scale=1.0)
        keyed(st, f0 + T + 1, scale=0.001)
        fx.trail(f'tr{i}', lambda f, s=src, m=mid, d=dst, a=f0: bez(s, m, d, min(1, max(0, (f - a) / T))), f0 + 1, f0 + T - 1, cam,
                 every=1, seed=i, size=(0.04, 0.09))
        key_value(lit, f0 + T - 1, 0.0)
        key_value(lit, f0 + T + 3, 5.0)
        key_value(lit, f0 + T + 12, 2.6)
        fx.burst(f'ib{i}', dst, f0 + T, cam, n=26, seed=70 + i, speed=(0.8, 1.8), size=(0.05, 0.11))
        ld = bpy.data.lights.new(f'isl_light{i}', 'POINT')
        ld.color = (1.0, 0.78, 0.45)
        lo = bpy.data.objects.new(f'isl_light{i}', ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = p + Vector((0, -0.6, 1.0))
        for f, e in ((f0 + T - 1, 0), (f0 + T + 2, 900), (f0 + T + 14, 350)):
            ld.energy = e
            ld.keyframe_insert('energy', frame=f)
        arrivals.append(f0 + T)
    flash_light(gem_pos, 30, energy=260, decay=12)
    key_cam(cam, 1, (0, 0, 1.05), 8.8, -14, 6, lens=45)  # 자막 위로 발이 보이게
    key_cam(cam, 30, (0, 0, 1.15), 9.0, -12, 7, lens=45)
    key_cam(cam, 56, (0, 2.2, 1.55), 12.4, -6, 9, lens=32)
    key_cam(cam, N, (0, 2.4, 1.65), 11.9, 6, 9, lens=32)
    return {'frames': N, 'passes': ['beauty'], 'meta': {'arrivals': arrivals}}


# ---------------------------------------------------------------- B06 마무리(곰돌이 + 인사)
def b06_outro(preview=False):
    r = rig()
    cam, L = ax_stage()
    hide_bear(False)
    N = 150
    keys = idle_keys(1, 12) + [
        (16, 'idle', {'hat.1': (0, 0, 8), 'eye_big': 0.6}, 'BEZIER'), (19, 'idle', {'hat.1': (0, 0, -8)}, 'BEZIER'),
        (22, 'idle', {'hat.1': (6, 0, 6)}, 'BEZIER'), (26, 'idle', {'squash': 0.05}, 'BEZIER'),
        (34, 'tada', None, 'BEZIER'), (50, 'tada', None, 'BEZIER'), (62, 'bow', None, 'BEZIER'), (78, 'bow', None, 'BEZIER'),
        (90, 'idle', {'happy': 1.0}, 'BEZIER'), (100, 'wave', None, 'BEZIER'), (108, 'wave', {'hand.L': (0, 0, -60)}, 'BEZIER'),
        (116, 'wave', {'hand.L': (0, 0, -10)}, 'BEZIER'), (124, 'wave', {'hand.L': (0, 0, -60)}, 'BEZIER'), (150, 'idle', {'happy': 1.0}, 'BEZIER')]
    finish(r, N, keys)
    hat_top = bone_pos('hat.3', 26, 0.3)
    fx.poof('pf', hat_top, 26, size=0.45)
    fx.burst('b2', hat_top, 27, cam, n=44, seed=81, colors=('gold', 'pink', 'white'), speed=(0.8, 2.0))
    flash_light(lambda f: hat_top, 27, energy=300, color='#FFE9F2', decay=10)
    root = bear_rig()
    spot = Vector((0.85, -0.2, 1.25))
    root.scale = (0.001,) * 3
    root.location = hat_top
    root.keyframe_insert('scale', frame=25)
    root.keyframe_insert('location', frame=25)
    for f, p, s in ((28, hat_top + Vector((0.05, 0, 0.30)), 1.55), (34, hat_top.lerp(spot, 0.6) + Vector((0, 0, 0.35)), 1.35),
                    (40, spot, 1.35)):
        keyed(root, f, loc=p, scale=s)
    float_bear(root, 44, 60, spot, scale=1.35)
    # 곰돌이도 꾸벅
    for f, ang in ((62, 0), (68, 35), (78, 35), (86, 0)):
        root.rotation_euler = (R(ang), 0, R(-20))
        root.keyframe_insert('rotation_euler', frame=f)
    float_bear(root, 90, N, spot, scale=1.35)
    key_bear_wave(100, 130)
    key_cam(cam, 1, (-0.85, 0, 1.5), 6.8, -12, 4, lens=50)
    key_cam(cam, N, (-0.80, 0, 1.55), 6.3, -6, 4, lens=50)
    return {'frames': N, 'passes': ['beauty']}


SHOTS = {'b01_intro': b01_intro, 'b02_docs': b02_docs, 'b03_law': b03_law, 'b04_map': b04_map,
         'b05_share': b05_share, 'b06_outro': b06_outro}
