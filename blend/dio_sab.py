# Builds a castillos-style disc diorama of one castro in Blender (bpy) and exports a GLB for three.js.
# Castro de Sabroso. Usage: /opt/bvenv/bin/python blend/dio_sab.py guimaraes-castro-de-sabroso
# Terrain, wall footing and trees from the DGT LiDAR 2025 point cloud (lidar/sab_laz.py → lidar/sab_*25.npy);
# 1930 plan georeferenced on the LiDAR rampart (lidar/sab_georef.py → blend/sab_fit.json).
# Local frame: x east, y north (Blender Z up), metres, origin = disc centre.
import sys, json, math, importlib, os
import numpy as np
import bpy, bmesh
from PIL import Image, ImageFilter, ImageEnhance
from scipy.interpolate import RectBivariateSpline
from scipy.ndimage import gaussian_filter, maximum_filter, label

SID = sys.argv[-1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, 'blend')
P = importlib.import_module({'guimaraes-castro-de-sabroso': 'sab_plan'}[SID])
FIT = json.load(open('blend/sab_fit.json'))
rng = np.random.default_rng(11)

# ---------- plan -> local metres (x east, z south), then to Blender (x, y=-z)
mean = np.array(FIT['mean']); K = FIT['K']; tx, tz, th, kk = FIT['x']
def plan2m(p):
    q = (np.asarray(p, float) - mean) * K * kk; c, s = math.cos(th), math.sin(th)
    return np.stack([q[..., 0] * c - q[..., 1] * s, q[..., 0] * s + q[..., 1] * c], -1) + [tx, tz]
allw = np.vstack([plan2m(L) for L in [P.W_WEST, P.W_LOWER, P.W_EAST_OUTER, P.W_EAST_INNER]])
CX, CZ = (allw.min(0) + allw.max(0)) / 2          # disc centre in the -c.jpg frame (m from site point)
R = float(np.max(np.hypot(allw[:, 0] - CX, allw[:, 1] - CZ))) + 24
def loc(p):  # plan px -> Blender xy
    m = plan2m(p); return np.stack([m[..., 0] - CX, -(m[..., 1] - CZ)], -1)

# ---------- terrain heights: DGT LiDAR 2025 ground points (class 2), TIN on a 25 cm grid, lightly smoothed
from scipy.ndimage import map_coordinates
X0L, Y0L = -17399.0506, 204754.9092                     # site point in PT-TM06
LB = json.load(open('lidar/sab_box.json'))
DTM = gaussian_filter(np.load('lidar/sab_dtm25.npy').astype(np.float32), 1.)
CHM = np.load('lidar/sab_dsm25.npy').astype(np.float32) - np.load('lidar/sab_dtm25.npy').astype(np.float32)
def _rc(x, y):  # Blender xy -> grid row/col
    lx = np.asarray(x, float) + CX; lz = CZ - np.asarray(y, float)
    return (LB['y1'] - (Y0L - lz)) / LB['cs'] - .5, (X0L + lx - LB['x0']) / LB['cs'] - .5
def _samp(A, x, y, order=1):
    r, c = _rc(x, y); return map_coordinates(A, [np.atleast_1d(r).ravel(), np.atleast_1d(c).ravel()], order=order, mode='nearest').reshape(np.shape(r))
def hraw(x, y): return _samp(DTM, x, y)
H0 = float(hraw(0, 0)); EX = 1.15
def hz(x, y): return (hraw(x, y) - H0) * EX

def new_obj(name, me, mat=None):
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    if mat: me.materials.append(mat)
    return ob
def img_mat(name, path, rough=.95, alpha=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.abspath(path))
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); return m, t
def col_mat(name, rgb, rough=.9):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*[c / 255 for c in rgb], 1); b.inputs['Roughness'].default_value = rough; return m
def mesh_from(name, V, F, UV=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in V], [], [tuple(f) for f in F])
    if UV is not None:
        uvl = me.uv_layers.new(name='UVMap'); loops = [li for f in me.polygons for li in f.loop_indices]
        vi = np.array([me.loops[li].vertex_index for li in loops]); uvl.data.foreach_set('uv', np.asarray(UV)[vi].ravel())
    me.validate(); me.update(); return me

for o in list(bpy.data.objects): bpy.data.objects.remove(o)

# ---------- ground texture: orthophoto crop of the disc, warmed slightly
ORT = Image.open(f'app/t3/{SID}-c.jpg').convert('RGB')     # 4 px/m, centre (1024,1024)
px0 = 1024 + (CX - R) * 4; py0 = 1024 + (CZ - R) * 4; S = int(2 * R * 4)
crop = ORT.crop((int(px0), int(py0), int(px0) + S, int(py0) + S)).resize((2048, 2048), Image.LANCZOS)
crop = ImageEnhance.Color(crop).enhance(1.12); crop = ImageEnhance.Brightness(crop).enhance(1.06)
crop.save('blend/ground_raw.jpg', quality=92)
def uv_of(x, y): return np.stack([(x + R) / (2 * R), (y + R) / (2 * R)], -1)

# ---------- terrain disc (polar grid)
NR, NA = 260, 800
rr = np.linspace(0, R, NR + 1)[1:]; aa = np.linspace(0, 2 * np.pi, NA, endpoint=False)
X = np.concatenate([[0], (rr[:, None] * np.cos(aa)[None]).ravel()]); Y = np.concatenate([[0], (rr[:, None] * np.sin(aa)[None]).ravel()])
Z = hz(X, Y); V = np.stack([X, Y, Z], 1); F = []
for a in range(NA): F.append((0, 1 + a, 1 + (a + 1) % NA))
for r in range(NR - 1):
    o0, o1 = 1 + r * NA, 1 + (r + 1) * NA
    for a in range(NA): b = (a + 1) % NA; F.append((o0 + a, o1 + a, o1 + b, o0 + b))
gmat, gtex = img_mat('ground', 'blend/ground_raw.jpg')
terrain = new_obj('terrain', mesh_from('terrain', V, F, uv_of(X, Y)), gmat)
for p in terrain.data.polygons: p.use_smooth = True
rim = np.arange(1 + (NR - 1) * NA, 1 + NR * NA)

# ---------- earth skirt with strata, and base
zb = float(Z.min()) - 16
sx, sy, sz = X[rim], Y[rim], Z[rim]
SV = []; SF = []; SUV = []
levels = [0, 1.2, 4, 7, 10, 13, None]
for li, d in enumerate(levels):
    for a in range(NA):
        z = zb if d is None else sz[a] - d
        SV.append((sx[a] * (1 + .0 * li), sy[a], z)); SUV.append((a / NA * 12, (z - zb) / 40))
for li in range(len(levels) - 1):
    for a in range(NA):
        b = (a + 1) % NA; SF.append((li * NA + a, li * NA + b, (li + 1) * NA + b, (li + 1) * NA + a))
cap = len(SV); SV.append((0, 0, zb)); SUV.append((.5, .5))
for a in range(NA): SF.append(((len(levels) - 1) * NA + (a + 1) % NA, (len(levels) - 1) * NA + a, cap))
# strata texture
st = np.zeros((256, 64, 3)); yy = np.arange(256)[:, None] / 256
band = (np.sin(yy * 40 + np.sin(np.arange(64)[None] / 64 * 2 * np.pi * 3) * .6) * .5 + .5)
st[...] = np.array([120, 86, 56]) * (.78 + .3 * band[..., None]); st[:20] = [92, 120, 60]
st[20:26] = [88, 64, 42]
Image.fromarray(np.clip(st[::-1] + rng.normal(0, 6, st.shape), 0, 255).astype(np.uint8)).resize((64, 256)).save('blend/strata.jpg', quality=90)
smat, _ = img_mat('earth', 'blend/strata.jpg')
skirt = new_obj('skirt', mesh_from('skirt', SV, SF, SUV), smat)

# ---------- wall sweep helper (trapezoid profile following the ground)
stone_m, _ = img_mat('stone', 'blend/stone.jpg', .85)
def dense(pts, step=.8, closed=False):
    pts = np.asarray(pts, float)
    if closed: pts = np.vstack([pts, pts[:1]])
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        for t in np.linspace(0, 1, n + 1)[1:]: out.append(a * (1 - t) + b * t)
    return np.array(out)
def sweep(pts, w, h, jitter=.25, sink=.6, closed=False, top_taper=.85):
    p = dense(pts, closed=closed); n = len(p)
    if n < 2: return [], [], []
    d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    nr = np.stack([-d[:, 1], d[:, 0]], 1)
    g = hz(p[:, 0], p[:, 1])
    hh = h + gaussian_filter(rng.normal(0, jitter, n), 2.5, mode='wrap' if closed else 'nearest')
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    prof = [(-w / 2, -sink), (-w / 2 * top_taper, 1), (w / 2 * top_taper, 1), (w / 2, -sink)]
    V = []; UV = []
    for i in range(n):
        for j, (o, zz) in enumerate(prof):
            z = g[i] + (zz if zz < 0 else hh[i])
            V.append((p[i, 0] + nr[i, 0] * o, p[i, 1] + nr[i, 1] * o, z))
            UV.append((s[i] / 2.2, (z - g[i]) / 2.2 + j * .37))
    F = []
    for i in range(n - 1):
        for j in range(3): a = i * 4 + j; F.append((a, a + 4, a + 5, a + 1))
    if not closed: F += [(0, 1, 2, 3), ((n - 1) * 4 + 3, (n - 1) * 4 + 2, (n - 1) * 4 + 1, (n - 1) * 4)]
    return V, F, UV
class Acc:
    def __init__(s): s.V = []; s.F = []; s.UV = []
    def add(s, r):
        V, F, UV = r; o = len(s.V); s.V += V; s.UV += UV; s.F += [tuple(i + o for i in f) for f in F]
    def obj(s, name, mat, smooth=False):
        if not s.V: return None
        ob = new_obj(name, mesh_from(name, s.V, s.F, s.UV), mat)
        for p in ob.data.polygons: p.use_smooth = smooth
        return ob
# ---------- structures: one object per documented structure, mode A (current state) and B (reconstitution)
CAT = []          # catalogue for the viewer: id, name, kind, phase, evidence, sources
def put(sid, name, mat, geo, mode, ev):
    A = Acc()
    for g in geo: A.add(g)
    o = A.obj(f'{mode}-{sid}', mat)
    if o: o['sid'] = sid; o['mode'] = mode; o['ev'] = ev
    return o
def item(**k): CAT.append(k)
WALLS = [  # id, plan line, name, phase, width, height now, height in reconstitution, evidence of the reconstituted height
 ('M1', P.W_WEST, 'Muralha do recinto superior, troço poente', '1.ª/2.ª fase', 4.0, 3.2, 5.0, 'doc'),
 ('M2', P.W_EAST_INNER, 'Muralha do recinto superior, troço nascente (aparelho poligonal)', '1.ª/2.ª fase', 4.0, 3.4, 5.2, 'doc'),
 ('M3', P.W_LOWER, 'Muralha do alargamento sul', '3.ª fase', 2.6, 2.0, 3.5, 'hip'),
 ('M4', P.W_EAST_OUTER, 'Muralha do alargamento nascente', '3.ª fase', 2.6, 2.0, 3.5, 'hip'),
]
# The LiDAR ground model already holds the rampart (the stone bank is classified as ground), so the wall is laid over the real
# slope: current state = stone skin a little above the crest of the bank; reconstitution = outer face of hb metres above the outer foot.
from scipy.ndimage import gaussian_filter1d
def rampart(pts, w, hb=None, jitter=.2, sink=.8, taper=.85):
    p = dense(pts); n = len(p)
    d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9; nr = np.stack([-d[:, 1], d[:, 0]], 1)
    o = np.linspace(-w / 2 - 1.5, w / 2 + 1.5, 9)
    prof = hz(p[:, 0, None] + nr[:, 0, None] * o, p[:, 1, None] + nr[:, 1, None] * o)
    crest = gaussian_filter1d(prof.max(1), 3, mode='nearest'); foot = gaussian_filter1d(prof.min(1), 3, mode='nearest')
    jit = gaussian_filter1d(rng.normal(0, jitter, n), 2.5, mode='nearest')
    top = crest + .35 + jit if hb is None else np.maximum(foot + hb, crest + 1.0) + jit * .3
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]); V = []; UV = []
    for i in range(n):
        for j, (oo, up) in enumerate([(-w / 2, 0), (-w / 2 * taper, 1), (w / 2 * taper, 1), (w / 2, 0)]):
            q = p[i] + nr[i] * oo; z = top[i] if up else float(hz(q[0], q[1])) - sink
            V.append((q[0], q[1], z)); UV.append((s[i] / 2.2, (z - foot[i]) / 2.2 + j * .37))
    F = [(i * 4 + j, i * 4 + j + 4, i * 4 + j + 5, i * 4 + j + 1) for i in range(n - 1) for j in range(3)]
    F += [(0, 1, 2, 3), ((n - 1) * 4 + 3, (n - 1) * 4 + 2, (n - 1) * 4 + 1, (n - 1) * 4)]
    return V, F, UV
def bank_drop(pts, half=4.0):   # median height drop (m, not exaggerated) across the wall line in the LiDAR ground model
    p = dense(pts, 2); d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9; nr = np.stack([-d[:, 1], d[:, 0]], 1)
    o = np.linspace(-half, half, 9); pr = hraw(p[:, 0, None] + nr[:, 0, None] * o, p[:, 1, None] + nr[:, 1, None] * o)
    return float(np.median(pr.max(1) - pr.min(1)))
WALL_DROP = {}
for sid, L, name, ph, w, h, hb, evb in WALLS:
    put(sid, name, stone_m, [rampart(loc(L), w)], 'A', 'conf')
    put(sid, name, stone_m, [rampart(loc(L), w, hb, .12, taper=.92)], 'B', evb)
    dr = bank_drop(loc(L)); WALL_DROP[sid] = dr
    item(id=sid, name=name, kind='Muralha', phase=ph, ev='conf', evB=evb,
         dims=f'largura ≈ {w:g} m · desnível atual na linha da muralha ≈ {dr:.1f} m (LiDAR) · reconstituição: face externa com {hb:g} m',
         note='Traçado da planta de 1930 (Cardozo), confirmado pelo painel de 2021 e pelo talude da muralha no modelo do terreno LiDAR da DGT (2025). No estado atual a pedra cobre o talude real. ' + ('Altura de reconstituição segundo Cardozo (1976): 3 a 5 m; face externa com 5,20 m medida em 2015.' if evb == 'doc' else 'A altura original deste troço não está publicada: valor hipotético, por comparação com o recinto superior.'),
         src=['cardozo1930', 'era2021', 'lidar', 'cardozo1976' if evb == 'doc' else 'loureiro1999'] + (['cruz2015'] if sid == 'M2' else []))
print('bank drop', {k: round(v, 1) for k, v in WALL_DROP.items()})
# SE entrance: elbow corridor (3rd phase), drawn in the 1930 plan
ent = [sweep(loc(P.W_SE), 1.6, 1.4, .25)] + [sweep(loc(L), 1.2, 1.4, .2) for L in P.W_INNER[:2]]
put('E1', 'Entrada SE', stone_m, ent, 'A', 'conf'); put('E1', 'Entrada SE', stone_m, [sweep(loc(P.W_SE), 1.6, 3.0, .1)] + [sweep(loc(L), 1.2, 3.0, .1) for L in P.W_INNER[:2]], 'B', 'hip')
item(id='E1', name='Entrada SE em corredor de cotovelo', kind='Entrada', phase='3.ª fase', ev='conf', evB='hip', dims='corredor com cerca de 18 m',
     note='Muros do corredor segundo a planta de 1930; interpretação como entrada em cotovelo de Hawkes (1958). Altura reconstituída hipotética.', src=['cardozo1930', 'hawkes1958', 'loureiro1999'])
for i, L in enumerate(P.W_INNER[2:]):
    sid = f'W{i + 1:02d}'
    put(sid, 'Muro', stone_m, [sweep(loc(L), .8, .9, .2, .4)], 'A', 'conf'); put(sid, 'Muro', stone_m, [sweep(loc(L), .8, 1.6, .05, .4)], 'B', 'hip')
    item(id=sid, name='Muro associado às habitações', kind='Muro', phase='—', ev='conf', evB='hip', dims='largura ≈ 0,8 m',
         note='Muros de pedra dispersos, associados às casas (Loureiro 1999). Traçado da planta de 1930; altura hipotética.', src=['cardozo1930', 'loureiro1999'])
# round houses (diameters measured on the 1930 plan, kept within the 3,50–5,27 m range published by Cartailhac)
th_m, _ = img_mat('thatch', 'blend/thatch.jpg', 1)
hpos = []
cyl = lambda c, rad, n=28: [(c[0] + math.cos(a) * rad, c[1] + math.sin(a) * rad) for a in np.linspace(0, 2 * np.pi, n + 1)[:-1]]
north_lim = loc([0, 760])[1]
hn = 0
for (x, y, r) in P.HOUSES:
    c = loc([x, y]); dia = float(np.clip(2 * r * K * kk, 3.5, 5.27)); rad = dia / 2
    if (x, y) == P.CISTERN_HOUSE:
        put('C1', 'Cisterna', stone_m, [sweep(cyl(c, rad), .55, .6, .05, .5, closed=True)], 'A', 'conf')
        item(id='C1', name='Cisterna', kind='Estrutura hidráulica', phase='—', ev='conf', evB='conf', dims=f'diâmetro ≈ {dia:.1f} m', note='Identificada como cisterna (n.º 1) na legenda da planta de 1930.', src=['cardozo1930'])
        hpos.append((c[0], c[1], rad)); continue
    hn += 1; sid = f'H{hn:02d}'; hpos.append((c[0], c[1], rad))
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .5, .7 + rng.random() * .35, .1, .3, closed=True)], 'A', 'conf')
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .5, 2.1, .02, .3, closed=True, top_taper=1)], 'B', 'doc')
    gz = float(hz(c[0], c[1])) + 2.1; rr2 = rad + .6; hr = rad * 1.15
    rv = [(c[0], c[1], gz + hr)] + [(c[0] + math.cos(k / 24 * 2 * np.pi) * rr2, c[1] + math.sin(k / 24 * 2 * np.pi) * rr2, gz - .3) for k in range(24)]
    ro = put(sid + 'R', 'Cobertura', th_m, [(rv, [(0, 1 + k, 1 + (k + 1) % 24) for k in range(24)], [(.5, .5)] + [(k / 24 * 3, 1.5) for k in range(24)])], 'B', 'hip')
    if ro:
        for p in ro.data.polygons: p.use_smooth = True
    zone = 'tabuleiro superior (norte)' if c[1] > north_lim else 'tabuleiro inferior (sul)'
    item(id=sid, name=f'Casa circular {hn}', kind='Habitação', phase=zone, ev='conf', evB='doc', roof='hip', dims=f'diâmetro ≈ {dia:.1f} m (medido na planta de 1930)',
         note='Planta circular em pedra. Reconstituição: paredes com 2,10 m, altura da reconstituição de Martins Sarmento no Museu de Guimarães (Pereira 1938). A cobertura cónica é hipotética: o material (vegetal ou placas de xisto, proposta de Sarmento nunca confirmada) é desconhecido. A posição das portas não está documentada e não foi representada.',
         src=['cardozo1930', 'sarmento1909', 'pereira1938', 'cruz2015'])
for i, (x, y) in enumerate(P.FILLED):
    c = loc([x, y]); sid = f'X{i + 1}'
    put(sid, 'Estrutura circular', stone_m, [sweep(cyl(c, 1.3, 18), .5, .45, .05, .3, closed=True)], 'A', 'conf')
    item(id=sid, name='Estrutura circular preenchida', kind='Indeterminada', phase='—', ev='conf', evB='conf', dims='diâmetro ≈ 2,6 m',
         note='Representada a cheio na planta de 1930; função não identificada nas fontes consultadas.', src=['cardozo1930'])
print('houses', hn)

# ---------- granite outcrops (gravuras / gruta are on these)
rock_m = col_mat('granite', (122, 116, 104), .95)
bm = bmesh.new()
for (x, y, r) in P.ROCKS:
    c = loc([x, y]); rad = r * K * kk
    for k in range(max(1, int(rad / 1.6))):
        tmp = bmesh.new(); bmesh.ops.create_icosphere(tmp, subdivisions=2, radius=1)
        sc = np.array([rad * (.35 + .4 * rng.random()), rad * (.3 + .35 * rng.random()), 1.2 + rng.random() * 1.6])
        off = (rng.random(2) - .5) * rad * 1.1; ang = rng.random() * np.pi
        for v in tmp.verts:
            p = np.array(v.co) * sc * (1 + rng.normal(0, .07)); ca, sa = math.cos(ang), math.sin(ang)
            v.co = (c[0] + off[0] + p[0] * ca - p[1] * sa, c[1] + off[1] + p[0] * sa + p[1] * ca, 0)
            v.co.z = float(hz(v.co.x, v.co.y)) + max(-.6, p[2] * .4 - .5)   # low: the outcrop relief is already in the LiDAR ground
        me = bpy.data.meshes.new('t'); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
from matplotlib.path import Path as MPath
_encl0 = MPath(loc(P.W_WEST + P.W_LOWER + P.W_EAST_OUTER[::-1] + P.W_EAST_INNER[::-1]))
me = bpy.data.meshes.new('rocks'); bm.to_mesh(me); bm.free(); rocks = new_obj('AB-R', me, rock_m); rocks['sid'] = 'R'; rocks['mode'] = 'AB'; rocks['ev'] = 'conf'
item(id='R', name='Afloramentos graníticos', kind='Afloramento', phase='—', ev='conf', evB='conf', dims='formas simplificadas', note='Posição e extensão segundo a planta de 1930; alguns têm gravuras rupestres (n.º 2 a 4) e uma gruta (n.º 5). O relevo dos penedos vem do modelo do terreno LiDAR; a forma das pedras à superfície é aproximada.', src=['cardozo1930', 'era2021', 'lidar'])

# ---------- trees from the LiDAR canopy height model (MDS − MDT, 25 cm): local maxima above 3 m, real heights
from scipy.ndimage import maximum_filter as _mf
rS, cS = _rc(np.array([-R, R]), np.array([R, -R])); r0_, r1_ = int(rS.min()), int(rS.max()) + 1; c0_, c1_ = int(cS.min()), int(cS.max()) + 1
CH = gaussian_filter(CHM[r0_:r1_, c0_:c1_], 2.4)
pk = (CH == _mf(CH, 13)) & (CH > 3)
ys, xs = np.nonzero(pk); tp = []; TH = {}
for yy_, xx_ in zip(ys, xs):
    lx = LB['x0'] + (c0_ + xx_ + .5) * LB['cs'] - X0L; lz = Y0L - (LB['y1'] - (r0_ + yy_ + .5) * LB['cs'])
    x, y = lx - CX, -(lz - CZ)
    if math.hypot(x, y) < R - 2.5: tp.append((x, y)); TH[(x, y)] = float(CHM[r0_ + yy_ - 2:r0_ + yy_ + 3, c0_ + xx_ - 2:c0_ + xx_ + 3].max())
# canopy cover (for undergrowth and ground colour), 512² over the disc
_cg = np.linspace(-R, R, 512)
can = gaussian_filter((_samp(CHM, *np.meshgrid(_cg, -_cg)) > 2.5).astype(float), 1.2)
wallpts = np.vstack([dense(loc(L)) for L in [P.W_WEST, P.W_LOWER, P.W_EAST_OUTER, P.W_EAST_INNER]] + [np.array([[h[0], h[1]] for h in hpos])])
from scipy.spatial import cKDTree
kd = cKDTree(wallpts)
from matplotlib.path import Path as MPath
_encl = MPath(loc(P.W_WEST + P.W_LOWER + P.W_EAST_OUTER[::-1] + P.W_EAST_INNER[::-1]))
_upper = MPath(loc(P.W_WEST + P.W_EAST_INNER[::-1]))
ntp0 = len(tp)
tp = [p for p in tp if (kd.query(p)[0] > 5 and not _encl.contains_point(p)) or (kd.query(p)[0] > 6 and rng.random() < (.1 if _upper.contains_point(p) else .15))]   # real trees, thinned inside the walls so the ruins stay readable
print('lidar trees', ntp0, 'kept', len(tp))
leaf = [col_mat('leaf1', (52, 86, 40)), col_mat('leaf2', (70, 104, 46)), col_mat('leaf3', (40, 70, 38))]
trunk = col_mat('trunk', (92, 66, 44))
def cone(cx, cy, z0, r, h, n=9):
    V = [(cx, cy, z0 + h)] + [(cx + math.cos(k / n * 2 * np.pi) * r, cy + math.sin(k / n * 2 * np.pi) * r, z0) for k in range(n)]
    F = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)] + [tuple(range(n, 0, -1))]
    return V, F, [(0, 0)] * len(V)
def blob(cx, cy, z0, r, h):
    tmp = bmesh.new(); bmesh.ops.create_icosphere(tmp, subdivisions=1, radius=1); V = []
    for v in tmp.verts: V.append((cx + v.co.x * r * (1 + rng.normal(0, .1)), cy + v.co.y * r * (1 + rng.normal(0, .1)), z0 + h / 2 + v.co.z * h / 2))
    F = [tuple(v.index for v in f.verts) for f in tmp.faces]; tmp.free(); return V, F, [(0, 0)] * len(V)
# unit prototypes (1 m tall) for the Minho hillside vegetation; three.js instances them
def blobs(specs):
    V = []; F = []
    for (cx, cy, cz, r, h) in specs:
        v, f, _ = blob(cx, cy, cz - h / 2, r, h); o = len(V); V += v; F += [tuple(i + o for i in q) for q in f]
    return V, F, [(0, 0)] * len(V)
def blades(n=6):
    V = []; F = []
    for k in range(n):
        a = k / n * 2 * np.pi + rng.random() * .5; lean = .18 + rng.random() * .2; w = .045
        bx, by = math.cos(a + 1.57) * w, math.sin(a + 1.57) * w; tx, ty = math.cos(a) * lean, math.sin(a) * lean
        o = len(V); V += [(-bx, -by, 0), (bx, by, 0), (tx, ty, .75 + rng.random() * .25)]; F.append((o, o + 1, o + 2))
    return V, F, [(0, 0)] * len(V)
def tblobs(specs, sub=2):
    V = []; F = []
    for (cx, cy, cz, r, h) in specs:
        tmp = bmesh.new(); bmesh.ops.create_icosphere(tmp, subdivisions=sub, radius=1); o = len(V)
        for v in tmp.verts:
            k = 1 + rng.normal(0, .09); V.append((cx + v.co.x * r * k, cy + v.co.y * r * k, cz + v.co.z * h / 2 * (1 + rng.normal(0, .06))))
        F += [tuple(o + v.index for v in f.verts) for f in tmp.faces]; tmp.free()
    return V, F, [(0, 0)] * len(V)
def limbs(specs):   # trunk and branches as thin tapered cones from (x0,y0,z0) to (x1,y1,z1)
    V = []; F = []
    for (x0, y0, z0, x1, y1, z1, r0) in specs:
        a = np.array([x0, y0, z0]); b_ = np.array([x1, y1, z1]); ax = b_ - a; L = np.linalg.norm(ax); ax /= L
        u = np.cross(ax, [0, 0, 1] if abs(ax[2]) < .9 else [1, 0, 0]); u /= np.linalg.norm(u); w_ = np.cross(ax, u); o = len(V)
        for k in range(7):
            t = k / 7 * 2 * np.pi; V.append(tuple(a + (u * math.cos(t) + w_ * math.sin(t)) * r0)); V.append(tuple(b_ + (u * math.cos(t) + w_ * math.sin(t)) * r0 * .45))
        for k in range(7): k2 = (k + 1) % 7; F.append((o + 2 * k, o + 2 * k2, o + 2 * k2 + 1, o + 2 * k + 1))
    return V, F, [(0, 0)] * len(V)
def crown(n, rmin, rmax, zlo, zhi, spread, seed):
    g = np.random.default_rng(seed); out = []
    for k in range(n):
        a = k / n * 2 * np.pi + g.random() * .7; d = spread * (.35 + .65 * g.random()); z = zlo + (zhi - zlo) * g.random()
        out.append((math.cos(a) * d, math.sin(a) * d, z, rmin + (rmax - rmin) * g.random(), (rmin + (rmax - rmin) * g.random()) * 1.5))
    return out + [(0, 0, zhi, rmax * 1.1, rmax * 1.3)]
# carvalho (Quercus robur/pyrenaica): open, lobed, irregular crown on a forked trunk
OAK_L = limbs([(0, 0, -.03, .02, 0, .42, .045), (.02, 0, .38, .2, .08, .66, .022), (.02, 0, .38, -.17, -.05, .7, .022), (.02, 0, .4, .0, -.16, .74, .018)])
OAK_C = tblobs(crown(9, .13, .21, .52, .86, .27, 1) + [(.24, .1, .64, .16, .24), (-.22, -.06, .7, .16, .24)])
# sobreiro (Quercus suber): short thick trunk stripped to rusty-red at the base, broad dark umbrella crown
COR_T = limbs([(0, 0, -.03, .03, 0, .2, .06)]); COR_L = limbs([(.03, 0, .18, .05, 0, .36, .05), (.05, 0, .33, .28, .06, .55, .026), (.05, 0, .33, -.26, -.04, .55, .026), (.05, 0, .33, .0, .24, .56, .022)])
COR_C = tblobs(crown(10, .14, .22, .55, .72, .34, 2))
def vase(n, seed, z0=.62):   # eucalyptus: few loose clumps in the upper third, spreading outwards with height, gaps between them
    g = np.random.default_rng(seed); out = []
    for k in range(n):
        u = (k + g.random()) / n; a = k * 2.4 + g.random() * .6; d = .05 + .17 * u; r = .07 + .04 * g.random()
        out.append((math.cos(a) * d, math.sin(a) * d, z0 + (.97 - z0) * u, r, r * .9))
    return out
PROTO = {
 'oak': [('trunk', OAK_L), ('leaf', OAK_C)],
 'cork': [('bark', COR_T), ('trunk', COR_L), ('leaf', COR_C)],
 # the hill today (Tiago): mostly eucalyptus, then chestnut, oak and cork oak. Variants so the forest is not made of clones.
 # eucalipto: tall, slender pale trunk forked high, open narrow crown of small drooping clumps
 'euc': [('pale', limbs([(0, 0, -.03, .01, 0, .62, .009), (.01, 0, .5, .08, .03, .84, .005), (.01, 0, .55, -.07, -.02, .86, .005)])), ('leaf', tblobs(vase(9, 6), 1))],
 'euc2': [('pale', limbs([(0, 0, -.03, -.01, .01, .72, .008), (-.01, .01, .62, .06, -.03, .9, .0045)])), ('leaf', tblobs(vase(7, 7, z0=.7), 1))],
 # castanheiro: thick short trunk, broad dense rounded crown
 'chest': [('trunk', limbs([(0, 0, -.03, .02, 0, .32, .06), (.02, 0, .28, .24, .06, .55, .03), (.02, 0, .28, -.22, -.05, .56, .03), (.02, 0, .3, 0, .22, .58, .026)])), ('leaf', tblobs(crown(12, .16, .24, .44, .8, .32, 8)))],
 'chest2': [('trunk', limbs([(0, 0, -.03, 0, 0, .38, .055), (0, 0, .34, .18, .1, .6, .026), (0, 0, .34, -.16, -.1, .62, .026)])), ('leaf', tblobs(crown(10, .15, .22, .5, .84, .26, 9)))],
 'oak2': [('trunk', limbs([(0, 0, -.03, .03, 0, .34, .05), (.03, 0, .3, .26, .1, .56, .024), (.03, 0, .3, -.24, -.08, .58, .024), (.03, 0, .32, .04, .22, .6, .02)])), ('leaf', tblobs(crown(10, .15, .23, .44, .74, .36, 3)))],
 'oak3': [('trunk', limbs([(0, 0, -.03, .01, 0, .55, .04), (.01, 0, .45, .12, .05, .8, .018), (.01, 0, .45, -.1, -.04, .82, .018)])), ('leaf', tblobs(crown(8, .1, .16, .52, .92, .18, 4)))],
 'cork2': [('bark', COR_T), ('trunk', COR_L), ('leaf', tblobs(crown(8, .15, .24, .5, .66, .3, 5) + [(.2, -.12, .58, .17, .2)]))],
 'shrub': [('leaf', blobs([(0, 0, .3, .42, .55), (.28, .1, .25, .3, .42), (-.25, -.12, .24, .28, .4)]))],
 'tuft': [('leaf', blades(7))],
}
_oak = [(96, 128, 54), (112, 140, 60), (84, 116, 48), (122, 138, 58), (78, 108, 50), (104, 122, 52)]
_cork = [(70, 88, 52), (80, 96, 56), (62, 80, 48), (88, 100, 58), (66, 84, 54)]
_euc = [(124, 140, 100), (136, 148, 108), (116, 132, 96), (144, 152, 112), (120, 138, 106), (130, 142, 92)]
_chest = [(92, 130, 50), (104, 140, 56), (84, 120, 46), (112, 146, 62), (98, 128, 52)]
PAL = {'oak': _oak, 'oak2': _oak, 'oak3': _oak, 'cork': _cork, 'cork2': _cork, 'euc': _euc, 'euc2': _euc, 'chest': _chest, 'chest2': _chest,
       'shrub': [(128, 138, 62), (112, 128, 56), (196, 170, 60)], 'tuft': [(120, 132, 62), (138, 144, 70), (104, 120, 56)]}
bark_m = col_mat('corkbark', (160, 78, 44), .9); pale_m = col_mat('eucbark', (196, 186, 166), .8); trunk = col_mat('trunk', (88, 74, 60), .9)
for nm, parts in PROTO.items():
    for part, geo in parts:
        A = Acc(); A.add(geo); o = A.obj(f'PROTO-{nm}-{part}-{len(bpy.data.objects)}', {'trunk': trunk, 'bark': bark_m, 'pale': pale_m}.get(part, leaf[1])); o.location = (0, 0, 0)
        _b = bmesh.new(); _b.from_mesh(o.data); bmesh.ops.recalc_face_normals(_b, faces=_b.faces); _b.to_mesh(o.data); _b.free()   # limbs() winds its tubes inwards
TYPES = list(PROTO)
TREES = []
# crown width from the canopy model: mean radius (8 directions) where the canopy stays above half the tree height
_ang = np.linspace(0, 2 * np.pi, 8, endpoint=False); _rad = np.arange(.5, 8.01, .5)
def crown_r(x, y, h):
    px = x + np.cos(_ang)[:, None] * _rad[None]; py = y + np.sin(_ang)[:, None] * _rad[None]
    c = _samp(CHM, px.ravel(), py.ravel()).reshape(px.shape) > h * .5
    return float(np.mean([_rad[np.argmin(r)] if not r.all() else _rad[-1] for r in c]))
CR = {p: 2 * crown_r(*p, TH[p]) / max(TH[p], 3) for p in tp}; cr0 = float(np.median(list(CR.values()))) if CR else 1
for (x, y) in tp:
    g = float(hz(x, y)); h_ = TH[(x, y)]; rr = rng.random(); wf = float(np.clip(CR[(x, y)] / cr0, .7, 1.4))
    # species are not in the LiDAR: tall narrow crowns are taken as eucalyptus (the commonest tree here), broad ones as chestnut
    pe = (.8 if wf < 1.15 else .45) if h_ >= 12 else (.5 if h_ >= 8 else .15)
    if rr < pe: sp = 'euc'
    else:
        w3 = [.45, .35, .2] if wf > 1.15 else ([.25, .35, .4] if h_ < 9 else [.3, .5, .2])
        sp = str(rng.choice(['chest', 'oak', 'cork'], p=w3))
    if sp == 'euc': kind = 'euc2' if wf < .85 or rng.random() < .3 else 'euc'
    elif sp == 'chest': kind = str(rng.choice(['chest', 'chest2']))
    elif sp == 'cork': kind = str(rng.choice(['cork', 'cork2']))
    else: kind = 'oak2' if wf > 1.15 else ('oak3' if wf < .85 else str(rng.choice(['oak', 'oak2', 'oak3'], p=[.5, .25, .25])))
    TREES.append([round(x, 2), round(y, 2), round(g, 2), round(min(22, h_ * EX), 1), TYPES.index(kind), int(rng.integers(0, len(PAL[kind]))), round(rng.random() * 6.28, 2), round(wf * (.92 + .16 * rng.random()), 2)])
# undergrowth: gorse/broom at the forest edges and on the slopes, grass tufts everywhere but the path and the structures
canm = lambda x, y: can[min(511, max(0, int((R - y) / (2 * R) * 512))), min(511, max(0, int((x + R) / (2 * R) * 512)))]
pathpts = dense(loc(P.PATH), 1.5); kp = cKDTree(pathpts)
def free(x, y, dw, dp=2.5): return math.hypot(x, y) < R - 2 and kd.query((x, y))[0] > dw and kp.query((x, y))[0] > dp
n_sh = 0
for _ in range(9000):
    x, y = (rng.random(2) * 2 - 1) * R; c = canm(x, y)
    if n_sh > 320 or not free(x, y, 6) or _encl.contains_point((x, y)): continue
    if rng.random() < (.9 if .12 < c < .6 else .08):
        TREES.append([round(x, 2), round(y, 2), round(float(hz(x, y)), 2), round(1.6 + rng.random() * 1.8, 2), TYPES.index('shrub'), int(rng.integers(0, 3)), round(rng.random() * 6.28, 2)]); n_sh += 1
n_tu = 0
for _ in range(20000):
    x, y = (rng.random(2) * 2 - 1) * R
    if n_tu > 2600 or not free(x, y, 1.6, 1.8): continue
    ins = _encl.contains_point((x, y))
    if rng.random() < (.22 if ins else .8):
        TREES.append([round(x, 2), round(y, 2), round(float(hz(x, y)), 2), round(.35 + rng.random() * .35, 2), TYPES.index('tuft'), int(rng.integers(0, 3)), round(rng.random() * 6.28, 2)]); n_tu += 1
print('trees', len(tp), 'shrubs', n_sh, 'tufts', n_tu, 'R', R)

# ---------- labels from the plan legend (empties named lbl:...)
for t, x, y in P.LABELS:
    c = loc([x, y]); e = bpy.data.objects.new(f'LBL-{t}-{len(bpy.data.objects)}', None); e.location = (c[0], c[1], float(hz(c[0], c[1])) + 3)
    bpy.context.scene.collection.objects.link(e)
for t, pts, k in [('Muralha', P.W_EAST_INNER, 3), ('Casas redondas', None, 0)]:
    if pts is None:
        c = np.mean([[h[0], h[1]] for h in hpos[:22]], 0)
    else:
        c = loc(pts[k])
    e = bpy.data.objects.new(f'LBL-{t}-{len(bpy.data.objects)}', None); e.location = (c[0], c[1], float(hz(c[0], c[1])) + 4); bpy.context.scene.collection.objects.link(e)

# ---------- stylised ground (the orthophoto only guides land cover): grass, dry grass in the enclosure, trodden earth, path
TS = 3072; mpp = 2 * R / TS
jj, ii = np.mgrid[0:TS, 0:TS]; GX = (ii + .5) * mpp - R; GY = R - (jj + .5) * mpp
def noise(sig, seed):
    return gaussian_filter(np.random.default_rng(seed).normal(0, 1, (TS, TS)), sig, mode='wrap')
n1 = noise(40, 1); n1 /= n1.std(); n2 = noise(10, 2); n2 /= n2.std(); n3 = noise(2, 3); n3 /= n3.std()
from PIL import ImageDraw
def m2px(p): return [((x + R) / mpp, (R - y) / mpp) for x, y in p]
def mask_draw(fn):
    im = Image.new('L', (TS, TS), 0); fn(ImageDraw.Draw(im)); return np.asarray(im, float) / 255
encl = loc(P.W_WEST + P.W_LOWER + P.W_EAST_OUTER[::-1] + P.W_EAST_INNER[::-1])
inside = gaussian_filter(mask_draw(lambda d: d.polygon(m2px(encl), fill=255)), 6)
def near(d):
    for L in [P.W_WEST, P.W_LOWER, P.W_EAST_OUTER, P.W_EAST_INNER, P.W_SE] + P.W_INNER: d.line(m2px(loc(L)), fill=255, width=int(6 / mpp))
    for (x, y, rad) in hpos:
        X, Y = (x + R) / mpp, (R - y) / mpp; q = (rad + 1.6) / mpp; d.ellipse([X - q, Y - q, X + q, Y + q], fill=255)
    for (x, y, r) in P.ROCKS:
        c = loc([x, y]); X, Y = (c[0] + R) / mpp, (R - c[1]) / mpp; q = r * K * kk / mpp * 1.1; d.ellipse([X - q, Y - q, X + q, Y + q], fill=200)
dirt = gaussian_filter(mask_draw(near), 5)
path = gaussian_filter(mask_draw(lambda d: d.line(m2px(dense(loc(P.PATH), 2)), fill=255, width=int(3.2 / mpp), joint='curve')), 2.2)
forest = gaussian_filter(np.asarray(Image.fromarray((can * 255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR), float) / 255, 8)
# slope from the height function
zz = hz(GX[::8, ::8], GY[::8, ::8]); gy_, gx_ = np.gradient(zz, mpp * 8); slope = np.hypot(gx_, gy_)
slope = np.asarray(Image.fromarray(slope.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
def lerp(a, b, t): t = np.clip(t, 0, 1)[..., None]; return a * (1 - t) + b * t
C = lambda *c: np.array(c, float)
col = lerp(C(96, 118, 52), C(132, 146, 68), .5 + .22 * n1 + .12 * n2)                 # meadow
col = lerp(col, C(150, 154, 84), np.clip(inside * (.75 + .06 * n2), 0, 1))           # dry, cleared enclosure
col = lerp(col, C(76, 96, 46), forest * .7 * (1 - inside))                                        # shaded forest floor
col = lerp(col, C(128, 104, 72), np.clip((slope - .55) * 1.4, 0, .7))               # earthy steep slopes
col = lerp(col, C(158, 140, 104), np.clip(dirt * 1.1, 0, .75))           # trodden earth by walls and houses
col = lerp(col, C(200, 176, 128), np.clip(path * (1.1 + .25 * n3), 0, 1))            # sandy path
hs_ = np.zeros_like(slope)
zz2 = hz(GX[::4, ::4], GY[::4, ::4]); gy2, gx2 = np.gradient(zz2, mpp * 4)
nx, ny, nz = -gx2, gy2, np.ones_like(gx2); nn = np.sqrt(nx * nx + ny * ny + 1); L_ = np.array([-.55, .45, .7]); L_ /= np.linalg.norm(L_)
shade = (nx * L_[0] + ny * L_[1] + nz * L_[2]) / nn; shade = np.asarray(Image.fromarray(shade.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
col *= np.clip(.78 + .3 * (shade - shade.mean()) / (shade.std() + 1e-6) * .35 + .22, .7, 1.15)[..., None]
clump = gaussian_filter(np.random.default_rng(5).normal(0, 1, (TS, TS)), 4); clump /= clump.std()
col = lerp(col, col * C(.84, .9, .8) / 1, np.clip(clump * .35, 0, .6) * (1 - path))      # darker grass clumps
spk = np.random.default_rng(6).random((TS, TS))
col = np.where(((spk > .9965) & (path < .3))[..., None], C(176, 170, 158), col)               # pebbles
col = np.where(((spk < .0012) & (inside < .3) & (forest < .3) & (path < .3))[..., None], C(232, 214, 96), col)   # wild flowers
col *= (1 + .07 * n3[..., None]) ; col += n3[..., None] * 4
rim = np.clip((np.hypot(GX, GY) - (R - 1.2)) / 1.2, 0, 1); col = lerp(col, C(84, 104, 46), rim)
Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save('blend/ground_raw.jpg', quality=92)
gtex.image = bpy.data.images.load(os.path.abspath('blend/ground_raw.jpg'))

# ---------- ambient occlusion baked into the ground texture (Cycles)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.device = 'CPU'
ao = bpy.data.images.new('ao', 1024, 1024, float_buffer=False)
an = gmat.node_tree.nodes.new('ShaderNodeTexImage'); an.image = ao; gmat.node_tree.nodes.active = an
for o in sc.objects: o.select_set(False)
for o in sc.objects:
    if o.name.startswith('B-'): o.hide_render = True
terrain.select_set(True); bpy.context.view_layer.objects.active = terrain
sc.world = sc.world or bpy.data.worlds.new('w')
sc.render.bake.margin = 4
bpy.ops.object.bake(type='AO')
aopx = np.array(ao.pixels[:]).reshape(1024, 1024, 4)[::-1, :, 0]   # blender images are bottom-up
aoi = Image.fromarray((np.clip(aopx, 0, 1) * 255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.5))
A = np.asarray(aoi, float)[..., None] / 255
G = np.asarray(Image.open('blend/ground_raw.jpg'), float) * (.68 + .32 * A)
Image.fromarray(np.clip(G, 0, 255).astype(np.uint8)).save(f'blend/ground.jpg', quality=88)
gmat.node_tree.nodes.remove(an); gtex.image = bpy.data.images.load(os.path.abspath('blend/ground.jpg'))
for o in sc.objects: o.hide_render = False

# ---------- export
os.makedirs('app/dio', exist_ok=True)
for o in sc.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.abspath(f'app/dio/{SID}.glb'), export_format='GLB', export_apply=True, export_yup=True,
                          export_image_format='JPEG', export_jpeg_quality=86, export_materials='EXPORT', use_selection=False, export_extras=True,
                          export_draco_mesh_compression_enable=False)
json.dump({'cat': CAT, 'sources': P.SOURCES, 'R': R, 'ex': EX, 'h0': H0, 'cx': CX, 'cz': CZ, 'trees': TREES, 'types': TYPES, 'pal': {k: [list(c) for c in v] for k, v in PAL.items()}}, open(f'app/dio/{SID}.json', 'w'))
print('ok', os.path.getsize(f'app/dio/{SID}.glb'))
