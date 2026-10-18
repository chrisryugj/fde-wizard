"""무대: 사이클로라마 배경, 조명 3점, 카메라, 렌더 설정."""
import math
import bpy
import bmesh
from mathutils import Vector
from lib import hex2lin, link, coll, principled

import params as P


def render_settings(w=1920, h=1080, samples=64, look='AgX - Medium High Contrast', exposure=-0.15):
    s = bpy.context.scene
    s.render.engine = 'BLENDER_EEVEE'
    s.render.resolution_x, s.render.resolution_y = w, h
    s.render.resolution_percentage = 100
    s.eevee.taa_render_samples = samples
    s.eevee.use_raytracing = True
    s.eevee.use_shadows = True
    s.eevee.use_fast_gi = True
    s.eevee.shadow_resolution_scale = 1.0
    s.view_settings.view_transform = 'AgX'
    s.view_settings.look = look
    s.view_settings.exposure = exposure
    s.render.image_settings.file_format = 'PNG'
    s.render.film_transparent = False


def world(color='#EEE6D9', strength=0.55):
    w = bpy.data.worlds.get('W') or bpy.data.worlds.new('W')
    bpy.context.scene.world = w
    bg = w.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (*hex2lin(color), 1)
    bg.inputs['Strength'].default_value = strength
    return w


def cyclorama(color=None, radius=2.5, width=30, depth=14, height=10):
    """바닥과 벽이 둥글게 이어진 배경판."""
    c = coll('STAGE')
    bm = bmesh.new()
    rows = []
    prof = []
    # 앞 바닥(-y) → 곡면 → 뒷벽(+z)
    for i in range(12):
        prof.append((-depth + (depth - 0.01) * i / 11, 0.0))
    for i in range(1, 17):
        a = math.pi / 2 * i / 16
        prof.append((math.sin(a) * radius, radius - math.cos(a) * radius))
    for i in range(1, 10):
        prof.append((radius, radius + (height - radius) * i / 9))
    for y, z in prof:
        row = []
        for k in range(13):
            x = -width / 2 + width * k / 12
            row.append(bm.verts.new((x, y + 6.0, z)))
        rows.append(row)
    for i in range(len(rows) - 1):
        for k in range(12):
            bm.faces.new((rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]))
    me = bpy.data.meshes.new('cyc')
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = link(bpy.data.objects.new('cyclorama', me), c)
    m = principled('cyc', color or P.COLORS['bg'], rough=0.9, spec=0.2)
    ob.data.materials.append(m)
    return ob


def area(name, loc, target, energy, size, color='#FFFFFF'):
    l = bpy.data.lights.new(name, 'AREA')
    l.energy = energy
    l.size = size
    l.color = hex2lin(color)
    ob = link(bpy.data.objects.new(name, l), coll('STAGE'))
    ob.location = loc
    look_at(ob, target)
    return ob


def look_at(ob, target, roll=0.0):
    d = Vector(target) - Vector(ob.location)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    if roll:
        ob.rotation_euler.rotate_axis('Z', roll)


def lights(target=(0, 0, 1.1), scale=1.0):
    return {
        'key': area('key', (-2.6, -3.6, 3.6), target, 900 * scale, 3.0, '#FFF0DF'),
        'fill': area('fill', (3.2, -2.8, 1.8), target, 260 * scale, 4.0, '#E2EBFF'),
        'rim': area('rim', (1.6, 3.2, 3.6), target, 700 * scale, 2.0, '#FFFFFF'),
    }


def camera(name='cam', lens=85):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start = 0.05
    cam.clip_end = 200
    ob = link(bpy.data.objects.new(name, cam), coll('STAGE'))
    bpy.context.scene.camera = ob
    return ob


def orbit(cam, target, dist, azim_deg, elev_deg):
    a, e = math.radians(azim_deg), math.radians(elev_deg)
    t = Vector(target)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    look_at(cam, t)


def render(path):
    s = bpy.context.scene
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)


def bloom(threshold=1.0, strength=0.5, size=0.55):
    """컴포지터: 빛나는 것만 번지게(블룸)."""
    s = bpy.context.scene
    ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree')
    ng.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    s.compositing_node_group = ng
    rl = ng.nodes.new('CompositorNodeRLayers')
    gl = ng.nodes.new('CompositorNodeGlare')
    gl.inputs['Type'].default_value = 'Bloom'
    gl.inputs['Quality'].default_value = 'High'
    gl.inputs['Threshold'].default_value = threshold
    gl.inputs['Strength'].default_value = strength
    gl.inputs['Size'].default_value = size
    out = ng.nodes.new('NodeGroupOutput')
    ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
    ng.links.new(gl.outputs['Image'], out.inputs['Image'])
    s.render.use_compositing = True
    return ng
