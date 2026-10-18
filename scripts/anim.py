"""애니메이션: 포즈 사이 키잉 + 2차 동작(스프링) 굽기."""
import math
import bpy
from mathutils import Vector, Matrix

import poses


def timeline(rig, keys):
    """keys: [(프레임, 포즈 이름|사전, 덧붙일 채널 사전|None, 보간)] — 포즈는 통째(절대값)로 키."""
    for f, pose, extra, interp in keys:
        poses.apply(rig, pose, extra)
        for n, path in poses.CHANNELS:
            rig.pose.bones[n].keyframe_insert(path, frame=f)
        if interp != 'BEZIER':
            set_interp(rig, f, interp)
    ease_all(rig)


def fcurves(rig):
    ad = rig.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    try:
        return list(act.fcurves)
    except AttributeError:  # 슬롯 액션(4.4+)
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out += list(bag.fcurves)
        return out


def set_interp(rig, frame, interp):
    for fc in fcurves(rig):
        for kp in fc.keyframe_points:
            if abs(kp.co.x - frame) < 0.5:
                kp.interpolation = interp


def ease_all(rig):
    for fc in fcurves(rig):
        for kp in fc.keyframe_points:
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        fc.update()


def mat_bone(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].matrix


def rel(rig, parent, child):
    d = rig.data.bones
    return d[parent].matrix_local.inverted() @ d[child].matrix_local


class Spring:
    """뼈 끝을 점 질량으로 두고 '단단할 때 끝 위치'로 끌어당긴다."""

    def __init__(self, k, c, gravity=0.0):
        self.k, self.c, self.g = k, c, gravity
        self.p = None
        self.v = Vector()

    def step(self, target, dt, wind=Vector()):
        if self.p is None:
            self.p = target.copy()
        n = 4
        h = dt / n
        for _ in range(n):
            a = (target - self.p) * self.k - self.v * self.c + Vector((0, 0, -self.g)) + wind
            self.v += a * h
            self.p += self.v * h
        return self.p


def bake_springs(rig, f0, f1, chains, wind=None, preroll=20):
    """chains: [(부모 뼈, [체인 뼈...], k, c, gravity)]. 매 프레임 회전 키를 박는다."""
    scene = bpy.context.scene
    dt = 1 / scene.render.fps
    sims = {(i, j): Spring(k, c, g) for i, (_, ch, k, c, g) in enumerate(chains) for j in range(len(ch))}
    for f in range(f0 - preroll, f1 + 1):
        scene.frame_set(max(f, f0))
        w = Vector(wind(f)) if wind else Vector()
        for i, (parent, chain, k, c, g) in enumerate(chains):
            M = mat_bone(rig, parent)
            prev = parent
            for j, name in enumerate(chain):
                R = M @ rel(rig, prev, name)
                L = rig.data.bones[name].length
                head = R.translation
                tip = R @ Vector((0, L, 0))
                p = sims[(i, j)].step(tip, dt, w)
                q = (tip - head).rotation_difference(p - head)
                R3 = R.to_3x3().normalized()
                local = (R3.inverted() @ q.to_matrix() @ R3).to_euler('XYZ')
                pb = rig.pose.bones[name]
                pb.rotation_euler = local
                if f >= f0:
                    pb.keyframe_insert('rotation_euler', frame=f)
                M = R @ local.to_matrix().to_4x4()
                prev = name


DEFAULT_CHAINS = [
    ('hat.1', ['hat.2', 'hat.3'], 170, 11, 0.0),
    ('chest', ['cape.1', 'cape.2', 'cape.3'], 70, 9, 0.0),
    ('chest', ['badge'], 230, 16, 0.0),
]
