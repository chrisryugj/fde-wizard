"""셰이더 노드 도우미."""
from lib import hex2lin  # noqa: F401


def node(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def sock(sockets, name, typ=None):
    for s in sockets:
        if s.name == name and (typ is None or s.type == typ):
            return s
    raise KeyError(name)


def mix_color(nt, fac, a, b):
    m = node(nt, 'ShaderNodeMix', data_type='RGBA')
    nt.links.new(fac, sock(m.inputs, 'Factor', 'VALUE'))
    for s, v in ((sock(m.inputs, 'A', 'RGBA'), a), (sock(m.inputs, 'B', 'RGBA'), b)):
        if isinstance(v, tuple):
            s.default_value = v
        else:
            nt.links.new(v, s)
    return sock(m.outputs, 'Result', 'RGBA')


def blob_mask(nt, center, radius, mirror_x=True):
    """오브젝트 좌표에서 center 둘레 radius 안쪽이 1 인 부드러운 마스크."""
    sep = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(rest_coords(nt), sep.inputs[0])
    comb = node(nt, 'ShaderNodeCombineXYZ')
    if mirror_x:
        ab = node(nt, 'ShaderNodeMath', operation='ABSOLUTE')
        nt.links.new(sep.outputs['X'], ab.inputs[0])
        nt.links.new(ab.outputs[0], comb.inputs['X'])
    else:
        nt.links.new(sep.outputs['X'], comb.inputs['X'])
    nt.links.new(sep.outputs['Y'], comb.inputs['Y'])
    nt.links.new(sep.outputs['Z'], comb.inputs['Z'])
    sub = node(nt, 'ShaderNodeVectorMath', operation='SUBTRACT')
    nt.links.new(comb.outputs[0], sub.inputs[0])
    sub.inputs[1].default_value = center
    ln = node(nt, 'ShaderNodeVectorMath', operation='LENGTH')
    nt.links.new(sub.outputs[0], ln.inputs[0])
    mr = node(nt, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    nt.links.new(ln.outputs['Value'], mr.inputs['Value'])
    mr.inputs['From Min'].default_value = 0.0
    mr.inputs['From Max'].default_value = radius
    mr.inputs['To Min'].default_value = 1.0
    mr.inputs['To Max'].default_value = 0.0
    return mr.outputs['Result']


def rest_coords(nt):
    """뼈로 변형돼도 미끄러지지 않는 쉬는 자세 좌표(메시 속성 'rest')."""
    a = node(nt, 'ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='rest')
    return a.outputs['Vector']
