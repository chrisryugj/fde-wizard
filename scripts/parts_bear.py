"""곰돌이(gomdori) 마스코트 — 모자에서 튀어나오는 꼬마 마법사. 원점=발밑."""
import math
import bpy

import params as P
from lib import ellipsoid, sweep, principled, emission, set_mat, coll, lerp
from parts_props import star_mesh

C = P.COLORS


def build_bear():
    c = coll('BEAR')
    fur = principled('bear_fur', '#C98B4E', rough=0.75, sheen=0.6)
    cream = principled('bear_cream', '#F4DFBF', rough=0.7, sheen=0.4)
    dark = principled('bear_dark', '#2E1C14', rough=0.25, coat=0.8)
    hi = emission('eye_hi', C['eye_hi'], 2.5)
    blush = principled('bear_blush', '#F08F86', rough=0.6)
    parts = {}
    parts['bear_body'] = set_mat(ellipsoid('bear_body', (0, 0, 0.115), (0.10, 0.085, 0.11), c, cuts=4), fur)
    parts['bear_belly'] = set_mat(ellipsoid('bear_belly', (0, -0.055, 0.105), (0.065, 0.04, 0.07), c, cuts=3), cream)
    parts['bear_head'] = set_mat(ellipsoid('bear_head', (0, 0, 0.30), (0.135, 0.12, 0.118), c, cuts=5), fur)
    parts['bear_snout'] = set_mat(ellipsoid('bear_snout', (0, -0.105, 0.272), (0.055, 0.035, 0.04), c, cuts=3), cream)
    parts['bear_nose'] = set_mat(ellipsoid('bear_nose', (0, -0.138, 0.288), (0.02, 0.012, 0.014), c, cuts=2), dark)
    for side, tag in ((-1, 'R'), (1, 'L')):
        parts[f'bear_ear.{tag}'] = set_mat(ellipsoid(f'bear_ear.{tag}', (side * 0.095, 0.0, 0.40), (0.045, 0.03, 0.045), c, cuts=3), fur)
        parts[f'bear_earin.{tag}'] = set_mat(ellipsoid(f'bear_earin.{tag}', (side * 0.095, -0.018, 0.40), (0.026, 0.015, 0.026), c, cuts=2), cream)
        parts[f'bear_eye.{tag}'] = set_mat(ellipsoid(f'bear_eye.{tag}', (side * 0.05, -0.108, 0.318), (0.017, 0.01, 0.021), c, cuts=2), dark)
        parts[f'bear_eyehi.{tag}'] = set_mat(ellipsoid(f'bear_eyehi.{tag}', (side * 0.05 + 0.005, -0.119, 0.326), (0.0055, 0.002, 0.0055), c, cuts=1), hi)
        parts[f'bear_blush.{tag}'] = set_mat(ellipsoid(f'bear_blush.{tag}', (side * 0.088, -0.09, 0.27), (0.022, 0.008, 0.014), c, cuts=2), blush)
        arm = ellipsoid(f'bear_arm.{tag}', (0, 0, 0), (0.035, 0.035, 0.06), c, cuts=3)
        arm.location = (side * 0.10, -0.01, 0.15)
        arm.rotation_euler = (0, side * 0.6, 0)
        parts[f'bear_arm.{tag}'] = set_mat(arm, fur)
        parts[f'bear_leg.{tag}'] = set_mat(ellipsoid(f'bear_leg.{tag}', (side * 0.05, -0.02, 0.03), (0.042, 0.05, 0.035), c, cuts=3), fur)
    # 꼬마 마법사 모자
    hat = sweep('bear_hat', [(0, 0.0, 0.40), (0, 0.01, 0.48), (0.02, 0.05, 0.56), (0.06, 0.10, 0.60)],
                lambda u: 0.075 * (1 - u) ** 0.9, c, sides=16, segs=24, tip=True, cap0=True)
    parts['bear_hat'] = set_mat(hat, bpy.data.materials['cape'])
    brim = ellipsoid('bear_hat_brim', (0, 0.0, 0.40), (0.11, 0.11, 0.012), c, cuts=3)
    parts['bear_hat_brim'] = set_mat(brim, bpy.data.materials['cape'])
    st = star_mesh('bear_hat_star', c, r=0.022, depth=0.008)
    st.location = (0, -0.07, 0.445)
    parts['bear_hat_star'] = set_mat(st, bpy.data.materials['star'])
    # 노란 목도리(주인 색)
    sc = sweep('bear_scarf', [(0.098 * math.sin(a), -0.088 * math.cos(a), 0.205) for a in
                              [math.radians(-178 + 356 * k / 24) for k in range(25)]], 0.03, c, sides=10, segs=48,
               aspect=0.75, tip=False)
    parts['bear_scarf'] = set_mat(sc, bpy.data.materials['star'])
    return parts
