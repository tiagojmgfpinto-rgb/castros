# Light shared with the web viewer: reads maquetas/luz.json (the same file app/src.html uses, through build.py) and sets the
# Blender scene's sun and world to match, so a Blender render and the web model are lit alike (as castillos.site does with blender/luz.py).
# Three.js is y-up with z = south; Blender is z-up with y = north: (x, y, z)three -> (x, -z, y)blender.
# Use from another script: import luz; luz.setup(bpy.context.scene, R)   (R = disc radius in m, as in app/dio/<id>.json)
import bpy, json, math, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(site_id=None):
    L = json.load(open(os.path.join(ROOT, 'maquetas', 'luz.json')))
    if site_id:
        f = os.path.join(ROOT, 'maquetas', site_id + '.json')
        x = json.load(open(f)).get('luz', {}) if os.path.exists(f) else {}
        for k, v in x.items(): L[k] = {**L[k], **v} if isinstance(v, dict) and isinstance(L.get(k), dict) else v
    return L

def rgb(h): h = h.lstrip('#'); return [((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4)]   # sRGB -> linear (approx.)

def setup(scene, R=150, site_id=None):
    L = load(site_id); S = L['sun']
    d = Vector((S['dir'][0], -S['dir'][2], S['dir'][1])).normalized()
    sun = bpy.data.objects.get('LUZ-sun') or bpy.data.objects.new('LUZ-sun', bpy.data.lights.new('LUZ-sun', 'SUN'))
    if sun.name not in scene.collection.objects: scene.collection.objects.link(sun)
    sun.data.color = rgb(S['color']); sun.data.energy = S['i']; sun.data.angle = math.radians(1.5)
    sun.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()   # the light shines along -Z: point +Z at the sun
    H = L['hemi']; w = scene.world or bpy.data.worlds.new('LUZ-world'); scene.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    # hemisphere light: sky colour from above, ground colour from below, blended by the ray direction
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground'); mix = nt.nodes.new('ShaderNodeMixRGB')
    geo = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); mr = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(geo.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], mr.inputs[0]); mr.inputs[1].default_value = -1; mr.inputs[2].default_value = 1
    nt.links.new(mr.outputs[0], mix.inputs[0]); mix.inputs[1].default_value = (*rgb(H['ground']), 1); mix.inputs[2].default_value = (*rgb(H['sky']), 1)
    nt.links.new(mix.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = H['i']; nt.links.new(bg.outputs[0], out.inputs[0])
    vs = scene.view_settings; vs.view_transform = 'AgX' if L.get('tone') == 'neutral' else 'Filmic' if 'Filmic' in [i.identifier for i in vs.bl_rna.properties['view_transform'].enum_items] else 'AgX'
    vs.exposure = math.log2(L['exposure'])
    return sun
