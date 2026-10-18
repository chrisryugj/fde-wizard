"""공용 도우미: 재질, 메시 생성(쿼드 구·스윕), 표면 투사."""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree


def hex2lin(h):
    h = h.lstrip('#')
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb)


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link(ob, c=None):
    (c or bpy.context.scene.collection).objects.link(ob)
    return ob


def bm_obj(bm, name, c=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    return link(bpy.data.objects.new(name, me), c)


def subsurf(ob, levels=2, render=None):
    m = ob.modifiers.new('Subsurf', 'SUBSURF')
    m.levels = levels
    m.render_levels = render if render is not None else levels
    return m


def set_mat(ob, *mats):
    ob.data.materials.clear()
    for m in mats:
        ob.data.materials.append(m)
    return ob


# ---------------------------------------------------------------- 재질
def principled(name, color, rough=0.5, metal=0.0, coat=0.0, sss=0.0,
               emit=None, emit_strength=0.0, spec=0.5, sheen=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    lin = hex2lin(color)
    b.inputs['Base Color'].default_value = (*lin, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['Sheen Weight'].default_value = sheen
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.2)
        b.inputs['Subsurface Scale'].default_value = 0.04
    if emit:
        b.inputs['Emission Color'].default_value = (*hex2lin(emit), 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    m.diffuse_color = (*lin, 1)
    return m


def emission(name, color, strength=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*hex2lin(color), 1)
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    m.diffuse_color = (*hex2lin(color), 1)
    return m


# ---------------------------------------------------------------- 형태
def quad_sphere(cuts=5):
    """정육면체를 쪼개 구로 부풀린 쿼드 메시 — 서브디비전에 깨끗하다."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    for v in bm.verts:
        v.co = v.co.normalized()
    return bm


def deform(bm, fn):
    for v in bm.verts:
        v.co = Vector(fn(v.co.copy()))
    return bm


def ellipsoid(name, center, size, c=None, cuts=4, levels=2, fn=None):
    bm = quad_sphere(cuts)
    sx, sy, sz = size
    cx, cy, cz = center

    def f(p):
        q = Vector((p.x * sx, p.y * sy, p.z * sz))
        if fn:
            q = Vector(fn(q, p))
        return q + Vector((cx, cy, cz))
    deform(bm, f)
    ob = bm_obj(bm, name, c)
    if levels:
        subsurf(ob, levels)
    return ob


def catmull(pts, n):
    pts = [Vector(p) for p in pts]
    P = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    segs = len(pts) - 1
    for i in range(n):
        t = i / (n - 1) * segs
        k = min(int(t), segs - 1)
        u = t - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * u * u * u))
    return out


def sweep(name, spine, radius, c=None, sides=8, segs=24, aspect=1.0, up=None,
          roll=0.0, tip=True, cap0=True, levels=2, width_scale=None):
    """spine 을 따라 단면(타원)을 쓸어 만든 관. radius(u)·aspect(u)는 함수나 숫자.
    up(p,u) 가 단면 '두께' 방향(예: 머리 중심에서 바깥)을 정한다. tip=True 면 끝이 뾰족."""
    R = radius if callable(radius) else (lambda u, r=radius: r)
    A = aspect if callable(aspect) else (lambda u, a=aspect: a)
    P = catmull(spine, segs)
    n = len(P)
    T = []
    for i in range(n):
        a, b = P[max(i - 1, 0)], P[min(i + 1, n - 1)]
        T.append((b - a).normalized())
    bm = bmesh.new()
    rings = []
    prev_n = None
    for i, p in enumerate(P):
        u = i / (n - 1)
        t = T[i]
        if up:
            upv = Vector(up(p, u))
        elif prev_n is not None:
            upv = prev_n
        else:
            upv = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((0, 1, 0))
        nn = (upv - t * upv.dot(t)).normalized()
        prev_n = nn
        bb = t.cross(nn)
        r = R(u)
        if tip and i == n - 1:
            rings.append([bm.verts.new(p)])
            continue
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * k / sides + (roll(u) if callable(roll) else roll)
            off = bb * (math.cos(ang) * r) + nn * (math.sin(ang) * r * A(u))
            ring.append(bm.verts.new(p + off))
        rings.append(ring)
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        if len(r1) == 1:
            for k in range(sides):
                bm.faces.new((r0[k], r0[(k + 1) % sides], r1[0]))
        else:
            for k in range(sides):
                bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    if cap0:
        bm.faces.new(list(reversed(rings[0])))
    if not tip and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = bm_obj(bm, name, c)
    if levels:
        subsurf(ob, levels)
    return ob


def bvh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(ob, dg)


def hit(tree, origin, direction):
    loc, nor, _, _ = tree.ray_cast(Vector(origin), Vector(direction).normalized())
    return loc, nor


def frame_from_normal(nor, up=(0, 0, 1)):
    """로컬 -Y 가 표면 바깥(nor)을 보도록 하는 회전 행렬."""
    y = -Vector(nor).normalized()
    z = Vector(up)
    z = (z - y * z.dot(y)).normalized()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed().to_4x4()


def place(ob, loc, nor, up=(0, 0, 1), push=0.0):
    M = frame_from_normal(nor, up)
    M.translation = Vector(loc) + Vector(nor) * push
    ob.matrix_world = M
    return ob


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def add_rest(ob):
    """정점의 현재(월드=로컬) 좌표를 'rest' 속성으로 박아 둔다."""
    me = ob.data
    if 'rest' in me.attributes:
        me.attributes.remove(me.attributes['rest'])
    at = me.attributes.new('rest', 'FLOAT_VECTOR', 'POINT')
    mw = ob.matrix_world
    at.data.foreach_set('vector', [c for v in me.vertices for c in (mw @ v.co)])
