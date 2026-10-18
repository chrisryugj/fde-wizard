"""무대 소품: 서류 더미, 화분, 배경 별. 레퍼런스의 대나무·석등처럼 화면 양끝에서 테마를 알린다."""
import math
import random
import bpy
import bmesh
from mathutils import Vector

from lib import coll, principled, emission, bm_obj, ellipsoid, sweep, subsurf
import fx


def box(name, c, size, loc, rot=0.0, mat=None, bevel=0.004):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    ob = bm_obj(bm, name, c, smooth=False)
    if bevel:
        b = ob.modifiers.new('Bevel', 'BEVEL')
        b.width = bevel
        b.segments = 2
    ob.location = loc
    ob.rotation_euler = (0, 0, rot)
    if mat:
        ob.data.materials.append(mat)
    return ob


def doc_stack(name, base, layers=7, seed=5, label='HWP', c=None, thick=1.0):
    """종이 묶음이 삐뚤빼뚤 쌓인 탑 + 집게 + 라벨."""
    c = c or coll('PROPS')
    rnd = random.Random(seed)
    paper = principled('paper', '#F7F4EC', rough=0.8, spec=0.2)
    folders = [principled('folder_b', '#4C7BD9', rough=0.6), principled('folder_y', '#F2C14E', rough=0.6),
               principled('folder_g', '#7CC6A4', rough=0.6)]
    obs = []
    z = base[2]
    for i in range(layers):
        h = rnd.uniform(0.06, 0.12) * thick
        w, d = rnd.uniform(0.40, 0.46), rnd.uniform(0.30, 0.34)
        off = Vector((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), 0))
        rot = rnd.uniform(-0.18, 0.18)
        p = box(f'{name}_p{i}', c, (w, d, h), Vector(base) + off + Vector((0, 0, z - base[2] + h / 2)), rot, paper, 0.003)
        obs.append(p)
        if rnd.random() < 0.45:
            f = box(f'{name}_f{i}', c, (w + 0.02, d + 0.01, 0.012), p.location + Vector((0, 0, -h / 2 - 0.006)), rot,
                    rnd.choice(folders), 0.003)
            obs.append(f)
        z += h + 0.012
    clip = principled('clip', '#2B2F3A', rough=0.3, metal=0.8)
    top = obs[-1]
    cl = box(f'{name}_clip', c, (0.08, 0.05, 0.03), top.location + Vector((0, -0.12, top.dimensions.z / 2)), top.rotation_euler.z, clip)
    obs.append(cl)
    lab = fx.text3d(f'{name}_label', label, 0.07, principled('label_ink', '#1E3A8A', rough=0.5), c, extrude=0.002)
    mid = obs[len(obs) // 2]
    lab.location = mid.location + Vector((0, -mid.dimensions.y / 2 - 0.004, 0))
    lab.rotation_euler = (math.pi / 2, 0, mid.rotation_euler.z)
    obs.append(lab)
    return obs


def plant(name, base, c=None, seed=9):
    """둥근 화분 + 통통한 잎."""
    c = c or coll('PROPS')
    rnd = random.Random(seed)
    pot = sweep(f'{name}_pot', [(base[0], base[1], base[2]), (base[0], base[1], base[2] + 0.30)],
                lambda u: 0.16 + 0.04 * u, c, sides=20, segs=6, tip=False, levels=2)
    pot.data.materials.append(principled('pot', '#F3EEE6', rough=0.5, spec=0.4))
    soil = ellipsoid(f'{name}_soil', (base[0], base[1], base[2] + 0.28), (0.18, 0.18, 0.03), c, cuts=3)
    soil.data.materials.append(principled('soil', '#5A4030', rough=0.9))
    leaf = principled('leaf', '#5FAF6E', rough=0.55, sheen=0.3)
    obs = [pot, soil]
    for i in range(9):
        a = 2 * math.pi * i / 9 + rnd.uniform(-0.2, 0.2)
        L = rnd.uniform(0.35, 0.6)
        p0 = Vector((base[0], base[1], base[2] + 0.28))
        tip = p0 + Vector((math.cos(a) * L * 0.55, math.sin(a) * L * 0.55, L))
        mid = p0.lerp(tip, 0.5) + Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.05))
        lf = sweep(f'{name}_leaf{i}', [p0, mid, tip], lambda u: 0.07 * math.sin(math.pi * min(1, 0.1 + u)) + 0.005,
                   c, sides=8, segs=14, aspect=0.25, tip=True, up=lambda p, u, a=a: (math.cos(a), math.sin(a), 0.2))
        lf.data.materials.append(leaf)
        obs.append(lf)
    return obs


def wall_stars(c=None, n=26, seed=4, y=7.6):
    """뒷벽에 흐릿한 별 몇 개(마법 분위기)."""
    c = c or coll('PROPS')
    rnd = random.Random(seed)
    m = emission('wall_star', '#FFE7A3', 1.4)
    obs = []
    for i in range(n):
        ob = fx.twinkle_mesh(f'wstar{i}', c, r=rnd.uniform(0.03, 0.07))
        ob.location = (rnd.uniform(-4.2, 4.2), y + rnd.uniform(-0.1, 0.1), rnd.uniform(1.6, 4.6))
        ob.rotation_euler = (0, rnd.uniform(0, 0.8), 0)
        ob.data.materials.append(m)
        obs.append(ob)
    return obs


def studio_props():
    doc_stack('docs', (-1.75, 1.3, 0.0), layers=9, seed=5)
    doc_stack('docs2', (-2.35, 1.7, 0.0), layers=5, seed=6, label='PDF')
    plant('plant', (1.85, 1.4, 0.0))
    wall_stars()
