"""모자 관통 검사: 머리카락(덩어리 + 다발) 꼭짓점을 모자 로컬로 옮겨, 챙 위로(원뿔 밖) 삐져나온 높이의 최대값을 잰다.
blender -b -P scripts/hat_check.py   (모델을 새로 짓는다, 쉰 자세 = 리그 기본 자세)
max ≤ 0 이면 통과(음수 = 챙 두께 안에 묻힘). 머리 볼륨·다발·모자 숫자를 바꿨으면 돌려 볼 것.
검사가 실제로 잡는지: HC_TOP=0.25 blender -b -P scripts/hat_check.py (머리를 부풀리면 수천 점이 걸려야 한다)"""
import sys
import os
import math
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_model  # noqa: E402
import params as P  # noqa: E402

if os.environ.get('HC_TOP'):
    P.HAIR['top'] = float(os.environ['HC_TOP'])
bpy.ops.wm.read_factory_settings(use_empty=True)
build_model.build()
T = P.HAT
inv = bpy.data.objects['hat_root'].matrix_world.inverted()
spine = [Vector(p) for p in T['spine']]
L = [0.0]
for a, b in zip(spine, spine[1:]):
    L.append(L[-1] + (b - a).length)


def cone_at(z):
    """높이 z 의 원뿔 중심·반지름(spine 직선 구간 근사, parts_props.build_hat 과 같은 반지름 식)."""
    for i in range(len(spine) - 1):
        a, b = spine[i], spine[i + 1]
        if a.z <= z <= b.z or i == len(spine) - 2:
            t = 0 if b.z == a.z else max(0.0, min(1.0, (z - a.z) / (b.z - a.z)))
            u = (L[i] + t * (L[i + 1] - L[i])) / L[-1]
            return a.lerp(b, t), T['base_r'] * (1 + 0.06 * math.sin(math.pi * min(1, u * 3))) * (1 - u) ** 0.85


r0 = T['base_r'] * 0.45
hair = {'hair_mass', *P.HAIR_LOCKS}
dg = bpy.context.evaluated_depsgraph_get()
worst = []
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name not in hair:
        continue
    me = o.evaluated_get(dg).to_mesh()
    for v in me.vertices:
        p = inv @ (o.matrix_world @ v.co)
        rr = math.hypot(p.x, p.y)
        if rr > T['brim_r'] + 0.02:
            continue
        t = max(0.0, min(1.0, (rr - r0) / (T['brim_r'] - r0)))
        top = T['brim_curl'] * t * t + 0.018          # 챙 윗면(두께 0.036 의 절반)
        if p.z <= top - 0.036:
            continue                                  # 챙 아래: 정상
        c, r = cone_at(max(0.0, p.z))
        if math.hypot(p.x - c.x, p.y - c.y) < r - 0.004:
            continue                                  # 원뿔 안: 가려짐
        worst.append((p.z - top, o.name))
    o.evaluated_get(dg).to_mesh_clear()
worst.sort(reverse=True)
print('HATCHECK points', len(worst), 'max', round(worst[0][0], 4) if worst else 0.0, worst[:3])
