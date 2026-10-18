"""포즈: 채널 사전 하나 = 자세 하나. 지정 안 한 채널은 쉬는 자세 값.
위치는 캐릭터 공간(쉬는 자세 = 월드), 세로 뼈 회전은 (앞으로 숙임, 몸통 돌림, 옆 기울임) 도."""
import math
from mathutils import Vector, Matrix

R = math.radians
HEAD_CENTER = (0.0, 0.0, 1.48)  # params.HEAD['center']

# 쉬는 자세 손목: L (0.491, 0, 0.669), R (-0.491, 0, 0.669)
POSES = {
    'rest': {},
    'idle': {
        'hand_ik.L': (0.40, -0.03, 0.57), 'hand_ik.R': (-0.42, -0.02, 0.60),
        'chest': (2, 0, 0), 'head': (-2, 0, 2),
    },
    'wave': {
        'hand_ik.L': (0.52, -0.16, 1.12), 'elbow_pole.L': (0.9, 0.3, 0.6), 'hand.L': (0, 0, -40),
        'hand_ik.R': (-0.42, -0.02, 0.60),
        'chest': (0, 6, -4), 'head': (0, 4, -8), 'happy': 1.0, 'open': 0.6, 'hat.1': (0, 0, -6),
    },
    'bow': {
        'hips_off': (0, 0.05, -0.02), 'hips': (4, 0, 0), 'spine': (14, 0, 0), 'chest': (14, 0, 0), 'neck': (4, 0, 0),
        'head': (6, 0, 0),
        'hand_ik.L': (0.10, -0.30, 0.50), 'hand_ik.R': (-0.36, -0.10, 0.50),
        'happy': 1.0, 'hat_slip': (14, 0.02),
    },
    'cast': {
        'hips_off': (0, 0.03, -0.02), 'chest': (-8, -16, 0), 'head': (-6, -10, 0),
        'hand_ik.R': (-0.50, -0.14, 1.20), 'elbow_pole.R': (-0.9, 0.3, 0.8), 'staff_dir': (-0.32, -0.42, 0.85),
        'hand_ik.L': (0.34, -0.42, 0.96), 'hand.L': (-20, 0, 0),
        'open': 1.0, 'brow': 0.012, 'hat.1': (-8, 0, 0),
    },
    'thumbs': {
        'hand_ik.L': (0.22, -0.34, 0.86), 'hand.L': (0, 70, 60), 'hand_ik.R': (-0.42, -0.02, 0.60),
        'chest': (0, 8, 0), 'head': (0, 6, -10), 'wink': 1.0, 'open': 0.4,
    },
    'tada': {
        'hips_off': (0, 0, 0.05), 'hand_ik.L': (0.40, -0.06, 1.28), 'hand_ik.R': (-0.40, -0.06, 1.32),
        'elbow_pole.L': (0.9, 0.3, 0.9), 'elbow_pole.R': (-0.9, 0.3, 0.9), 'staff_dir': (-0.25, 0.05, 1.0),
        'chest': (-8, 0, 0), 'head': (-8, 0, 0), 'happy': 1.0, 'open': 1.0,
    },
    'think': {
        'hand_ik.L': (0.10, -0.40, 1.02), 'elbow_pole.L': (0.6, 0.2, 0.5), 'hand.L': (-30, 0, 0),
        'hand_ik.R': (-0.42, -0.02, 0.60),
        'chest': (4, -6, 0), 'head': (-4, -10, 10), 'brow_l': 0.016,
    },
}

POSE_LABELS = {'bow': '인사', 'wave': '손인사', 'cast': '주문', 'thumbs': '엄지척', 'tada': '짠!', 'think': '생각'}

ROT_BONES = ('hips', 'spine', 'chest', 'neck', 'head', 'hand.L', 'hand.R', 'staff', 'hat.1')
SPRING_BONES = ('hat.2', 'hat.3', 'cape.1', 'cape.2', 'cape.3', 'badge')
IK_BONES = ('hand_ik.L', 'hand_ik.R', 'elbow_pole.L', 'elbow_pole.R', 'foot_ik.L', 'foot_ik.R')


def apply(rig, pose, extra=None):
    """포즈 사전을 리그에 적용(지정 안 된 채널은 쉬는 자세)."""
    p = dict(POSES[pose]) if isinstance(pose, str) else dict(pose)
    if extra:
        p.update(extra)
    pbs = rig.pose.bones
    rest = rig.data.bones
    for n in ROT_BONES:
        pbs[n].rotation_euler = [R(a) for a in p.get(n, (0, 0, 0))]
    for n in IK_BONES:
        pbs[n].location = Vector(p[n]) - rest[n].head_local if n in p else Vector()
    hb = rest['hips']
    pbs['hips'].location = hb.matrix_local.to_3x3().inverted() @ Vector(p.get('hips_off', (0, 0, 0)))
    pbs['root'].location = rest['root'].matrix_local.to_3x3().inverted() @ Vector(p.get('root_off', (0, 0, 0)))
    pbs['root'].rotation_euler = (0, 0, R(p.get('root_turn', 0)))
    happy, wink, blink = p.get('happy', 0.0), p.get('wink', 0.0), p.get('blink', 0.0)
    for tag in ('L', 'R'):
        h = max(happy, wink if tag == 'L' else 0.0)
        e = (1 - h) * (1 - 0.92 * blink)
        big = 1 + 0.18 * p.get('eye_big', 0.0)
        gone = (1 - h) < 0.01  # 눈웃음·윙크로 완전히 감으면 깊이까지 접어 눈 조각이 남지 않게
        pbs[f'eye.{tag}'].scale = (max(1 - h, 0.001) * big, 0.001 if gone else 1, max(e, 0.001) * big)
        pbs[f'eye_happy.{tag}'].scale = (max(h, 0.001),) * 3
        lift = p.get('brow', 0.0) + (p.get('brow_l', 0.0) if tag == 'L' else 0.0)
        # 눈썹 뼈 로컬 Z = 위
        pbs[f'brow.{tag}'].location = (0, 0, lift)
    o = p.get('open', 0.0)
    pbs['mouth'].scale = (max(1 - o, 0.001),) * 3
    pbs['mouth_open'].scale = (max(o, 0.001),) * 3
    hb1 = rest['hat.1']
    off = Vector(p.get('hat_off', (0, 0, 0)))
    if 'hat_slip' in p:
        # 모자가 머리 위를 굴러 앞으로 미끄러진다: 밑동이 아니라 머리 중심을 축으로 돌리고 lift 만큼 띄운다
        # (밑동을 축으로 기울이거나 그냥 내리면 앞머리 다발이 모자를 뚫고 나온다)
        ang, lift = p['hat_slip']
        v = hb1.head_local - Vector(HEAD_CENTER)
        rv = Matrix.Rotation(R(ang), 3, 'X') @ v
        off += rv - v + rv.normalized() * lift
        pbs['hat.1'].rotation_euler.x += R(ang)
    pbs['hat.1'].location = hb1.matrix_local.to_3x3().inverted() @ off
    if 'staff' not in p:
        aim(rig, 'staff', p.get('staff_dir', (0, 0, 1)))
    sq = p.get('squash', 0.0)
    pbs['root'].scale = (0.001,) * 3 if p.get('vanish') else (1 + sq * 0.5, 1 + sq * 0.5, 1 - sq)


def aim(rig, name, direction):
    """root 자식 뼈의 Y 축이 캐릭터 공간 방향을 보도록(쉬는 자세 기준, 깊이 평가 없음)."""
    b = rig.data.bones[name]
    d = (b.matrix_local.to_3x3().inverted() @ Vector(direction)).normalized()
    rig.pose.bones[name].rotation_euler = Vector((0, 1, 0)).rotation_difference(d).to_euler('XYZ')


CHANNELS = [(n, 'rotation_euler') for n in ROT_BONES] + [(n, 'location') for n in IK_BONES] + \
    [('hips', 'location'), ('root', 'location'), ('root', 'rotation_euler'), ('root', 'scale'), ('hat.1', 'location')] + \
    [(f'{b}.{t}', 'scale') for b in ('eye', 'eye_happy') for t in ('L', 'R')] + \
    [(f'brow.{t}', 'location') for t in ('L', 'R')] + [('mouth', 'scale'), ('mouth_open', 'scale')]


def key(rig, frame, interp='BEZIER'):
    for n, path in CHANNELS:
        rig.pose.bones[n].keyframe_insert(path, frame=frame)
