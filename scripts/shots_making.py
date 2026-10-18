"""제작영상(A) 샷들. 각 함수는 장면을 꾸미고 {'frames', 'passes'} 를 돌려준다."""
import math
import random
import bpy
from mathutils import Vector, Matrix

import anim
import fx
from shots_common import (rig, studio, gem_pos, bone_pos, key_cam, hide_bear, bear_root, char_objects,
                          reveal_bones, cam_full, flash_light, dim_lights, shake)

R = math.radians


# ---------------------------------------------------------------- 공용 동작
def idle_keys(f0, f1, blinks=(), base='idle', extra=None):
    """숨쉬기(엉덩이 위아래) + 깜빡임."""
    keys = []
    f = f0
    up = False
    while f <= f1:
        e = dict(extra or {})
        e['hips_off'] = (0, 0, 0.008 if up else -0.004)
        e['chest'] = (1 if up else 3, 0, 0)
        keys.append((f, base, e, 'BEZIER'))
        up = not up
        f += 22
    for b in blinks:
        for df, amt in ((0, 0.0), (2, 1.0), (5, 0.0)):
            keys.append((b + df, base, dict(extra or {}, blink=amt), 'BEZIER'))
    return sorted(keys, key=lambda k: k[0])


def cast_keys(f0):
    """대기 → 웅크려 지팡이 뒤로 → 앞위로 휘두름(오버슈트) → 버팀."""
    return [
        (f0, 'idle', None, 'BEZIER'),
        (f0 + 9, 'idle', {'hips_off': (0, 0.02, -0.05), 'squash': 0.07, 'hand_ik.R': (-0.42, 0.10, 0.84),
                          'staff_dir': (-0.15, 0.55, 0.82), 'head': (-12, 0, 0), 'chest': (8, 0, 0), 'brow': -0.008,
                          'hand_ik.L': (0.34, 0.02, 0.62)}, 'BEZIER'),
        (f0 + 15, 'cast', {'squash': -0.06, 'hips_off': (0, 0, 0.04)}, 'BEZIER'),
        (f0 + 19, 'cast', {'staff_dir': (-0.40, -0.62, 0.68), 'squash': 0.02}, 'BEZIER'),
        (f0 + 26, 'cast', None, 'BEZIER'),
    ]


def finish(r, f1, keys, chains=anim.DEFAULT_CHAINS):
    anim.timeline(r, keys)
    anim.bake_springs(r, 1, f1, chains)


def reorigin(ob):
    """부품 원점을 자기 중심으로(크기 애니메이션이 제자리에서 일어나게)."""
    if ob.type != 'MESH':
        return ob.location.copy()
    vs = [v.co for v in ob.data.vertices]
    c = sum(vs, Vector()) / len(vs)
    ob.data.transform(Matrix.Translation(-c))
    ob.matrix_basis = ob.matrix_basis @ Matrix.Translation(c)  # 보이는 자리는 그대로(갓 만든 객체는 matrix_world 가 아직 갱신 전)
    return ob.location.copy()


def pop(ob, f, s0=0.0, over=1.16):
    for df, s in ((-1, s0), (3, over), (5, 0.95), (7, 1.0)):
        ob.scale = (s, s, s)
        ob.keyframe_insert('scale', frame=f + df)


# ---------------------------------------------------------------- A01 콜드오픈
def a01_cold(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=85, light=0.8)
    hide_bear(True)
    N = 90
    keys = cast_keys(1) + [(60, 'cast', {'squash': 0.0}, 'BEZIER'), (72, 'tada', {'staff_dir': (-0.2, -0.2, 1)}, 'BEZIER'),
                           (90, 'tada', {'hips_off': (0, 0, 0.0)}, 'BEZIER')]
    finish(r, N, keys)
    fx.magic_circle('mc', (0, -0.05, 0.004), 1.15, 15, 84, ['법령', '조례', '문서', '통계', '지도', '데이터'])
    fx.trail('tr', lambda f: gem_pos(f), 9, 20, cam, every=1)
    fx.burst('b1', gem_pos(16), 16, cam, n=70, seed=11, speed=(1.2, 3.2), size=(0.03, 0.08))
    fx.burst('b2', gem_pos(22), 22, cam, n=36, seed=12, speed=(0.5, 1.6))
    fx.burst('b3', gem_pos(72), 72, cam, n=40, seed=13, colors=('gold', 'pink', 'white', 'cyan'), speed=(0.8, 2.2))
    flash_light(gem_pos, 16, energy=320, decay=10)
    flash_light(gem_pos, 72, energy=240, color='#FFC2E0', decay=10)
    dim_lights(L, [(1, 1.0), (10, 0.7), (40, 0.7), (60, 1.0)])
    key_cam(cam, 1, (0, 0, 1.55), 4.2, -16, 2, lens=60)
    key_cam(cam, 12, (0, 0, 1.50), 4.6, -18, 2, lens=60)
    key_cam(cam, 20, (0, 0, 1.18), 8.0, -20, 9, lens=50)
    key_cam(cam, N, (0, 0, 1.20), 7.4, -12, 7, lens=50)
    shake(cam, 16)
    return {'frames': N, 'passes': ['beauty']}


# ---------------------------------------------------------------- A03 부품 조립(클레이)
ASSEMBLY = [
    (4, ['shoe.L', 'shoe.R']), (8, ['leg.L', 'leg.R']), (12, ['torso']), (16, ['neck']),
    (18, ['sleeve.L', 'sleeve.R']), (21, ['cuff.L', 'cuff.R', 'hand.L', 'hand.R', 'thumb.L', 'thumb.R']),
    (25, ['head']), (28, ['ear.L', 'ear.R']), (30, ['eye.L', 'eye.R', 'eye_hi0.L', 'eye_hi0.R', 'eye_hi1.L', 'eye_hi1.R']),
    (32, ['lid.L', 'lid.R', 'brow.L', 'brow.R']), (34, ['nose', 'mouth']), (38, ['hair_mass']),
    (41, ['back_g']), (42, ['back_h']), (44, ['swoop_d']), (45, ['swoop_c']), (47, ['swoop_b']), (48, ['part_f']),
    (50, ['part_e']), (52, ['swoop_a']),
    (55, ['collar.L', 'collar.R', 'lapel.L', 'lapel.R', 'tie', 'tie_knot', 'button0', 'button1']),
    (59, ['cape', 'cape_trim', 'clasp.L', 'clasp.R', 'clasp_chain']),
    (63, ['strap.L', 'strap.R', 'badge_card', 'badge_face', 'badge_clip']),
]
HAT = ['hat_cone', 'hat_brim', 'hat_band', 'hat_buckle'] + [f'hat_star{i}' for i in range(5)]
STAFF = ['staff_shaft', 'staff_ring', 'staff_cup', 'staff_gem']


def a03_assemble(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=70)
    hide_bear(True)
    N = 84
    finish(r, N, [(1, 'rest', None, 'BEZIER'), (N, 'rest', None, 'BEZIER')])
    obs = bpy.data.objects
    done = set()
    for f, names in ASSEMBLY:
        for n in names:
            if n in obs:
                reorigin(obs[n])
                pop(obs[n], f)
                done.add(n)
    for n in HAT:
        if n in obs:
            reorigin(obs[n])
            ob = obs[n]
            base = ob.location.copy()
            for f, dz, s in ((66, 0.9, 1.0), (72, -0.05, 1.0), (75, 0.02, 1.0), (78, 0.0, 1.0)):
                ob.location = base + Vector((0, 0, dz))
                ob.keyframe_insert('location', frame=f)
            pop(ob, 66, over=1.0)
            done.add(n)
    for n in STAFF:
        if n in obs:
            reorigin(obs[n])
            pop(obs[n], 72)
            done.add(n)
    print('ASSEMBLED', len(done), 'parts')
    cam_full(cam, 1, -36, 8, dist=8.6)
    cam_full(cam, N, -16, 5, dist=7.9)
    return {'frames': N, 'passes': ['clay'], 'meta': {'parts': len(done)}}


# ---------------------------------------------------------------- A04 턴테이블
def a04_turntable(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=70)
    hide_bear(True)
    N = 96
    finish(r, N, [(1, 'rest', {'root_turn': 0}, 'LINEAR'), (N + 1, 'rest', {'root_turn': 360}, 'LINEAR')])
    for fc in anim.fcurves(r):
        if 'root' in fc.data_path and 'rotation' in fc.data_path:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    cam_full(cam, 1, 0, 4)
    return {'frames': N, 'passes': ['wire', 'clay', 'beauty']}


# ---------------------------------------------------------------- A05 뼈 등장
def a05_rig(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=70)
    hide_bear(True)
    N = 54
    finish(r, N, idle_keys(1, N, base='rest'))
    reveal_bones(4, 40)
    cam_full(cam, 1, -18, 6)
    cam_full(cam, N, -12, 6, dist=7.5, dz=-0.1)  # 발과 발 IK 고리가 자막에 안 가리게
    return {'frames': N, 'passes': ['clay', 'bones']}


# ---------------------------------------------------------------- A06 리그 테스트: 손 흔들기 / 걷기 / 인사
def walk_keys(f0, cycles=2, period=20):
    keys = []
    q = period // 4
    for c in range(cycles):
        for i in range(4):
            f = f0 + c * period + i * q
            right_fwd = i in (0, 1)
            if i % 2 == 0:  # 접지
                fr = (-0.10, -0.11, 0.085) if right_fwd else (-0.10, 0.09, 0.085)
                fl = (0.10, 0.09, 0.085) if right_fwd else (0.10, -0.11, 0.085)
                hz = -0.025
            else:  # 지나감
                fr = (-0.10, 0.0, 0.085) if i == 1 else (-0.10, 0.0, 0.16)
                fl = (0.10, 0.0, 0.16) if i == 1 else (0.10, 0.0, 0.085)
                hz = 0.015
            s = 1 if right_fwd else -1
            keys.append((f, 'idle', {
                'foot_ik.R': fr, 'foot_ik.L': fl, 'hips_off': (0, 0, hz),
                'hand_ik.L': (0.40, -0.12 * s, 0.60), 'hand_ik.R': (-0.42, 0.10 * s, 0.62),
                'chest': (3, 7 * s, 0), 'head': (0, -5 * s, 0), 'staff_dir': (0, -0.15 * s, 1)}, 'BEZIER'))
    return keys


def a06_rigtest(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=70)
    hide_bear(True)
    N = 120
    keys = [(1, 'rest', None, 'BEZIER'), (8, 'idle', None, 'BEZIER'), (14, 'wave', {'hand.L': (0, 0, -10)}, 'BEZIER'),
            (20, 'wave', {'hand.L': (0, 0, -60)}, 'BEZIER'), (26, 'wave', {'hand.L': (0, 0, -10)}, 'BEZIER'),
            (32, 'wave', {'hand.L': (0, 0, -60)}, 'BEZIER'), (38, 'idle', None, 'BEZIER')]
    keys += walk_keys(40, cycles=2, period=20)
    keys += [(80, 'idle', None, 'BEZIER'), (90, 'bow', None, 'BEZIER'), (104, 'bow', None, 'BEZIER'), (116, 'idle', None, 'BEZIER'),
             (120, 'idle', None, 'BEZIER')]
    finish(r, N, keys)
    reveal_bones(-10, 0)
    cam_full(cam, 1, -26, 6)
    cam_full(cam, N, -14, 6)
    return {'frames': N, 'passes': ['clay', 'bones'],
            'meta': {'cues': [[1, '테스트: 손 흔들기'], [40, '테스트: 걷기'], [80, '테스트: 인사']]}}


# ---------------------------------------------------------------- A07 포즈 라이브러리
POSE_ORDER = ['bow', 'wave', 'cast', 'thumbs', 'tada', 'think']


def a07_poses(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=70)
    hide_bear(True)
    N = 90
    keys = [(1, 'idle', None, 'CONSTANT')]
    cues = []
    for i, p in enumerate(POSE_ORDER):
        f = 6 + i * 14
        keys.append((f, p, None, 'CONSTANT'))
        cues.append([f, p])
    keys.append((N, 'think', None, 'CONSTANT'))
    finish(r, N, keys)
    cam_full(cam, 1, -18, 5, dx=0.55, dist=8.1)
    return {'frames': N, 'passes': ['beauty'], 'meta': {'cues': cues}}


def a07_thumbs(preview=False):
    """포즈 선반 썸네일(포즈마다 한 장, 정사각)."""
    import poses
    r = rig()
    cam, L, cyc = studio(lens=70, w=360, h=360, samples=32)
    hide_bear(True)
    frames = []
    for i, p in enumerate(POSE_ORDER):
        poses.apply(r, p)
        for n, path in poses.CHANNELS:
            r.pose.bones[n].keyframe_insert(path, frame=i + 1)
    anim.ease_all(r)
    for fc in anim.fcurves(r):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT'
    key_cam(cam, 1, (0, 0, 1.38), 4.5, -18, 6, lens=50)  # 썸네일(정사각)은 자막이 없어 원래 구도
    return {'frames': len(POSE_ORDER), 'passes': ['beauty']}


# ---------------------------------------------------------------- A08 손인사
def a08_wave(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=70)
    hide_bear(True)
    N = 60
    keys = [(1, 'idle', None, 'BEZIER'), (8, 'idle', {'squash': 0.04, 'hips_off': (0, 0, -0.02)}, 'BEZIER'),
            (14, 'wave', {'hand.L': (0, 0, -15), 'eye_big': 0.3}, 'BEZIER')]
    for i in range(4):
        keys.append((20 + i * 7, 'wave', {'hand.L': (0, 0, -65 if i % 2 == 0 else -10), 'head': (0, 4, -8 - 3 * (i % 2))}, 'BEZIER'))
    keys += [(50, 'idle', {'happy': 1.0}, 'BEZIER'), (60, 'idle', {'happy': 1.0}, 'BEZIER')]
    finish(r, N, keys)
    fx.trail('wt', lambda f: bone_pos('hand.L', f, 0.6), 16, 46, cam, every=2, colors=('gold', 'white', 'pink'))
    key_cam(cam, 1, (0, 0, 1.62), 6.3, 14, 4, lens=50)
    key_cam(cam, N, (0, 0, 1.64), 5.9, 8, 4, lens=50)
    return {'frames': N, 'passes': ['beauty']}


# ---------------------------------------------------------------- A09 공손한 인사(모자 미끄러짐)
def a09_bow(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=70)
    hide_bear(True)
    N = 72
    keys = [(1, 'idle', None, 'BEZIER'), (6, 'idle', {'happy': 1.0}, 'BEZIER'), (16, 'bow', None, 'BEZIER'),
            (22, 'bow', {'hat_slip': (30, 0.05)}, 'BEZIER'),
            (27, 'bow', {'hat_slip': (58, 0.10), 'happy': 0.0, 'eye_big': 1.0, 'brow': 0.02, 'open': 0.5}, 'BEZIER'),
            (32, 'idle', {'hips_off': (0, 0, 0.05), 'squash': -0.05, 'eye_big': 1.0, 'brow': 0.02, 'open': 0.6,
                          'hat_off': (0, -0.05, 0.12), 'hat.1': (-10, 0, 0)}, 'BEZIER'),
            (38, 'idle', {'hat_off': (0, 0, -0.01), 'squash': 0.04}, 'BEZIER'),
            (44, 'thumbs', None, 'BEZIER'), (60, 'thumbs', None, 'BEZIER'), (72, 'idle', {'happy': 1.0}, 'BEZIER')]
    finish(r, N, keys)
    fx.burst('hb', bone_pos('hat.2', 36, 0.0), 36, cam, n=22, seed=21, speed=(0.4, 1.2), size=(0.02, 0.045))
    cam_full(cam, 1, -30, 4, dz=-0.05)
    cam_full(cam, N, -22, 4, dz=-0.05)
    return {'frames': N, 'passes': ['beauty']}


# ---------------------------------------------------------------- A10 주문 시전 + 곰돌이 등장
def bear_rig():
    root = bear_root()
    for side, tag in ((-1, 'R'), (1, 'L')):
        a = bpy.data.objects[f'bear_arm.{tag}']
        a.data.transform(Matrix.Translation(Vector((-side * 0.085, 0.01, -0.19))))
        a.location = (side * 0.085, -0.01, 0.19)
    return root


def key_bear_wave(f0, f1, period=8):
    for tag, ph in (('L', 0), ('R', 0.5)):
        a = bpy.data.objects[f'bear_arm.{tag}']
        side = 1 if tag == 'L' else -1
        f = f0
        i = 0
        while f <= f1:
            ang = side * (R(150) if (i + (1 if tag == 'R' else 0)) % 2 == 0 else R(110))
            a.rotation_euler = (0, ang, 0)
            a.keyframe_insert('rotation_euler', frame=f)
            f += period // 2
            i += 1


def float_bear(root, f0, f1, base, amp=0.03, scale=1.0):
    for f in range(f0, f1 + 1, 4):
        root.location = Vector(base) + Vector((0, 0, amp * math.sin(f * 0.25)))
        root.rotation_euler = (0, 0.08 * math.sin(f * 0.17), R(-20) + 0.1 * math.sin(f * 0.11))
        root.scale = (scale,) * 3
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('rotation_euler', frame=f)
        root.keyframe_insert('scale', frame=f)


def a10_cast(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=70, light=0.85)
    hide_bear(False)
    N = 105
    keys = cast_keys(1) + [
        (44, 'cast', None, 'BEZIER'), (52, 'idle', {'eye_big': 0.6, 'hat.1': (0, 0, 8)}, 'BEZIER'),
        (55, 'idle', {'hat.1': (0, 0, -8), 'eye_big': 0.8}, 'BEZIER'), (58, 'idle', {'hat.1': (6, 0, 6)}, 'BEZIER'),
        (62, 'idle', {'hat.1': (0, 0, 0), 'squash': 0.05}, 'BEZIER'),
        (70, 'tada', {'staff_dir': (-0.2, -0.2, 1)}, 'BEZIER'), (86, 'tada', None, 'BEZIER'),
        (96, 'idle', {'happy': 1.0}, 'BEZIER'), (105, 'idle', {'happy': 1.0}, 'BEZIER')]
    finish(r, N, keys)
    fx.magic_circle('mc', (0, -0.05, 0.004), 1.15, 15, 60, ['법령', '조례', '문서', '통계', '지도', '데이터'])
    fx.trail('tr', lambda f: gem_pos(f), 9, 20, cam)
    fx.burst('b1', gem_pos(16), 16, cam, n=70, seed=31, speed=(1.2, 3.2), size=(0.03, 0.08))
    flash_light(gem_pos, 16, energy=320, decay=10)
    dim_lights(L, [(1, 1.0), (10, 0.7), (40, 0.7), (58, 1.0)])
    hat_top = bone_pos('hat.3', 62, 0.3)
    fx.poof('pf', hat_top, 62, size=0.45)
    fx.burst('b2', hat_top, 63, cam, n=44, seed=32, colors=('gold', 'pink', 'white'), speed=(0.8, 2.0))
    flash_light(lambda f: hat_top, 63, energy=500, color='#FFE9F2', decay=10)
    root = bear_rig()
    spot = Vector((0.82, -0.18, 1.28))
    root.scale = (0.001,) * 3
    root.location = hat_top
    root.keyframe_insert('scale', frame=61)
    root.keyframe_insert('location', frame=61)
    for f, p, s in ((64, hat_top + Vector((0.05, 0, 0.30)), 1.55), (70, hat_top.lerp(spot, 0.6) + Vector((0, 0, 0.35)), 1.35),
                    (76, spot + Vector((0, 0, -0.03)), 1.35)):
        root.location = p
        root.scale = (s,) * 3
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('scale', frame=f)
    float_bear(root, 80, N, spot, scale=1.35)
    key_bear_wave(82, N)
    cam_full(cam, 1, -16, 3, dx=0.1, dist=8.3, dz=0.05)
    cam_full(cam, N, -8, 3, dx=0.3, dist=7.8, dz=0.08)
    shake(cam, 16)
    return {'frames': N, 'passes': ['beauty']}


# ---------------------------------------------------------------- A11 엔드카드(캐릭터는 오른쪽)
def a11_end(preview=False):
    r = rig()
    cam, L, cyc = studio(lens=70)
    hide_bear(False)
    N = 135  # 마지막 나레이션(3.8초)이 다 들리게
    keys = idle_keys(1, N, blinks=(30, 84), base='idle', extra={'happy': 0.0})
    keys += [(40, 'idle', {'hips_off': (0, 0, 0.0)}, 'BEZIER'), (50, 'wave', {'hand.L': (0, 0, -20)}, 'BEZIER'),
             (57, 'wave', {'hand.L': (0, 0, -60)}, 'BEZIER'), (64, 'wave', {'hand.L': (0, 0, -15)}, 'BEZIER'),
             (71, 'wave', {'hand.L': (0, 0, -60)}, 'BEZIER'), (80, 'idle', {'happy': 1.0}, 'BEZIER')]
    keys = sorted({k[0]: k for k in keys}.values(), key=lambda k: k[0])
    finish(r, N, keys)
    root = bear_rig()
    float_bear(root, 1, N, (0.78, -0.14, 1.30), scale=1.3)
    key_bear_wave(50, 80)
    cam_full(cam, 1, -14, 4, dx=-1.15, dist=8.2)
    cam_full(cam, N, -10, 4, dx=-1.10, dist=7.9)
    return {'frames': N, 'passes': ['beauty']}


SHOTS = {
    'a01_cold': a01_cold, 'a03_assemble': a03_assemble, 'a04_turntable': a04_turntable, 'a05_rig': a05_rig,
    'a06_rigtest': a06_rigtest, 'a07_poses': a07_poses, 'a07_thumbs': a07_thumbs, 'a08_wave': a08_wave,
    'a09_bow': a09_bow, 'a10_cast': a10_cast, 'a11_end': a11_end,
}
