# Control render (Cycles, CPU) of a site model with the shared light (blend/luz.py), from the web viewer's default oblique view.
# Use: /opt/bvenv/bin/python blend/luz_render.py <model .glb> <out .png> [site id]
import bpy, sys, os, json, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import luz
glb, out = sys.argv[1:3]; sid = sys.argv[3] if len(sys.argv) > 3 else None
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=glb)
for o in list(sc.objects):
    if o.name.startswith(('PROTO-', 'B-')): o.hide_render = True   # current state (A): reconstitution-only pieces hidden
meta = json.load(open(os.path.join(luz.ROOT, 'app', 'dio', sid + '.json'))) if sid else {}
R = meta.get('R', 150); luz.setup(sc, R, sid)
# camera: the viewer's default direction (-0.35 R, 1.75 R + 4, 2.75 R) in three.js axes, framing the disc
h = Vector((-0.35 * R, -(2.75 * R), 1.75 * R + 4)).normalized()
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.angle = math.radians(32); cam.location = h * R * 4.3; cam.rotation_euler = (-h).to_track_quat('-Z', 'Y').to_euler()
cam.data.clip_end = R * 20
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = True   # Eevee needs a GPU (EGL); the trees are instanced only in the web viewer
sc.render.resolution_x, sc.render.resolution_y = 1200, 760; sc.render.film_transparent = True
sc.render.filepath = out; bpy.ops.render.render(write_still=True); print('written', out)
