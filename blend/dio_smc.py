# Builds a castillos-style disc diorama of one castro in Blender (bpy) and exports a GLB for three.js.
# Castro de Santa Marta das Cortiças (Braga). Usage: /opt/bvenv/bin/python blend/dio_smc.py braga-castro-de-santa-marta-das-corticas
# No published plan could be read: the two lines of rampart are traced on the DGT LiDAR 2025 ground model (blend/smc_trace.py,
# snapped onto the scarps by lidar/smc_lines.py -> blend/smc_lines.json). Terrain and trees from the point clouds
# LO-177505/177506/178505/178506 (lidar/smc_laz.py -> lidar/smc_*25.npy). Chapel, monument, towers and roads from OpenStreetMap,
# the LiDAR (building class and heights) and Tiago's photographs. Basilica and palace: published dimensions (Barroca, Arezes
# and Morais), placed at the published coordinates (see GAPS: the two coordinates seem swapped).
# Local frame: x east, y north (Blender Z up), metres, origin = disc centre.
import sys, json, math, importlib, os
import numpy as np
import bpy, bmesh
from PIL import Image, ImageFilter, ImageEnhance
from scipy.ndimage import gaussian_filter, maximum_filter, label

SID = sys.argv[-1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, 'blend')
LN = json.load(open('blend/smc_lines.json'))
rng = np.random.default_rng(12)
# OpenStreetMap features (local metres from the site point, x east, y north), read from osm/braga.pbf in 2026-11
ROADS = [[(-2.2, 188.1), (-25.8, 156.0), (-40.6, 132.9), (-49.4, 111.5), (-50.8, 102.9), (-53.9, 84.4), (-56.3, 60.8), (-54.5, 39.0), (-48.1, 23.9),
          (-47.0, 22.2), (-27.7, -6.7), (-8.0, -26.5), (4.1, -30.0), (14.4, -27.5), (37.7, -14.2), (42.3, -2.5), (45.4, 10.0), (42.1, 26.8),
          (44.4, 43.5), (52.0, 64.5), (58.2, 74.7), (77.9, 68.4), (80.9, 66.1), (90.5, 56.7)],            # access road (unclassified), loop round the top
         [(-17.2, 33.3), (27.6, 42.9), (44.4, 43.5), (67.7, 49.4), (74.1, 51.4), (78.7, 52.9), (90.5, 56.7), (110.0, 35.1), (113.1, 27.9), (112.1, 21.9), (93.7, -10.4)],   # service road monument–chapel, pedestrian
         [(58.2, 74.7), (74.8, 92.3), (77.9, 95.5)], [(74.8, 92.3), (81.1, 86.0), (83.3, 81.6), (85.1, 76.1), (83.7, 71.4), (80.9, 66.1)],
         [(93.7, -10.4), (72.1, -29.8), (65.4, -36.5), (64.7, -41.2), (68.6, -43.9), (124.1, -42.1), (140.5, -49.4), (152.2, -57.2), (162.5, -56.1), (167.1, -51.9)],   # track
         [(37.7, -14.2), (53.5, -8.5), (64.6, -3.3), (71.6, -3.2), (81.6, -2.3), (88.8, -5.6), (93.7, -10.4)]]
CHAPEL_C, CHAPEL_A, CHAPEL_L, CHAPEL_W = (99.2, 59.9), math.radians(45), 14.6, 11.0   # LiDAR building class: 14.6 m along NE, 11 m wide
STATUE = (-29.3, 29.5)       # monument to Nossa Senhora da Assunção (OSM statue; LiDAR base 5.8 x 5.2 m, top 16.3 m above the rock)
MON_RING = [(-18.6, 26.5), (-19.7, 33.1), (-20.8, 39.6), (-22.8, 40.9), (-24.9, 41.6), (-27.6, 42.0), (-29.8, 41.6), (-32.6, 40.0), (-35.7, 37.4), (-37.9, 34.9),
            (-39.1, 32.0), (-39.4, 28.5), (-39.0, 25.1), (-37.8, 22.8), (-34.5, 20.0), (-31.2, 18.8), (-25.9, 18.7), (-21.4, 20.3), (-20.0, 21.7), (-18.9, 23.6), (-18.6, 26.5)]
ANNEX = [(107.0, 51.1), (112.8, 53.1), (119.2, 35.5), (113.4, 33.4)]   # OSM building=yes beside the chapel
VERTEX = (54.8, 9.7)         # geodetic vertex Santa Marta, 561.84 m (pillar 3.02 m)
TV = (-63.3, 140.4)          # TV tower "Braga" (lattice), LiDAR top 41.5 m
LOOKOUT = (57.1, 3.3)        # fire lookout Santa Marta, LiDAR 11.2 m (OSM: 10 m)
MAST = (34.7, 51.4)          # radio-amateur repeater mast, LiDAR 10.3 m
SWING = (-47.0, 22.2)        # panoramic swing, inaugurated 2023 (tese)
CROSS = (56.9, 35.1)         # wayside cross
PICNIC = [(96.7, 81.2), (96.3, 92.3), (93.6, 100.7), (86.1, 107.5), (78.9, 109.0), (73.0, 105.7), (68.0, 101.6), (59.5, 93.8), (50.2, 80.5), (56.8, 76.9), (72.7, 72.3), (84.4, 66.0)]
# Barroca, Arezes & Morais: Núcleo A (houses) 41.514465 N -8.395269 W, Núcleo B (basilica) 41.514226 N -8.395638 W (note 2), in local metres:
NUC_A_PUB, NUC_B_PUB = (10.2, 30.1), (-20.7, 3.7)
# the text puts the basilica on the crest, cut by the path chapel–monument, and Núcleo A west of the monument by the access road:
# that fits the two coordinates swapped, so the basilica is placed on the first one and the palace "a short distance south" of it
BASIL_C, BASIL_A = NUC_A_PUB, math.radians(0)            # oriented east-west (published)
PALACE_C, PALACE_A = (10.5, 6.0), math.radians(-6)       # south of the basilica, alignment "slightly divergent" (angle not published)

# ---------- disc: holds the two lines, the chapel, the monument and the TV tower
CX, CY, R = 45.0, 58.0, 158.0
def loc(p): p = np.asarray(p, float); return np.stack([p[..., 0] - CX, p[..., 1] - CY], -1)

# ---------- terrain heights: DGT LiDAR 2025 ground points (class 2), TIN on a 25 cm grid, lightly smoothed
from scipy.ndimage import map_coordinates
X0L, Y0L = -21894.7, 205017.0                     # site point in PT-TM06
LB = json.load(open('lidar/smc_box.json'))
_dtm = np.load('lidar/smc_dtm25.npy').astype(np.float32); _dtm = np.where(np.isnan(_dtm), np.nanmean(_dtm), _dtm)
DTM = gaussian_filter(_dtm, 1.)
CHM = np.load('lidar/smc_dsm25.npy').astype(np.float32) - _dtm
def _rc(x, y):  # Blender xy -> grid row/col
    lx = np.asarray(x, float) + CX; ly = np.asarray(y, float) + CY
    return (LB['y1'] - (Y0L + ly)) / LB['cs'] - .5, (X0L + lx - LB['x0']) / LB['cs'] - .5
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

def uv_of(x, y): return np.stack([(x + R) / (2 * R), (y + R) / (2 * R)], -1)
Image.new('RGB', (64, 64), (120, 130, 70)).save('blend/ground_raw.jpg')
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
# ---------- structures: one object per structure, mode A (current state) and B (reconstitution)
CAT = []          # catalogue for the viewer: id, name, kind, phase, evidence, sources
def put(sid, name, mat, geo, mode, ev):
    A = Acc()
    for g in geo: A.add(g)
    o = A.obj(f'{mode}-{sid}', mat)
    if o: o['sid'] = sid; o['mode'] = mode; o['ev'] = ev
    return o
def item(**k): CAT.append(k)
# rubble: the stone of the buried ramparts, darkened and greened (moss, earth)
_st = np.asarray(Image.open('blend/stone.jpg').convert('RGB'), float)
Image.fromarray(np.clip(_st * [.6, .64, .52] + [4, 8, 0], 0, 255).astype(np.uint8)).save('blend/rubble.jpg', quality=88)
rub_m, _ = img_mat('rubble', 'blend/rubble.jpg', .95)
# The LiDAR ground model holds the banks (rampart = terrace edge with a 2-6 m scarp), so the wall is laid over the real slope:
# current state = rubble skin just above the crest; reconstitution = wall rising `above` metres over the crest.
from scipy.ndimage import gaussian_filter1d
def rampart(pts, w, above=.15, jitter=.2, sink=.8, taper=.85):
    p = dense(pts); n = len(p)
    d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9; nr = np.stack([-d[:, 1], d[:, 0]], 1)
    o = np.linspace(-w / 2 - 1.5, w / 2 + 1.5, 9)
    prof = hz(p[:, 0, None] + nr[:, 0, None] * o, p[:, 1, None] + nr[:, 1, None] * o)
    crest = gaussian_filter1d(prof.max(1), 3, mode='nearest'); foot = gaussian_filter1d(prof.min(1), 3, mode='nearest')
    jit = gaussian_filter1d(rng.normal(0, jitter, n), 2.5, mode='nearest')
    top = crest + above + jit
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]); V = []; UV = []
    for i in range(n):
        for j, (oo, up) in enumerate([(-w / 2, 0), (-w / 2 * taper, 1), (w / 2 * taper, 1), (w / 2, 0)]):
            q = p[i] + nr[i] * oo; z = top[i] if up else float(hz(q[0], q[1])) - sink
            V.append((q[0], q[1], z)); UV.append((s[i] / 2.2, (z - foot[i]) / 2.2 + j * .37))
    F = [(i * 4 + j, i * 4 + j + 4, i * 4 + j + 5, i * 4 + j + 1) for i in range(n - 1) for j in range(3)]
    F += [(0, 1, 2, 3), ((n - 1) * 4 + 3, (n - 1) * 4 + 2, (n - 1) * 4 + 1, (n - 1) * 4)]
    return V, F, UV
def line(k):
    v = LN[k]; p = np.array(v['pts']); return loc(np.vstack([p, p[:1]]) if v['closed'] else p)
WALLS = [  # id, name, width, height of the reconstituted wall above the crest, evidence of the reconstitution, note
 ('M1', 'Primeira muralha, à volta da plataforma do cume', 4.0, 1.8, 'hip',
  'Rebordo da plataforma do cume, com um talude de cerca de {d:.1f} m no modelo do terreno LiDAR. A poente e a sul a estrada de acesso dá a volta ao alto por cima desta linha e cortou-a; a nascente coincide com os afloramentos sobre a encosta. Fecha a plataforma onde estão a capela, o monumento, a basílica e o edifício palatino.'),
 ('M2', 'Segunda muralha, a norte e a nascente', 3.5, 1.5, 'hip',
  'Segundo talude, 40 a 75 m para fora da primeira linha, visível a norte e a nascente (cerca de {d:.1f} m de desnível). A poente e a sul perde-se entre os penedos de granito e os caminhos e não foi desenhada. Belino escavou em 1899 «pelo lado sul, entre a primeira e a segunda muralhas».'),
]
def bank_drop(pts, half=4.0):   # median height drop (m, not exaggerated) across the wall line in the LiDAR ground model
    p = dense(pts, 2); d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9; nr = np.stack([-d[:, 1], d[:, 0]], 1)
    o = np.linspace(-half, half, 9); pr = hraw(p[:, 0, None] + nr[:, 0, None] * o, p[:, 1, None] + nr[:, 1, None] * o)
    return float(np.median(pr.max(1) - pr.min(1)))
WALL_DROP = {}
for sid, name, w, ab, evb, note in WALLS:
    L = line(sid)
    put(sid, name, rub_m, [rampart(L, w)], 'A', 'conf')
    put(sid, name, stone_m, [rampart(L, w, ab, .12, taper=.92)], 'B', evb)
    dr = bank_drop(L); WALL_DROP[sid] = dr
    extra = f' · recinto com {LN[sid]["area_ha"]:.2f} ha' if LN[sid]['closed'] else ''
    item(id=sid, name=name, kind='Muralha', phase='Idade do Ferro', ev='conf', evB=evb,
         dims=f'comprimento ≈ {LN[sid]["len"]:.0f} m{extra} · desnível atual na linha ≈ {dr:.1f} m (LiDAR) · reconstituição: {ab:g} m acima do terraço',
         note=note.format(d=dr) + ' Traçado no modelo do terreno do LiDAR da DGT (2025), sem planta publicada que se pudesse consultar; a pedra está soterrada e coberta de mato, por isso no estado atual a linha aparece como um cordão de pedra sobre o talude. A altura original não está publicada: valor hipotético.',
         src=['lidar', 'barroca', 'wiki'])
print('bank drop', {k: round(v, 1) for k, v in WALL_DROP.items()})

# ---------- buildings: helpers
lime_m = col_mat('lime', (236, 232, 222), .85); tile_m = col_mat('tile', (172, 84, 52), .8); gran_m = col_mat('granite', (168, 162, 150), .9)
white_m = col_mat('marble', (246, 244, 238), .6); dark_m = col_mat('dark', (40, 36, 34), .9); steel_m = col_mat('steel', (150, 154, 158), .5)
wood_m = col_mat('wood', (118, 84, 54), .9); ruin_m = col_mat('ruin', (150, 142, 124), .95)
def T2(cx, cy, a):
    ca, sa = math.cos(a), math.sin(a); return lambda u, v: (cx + u * ca - v * sa, cy + u * sa + v * ca)
def boxv(cx, cy, a, lx, ly, z0, z1):
    t = T2(cx, cy, a); Q = [t(-lx / 2, -ly / 2), t(lx / 2, -ly / 2), t(lx / 2, ly / 2), t(-lx / 2, ly / 2)]
    V = [(x, y, z0) for x, y in Q] + [(x, y, z1) for x, y in Q]
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return V, F, [(0, 0)] * 8
def prism(cx, cy, r, z0, z1, n=8, rot=math.pi / 8, r1=None):   # n-sided prism (octagonal tiers), optional taper to r1
    r1 = r if r1 is None else r1
    V = [(cx + math.cos(rot + k / n * 2 * np.pi) * r, cy + math.sin(rot + k / n * 2 * np.pi) * r, z0) for k in range(n)]
    V += [(cx + math.cos(rot + k / n * 2 * np.pi) * r1, cy + math.sin(rot + k / n * 2 * np.pi) * r1, z1) for k in range(n)]
    F = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    return V, F, [(0, 0)] * len(V)
def gable(cx, cy, a, lx, ly, z0, h, ov=.35):   # ridge along local u
    t = T2(cx, cy, a); hx, hy = lx / 2 + ov, ly / 2 + ov
    V = [(*t(-hx, -hy), z0), (*t(hx, -hy), z0), (*t(hx, hy), z0), (*t(-hx, hy), z0), (*t(-hx, 0), z0 + h), (*t(hx, 0), z0 + h)]
    F = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5)]
    return V, F, [(0, 0)] * 6
def gable_wall(cx, cy, a, lx, ly, z0, h):   # triangular end walls under a gable
    t = T2(cx, cy, a); V = []; F = []
    for s_ in (-1, 1):
        o = len(V); V += [(*t(s_ * lx / 2, -ly / 2), z0), (*t(s_ * lx / 2, ly / 2), z0), (*t(s_ * lx / 2, 0), z0 + h)]; F.append((o, o + 1, o + 2) if s_ > 0 else (o + 2, o + 1, o))
    return V, F, [(0, 0)] * len(V)
def shed(cx, cy, a, lx, ly, z0, hlo, hhi, ov=.3):   # lean-to roof, high side at v = -ly/2
    t = T2(cx, cy, a); hx = lx / 2 + ov
    V = [(*t(-hx, -ly / 2), z0 + hhi), (*t(hx, -ly / 2), z0 + hhi), (*t(hx, ly / 2 + ov), z0 + hlo), (*t(-hx, ly / 2 + ov), z0 + hlo)]
    return V, [(0, 3, 2, 1), (0, 1, 2, 3)], [(0, 0)] * 4
def plan_walls(cx, cy, a, segs, th, z0, z1):   # list of wall segments in local (u, v) metres
    t = T2(cx, cy, a); A_ = Acc()
    for (u0, v0, u1, v1) in segs:
        L_ = math.hypot(u1 - u0, v1 - v0); ang_ = math.atan2(v1 - v0, u1 - u0); mc = t((u0 + u1) / 2, (v0 + v1) / 2)
        A_.add(boxv(mc[0], mc[1], a + ang_, L_ + th, th, z0, z1))
    return A_.V, A_.F, A_.UV
def arc_walls(cx, cy, a, uc, vc, r, a0, a1, th, z0, z1, n=10):
    pts = [(uc + r * math.cos(a0 + (a1 - a0) * k / n), vc + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
    return plan_walls(cx, cy, a, [(*pts[k], *pts[k + 1]) for k in range(n)], th, z0, z1)

# ---------- chapel of Santa Marta das Cortiças (D. Diogo de Sousa, 1520): footprint and heights from the LiDAR, form from Tiago's photograph
# nave on the north-west side (ridge 6.3 m above the yard in the LiDAR), lower lean-to annex on the south-east side (3.5–4.5 m),
# gabled façade with granite corner pilasters, door and a barred window, facing south-west to the summit; cross on the apex
cc = np.array(loc(CHAPEL_C)); g0 = float(hz(*cc)) - .25; ca_ = CHAPEL_A
NW_ = 6.6; AW_ = CHAPEL_W - NW_; nave_c = np.array(T2(*cc, ca_)(0, CHAPEL_W / 2 - NW_ / 2)); ann_c = np.array(T2(*cc, ca_)(0, -CHAPEL_W / 2 + AW_ / 2))   # local +v = north-west
EH = 4.3; RH = 2.0                       # nave eaves and roof rise (ridge ≈ 6.3 m)
geo_lime = [boxv(*nave_c, ca_, CHAPEL_L, NW_, g0, g0 + .25 + EH), gable_wall(*nave_c, ca_, CHAPEL_L, NW_, g0 + .25 + EH, RH),
            boxv(*ann_c, ca_, CHAPEL_L - .6, AW_, g0, g0 + .25 + 3.0)]
fu = -CHAPEL_L / 2 - .05; tn = T2(*nave_c, ca_)          # façade at the south-west end (u = -L/2)
geo_gran = [boxv(*tn(fu + .1, s_ * (NW_ / 2 - .2)), ca_, .5, .5, g0, g0 + .25 + EH + .1) for s_ in (-1, 1)]   # corner pilasters
geo_gran += [boxv(*tn(fu, 0), ca_, .14, 1.6, g0 + .25, g0 + 2.7), boxv(*tn(fu, 0), ca_, .14, 1.0, g0 + 3.4, g0 + 4.4)]    # door and window frames
geo_gran += [boxv(*tn(-CHAPEL_L / 2 + .6, 0), ca_, .9, .14, g0 + .25 + EH + RH + .1, g0 + .25 + EH + RH + .25),           # cross
             boxv(*tn(-CHAPEL_L / 2 + .6, 0), ca_, .14, .14, g0 + .25 + EH + RH, g0 + .25 + EH + RH + 1.0),
             boxv(*tn(-CHAPEL_L / 2 + .6, 0), ca_, .14, .55, g0 + .25 + EH + RH + .55, g0 + .25 + EH + RH + .7)]
geo_dark = [boxv(*tn(fu - .04, 0), ca_, .06, 1.15, g0 + .3, g0 + 2.5), boxv(*tn(fu - .04, 0), ca_, .06, .7, g0 + 3.55, g0 + 4.25),
            boxv(*T2(*ann_c, ca_)(-CHAPEL_L / 2 + .25, 0), ca_, .06, 1.1, g0 + 1.3, g0 + 2.2)]
put('CH', 'Capela de Santa Marta das Cortiças', lime_m, geo_lime, 'AB', 'conf')
put('CH', 'Cantaria da capela', gran_m, geo_gran, 'AB', 'conf')
put('CH', 'Vãos da capela', dark_m, geo_dark, 'AB', 'conf')
put('CH', 'Telhados da capela', tile_m, [gable(*nave_c, ca_, CHAPEL_L, NW_, g0 + .25 + EH, RH), shed(*ann_c, ca_ + math.pi, CHAPEL_L - .6, AW_, g0 + .25, 2.9, 3.7)], 'AB', 'conf')
# yard parapet: low stone wall on the edge of the chapel terrace (photo), where the ground drops > 1.2 m within 26 m of the chapel
par = []
for az in np.radians(np.arange(-60, 151, 4)):       # from the north-west round by the north and east to the south-east
    d_ = np.array([math.sin(az), math.cos(az)]); rr_ = np.arange(6, 26, .5); q_ = cc[None] + d_[None] * rr_[:, None]
    zq = hraw(q_[:, 0], q_[:, 1]); k_ = np.nonzero(zq < hraw(*cc) - 1.2)[0]
    par.append(q_[max(0, k_[0] - 2)] if len(k_) else None)
segs_ = []; cur = []
for p_ in par:
    if p_ is None:
        if len(cur) > 2: segs_.append(np.array(cur))
        cur = []
    else: cur.append(p_)
if len(cur) > 2: segs_.append(np.array(cur))
from scipy.ndimage import gaussian_filter1d as _g1
put('CW', 'Muro do adro da capela', gran_m, [sweep(np.stack([_g1(s_[:, 0], 1, mode='nearest'), _g1(s_[:, 1], 1, mode='nearest')], 1), .6, .8, .03, .3) for s_ in segs_], 'AB', 'conf')
item(id='CH', name='Capela de Santa Marta das Cortiças', kind='Capela', phase='1520', ev='conf', evB='conf',
     dims=f'planta ≈ {CHAPEL_L:.1f} × {CHAPEL_W:.1f} m (LiDAR, classe edifício): nave ≈ {NW_:.1f} m de largura e anexo lateral ≈ {AW_:.1f} m; cumeeira ≈ 6,3 m (LiDAR)',
     note='Mandada construir pelo arcebispo D. Diogo de Sousa em 1520, sobre um culto mais antigo (o monte de Santa Marta aparece nos documentos desde 900). Nave com fachada empenada virada a sudoeste, cunhais e molduras de granito, porta e janela gradeada, cruz no vértice; anexo mais baixo com telhado de uma água do lado sudeste. Forma tirada da fotografia de 2023 e alturas do LiDAR; a escavação de 1953-54 não sondou a zona da capela, onde Barroca, Arezes e Morais admitem que estaria o castelo medieval.',
     src=['photo', 'lidar', 'osm', 'barroca', 'wiki'])
item(id='CW', name='Muro do adro da capela', kind='Muro moderno', phase='atual', ev='conf', evB='conf',
     dims='≈ 0,8 m de altura (fotografia)', note='Muro baixo de pedra que limita o adro da capela sobre a encosta, visível na fotografia de 2023. Traçado no rebordo do terraço do LiDAR (onde o terreno desce mais de 1,2 m), aproximado.', src=['photo', 'lidar'])
# support building beside the chapel (OSM footprint, LiDAR height ≈ 5.5 m): current state only
ap = np.array(loc(ANNEX)); ac = ap.mean(0); e_ = ap[2] - ap[1]; aa_ = math.atan2(e_[1], e_[0]); La = float(np.linalg.norm(e_)); Wa = float(np.linalg.norm(ap[1] - ap[0]))
ga = float(min(hz(*ap.T))) - .2
put('BD', 'Edifício de apoio', lime_m, [boxv(*ac, aa_, La, Wa, ga, ga + 3.6)], 'A', 'conf')
put('BD', 'Telhado do edifício de apoio', tile_m, [gable(*ac, aa_, La, Wa, ga + 3.6, 1.3)], 'A', 'conf')
item(id='BD', name='Edifício de apoio junto à capela', kind='Edifício moderno', phase='atual', ev='conf', evB='conf',
     dims=f'planta ≈ {La:.1f} × {Wa:.1f} m (OpenStreetMap)', note='Edifício moderno a sudeste da capela. Função e data não apuradas; forma simplificada. Só no estado atual.', src=['osm', 'lidar'])

# ---------- monument to Nossa Senhora da Assunção, on a granite outcrop west of the summit (photo; LiDAR: base 5.8 m, top 16.3 m)
mc = np.array(loc(STATUE)); gm = float(hraw(*mc) - H0) * EX - .3
TIERS = [  # (radius of the octagon/square, z0, z1, sides, material) — proportions from the photograph, total height from the LiDAR
 (3.05, 0, .8, 8, rub_m), (2.85, .8, 1.7, 8, gran_m), (2.95, 1.7, 2.0, 8, gran_m), (2.6, 2.0, 3.6, 8, gran_m), (2.3, 3.6, 4.3, 8, gran_m),
 (1.9, 4.3, 5.7, 8, gran_m), (2.05, 5.7, 6.1, 8, gran_m), (1.15, 6.1, 8.6, 4, gran_m), (1.3, 8.6, 9.0, 4, gran_m), (.8, 9.0, 12.4, 4, gran_m),
 (.95, 12.4, 12.8, 4, gran_m), (.55, 12.8, 13.7, 4, gran_m)]
mon_g = []; mon_r = []
for (r_, z0_, z1_, n_, m_) in TIERS:
    rr0 = r_ / math.cos(math.pi / n_)        # circumradius from the half-width
    rr1 = rr0 * (.86 if (z1_ - z0_) == .7 else 1)      # sloped step
    (mon_r if m_ is rub_m else mon_g).append(prism(*mc, rr0, gm + z0_, gm + z1_, n_, math.pi / n_, rr1))
put('MN', 'Monumento a Nossa Senhora da Assunção', gran_m, mon_g, 'AB', 'conf')
put('MN', 'Base do monumento', rub_m, mon_r, 'AB', 'conf')
# the white statue: Our Lady of the Assumption, robe widening to the feet, right arm raised, halo
z_ = gm + 13.7; st_ = [prism(*mc, .32, z_, z_ + .18, 10, 0),                                   # cloud plinth
                     prism(*mc, .52, z_ + .18, z_ + 1.35, 12, 0, .34), prism(*mc, .34, z_ + 1.35, z_ + 1.85, 12, 0, .26),   # robe and bust
                     prism(*mc, .17, z_ + 1.85, z_ + 2.05, 10, 0, .19), prism(*mc, .19, z_ + 2.05, z_ + 2.2, 10, 0, .12),    # head
                     prism(*(mc + [.32, 0]), .08, z_ + 1.65, z_ + 2.45, 6, 0, .06), prism(*(mc + [-.33, .05]), .08, z_ + 1.25, z_ + 1.75, 6, 0)]   # raised right arm, left arm
for k in range(12):
    a0 = k / 12 * 2 * np.pi; a1 = (k + 1) / 12 * 2 * np.pi
    st_.append(boxv(mc[0] + .27 * math.cos((a0 + a1) / 2), mc[1] + .27 * math.sin((a0 + a1) / 2), (a0 + a1) / 2 + math.pi / 2, .16, .035, z_ + 2.3, z_ + 2.34))
put('MN', 'Imagem de Nossa Senhora da Assunção', white_m, st_, 'AB', 'conf')
item(id='MN', name='Monumento a Nossa Senhora da Assunção', kind='Monumento', phase='moderno', ev='conf', evB='conf',
     dims='≈ 16 m de altura sobre o penedo (LiDAR: 16,3 m); base ≈ 5,8 × 5,2 m (LiDAR); imagem branca no topo',
     note='Coluna de granito em andares: base de alvenaria sobre o afloramento, plinto oitavado em degraus, pedestal e fuste quadrados com um brasão, e a imagem branca de Nossa Senhora da Assunção, de braço erguido e com resplendor. Fica num penedo com escadas e um caminho à volta. Proporções tiradas da fotografia e altura total do LiDAR; data de construção não apurada. Segundo a Wikipédia, junto à sua base apareceram alicerces de vários muros, «um labirinto», de função desconhecida.',
     src=['photo', 'lidar', 'osm', 'wiki', 'barroca'])

# ---------- the late-antique buildings: published dimensions, positions from the published coordinates (approximate, see gaps)
def ruin_geo(segs_fn, h):   # current state: low grassed rubble on the line of the walls; reconstitution: wall plan raised to h
    return segs_fn(h)
gb = float(hz(*loc(BASIL_C))) - .2
def basilica(h, th=.75):
    L_, W_ = 25.0, 16.0; NW = 7.2; ap_r = NW / 2 - .2; ue = L_ / 2
    segs = [(-ue, -W_ / 2, ue, -W_ / 2), (-ue, W_ / 2, ue, W_ / 2), (-ue, -W_ / 2, -ue, W_ / 2), (ue, -W_ / 2, ue, W_ / 2)]   # rectangle, straight east wall
    ua = ue - ap_r - .5
    segs += [(ua, -W_ / 2, ua, -NW / 2), (ua, NW / 2, ua, W_ / 2)]                                     # rooms beside the apse (diaconicon N, prothesis S)
    segs += [(ua, -NW / 2, ue, -NW / 2), (ua, NW / 2, ue, NW / 2)]
    A_ = Acc(); A_.add(plan_walls(*loc(BASIL_C), BASIL_A, segs, th, gb - .3, gb + h))
    A_.add(arc_walls(*loc(BASIL_C), BASIL_A, ua, 0, ap_r, -math.radians(115), math.radians(115), th * .8, gb - .3, gb + h))   # inscribed horseshoe apse
    return A_.V, A_.F, A_.UV
def basil_cols(h):
    A_ = Acc(); t = T2(*loc(BASIL_C), BASIL_A)
    for u_ in (-6.5, -1.5, 3.5):
        for v_ in (-3.6, 3.6):
            A_.add(prism(*t(u_, v_), .38, gb - .2, gb + h, 8 if h < 1 else 12, 0, .3 if h > 1 else None))
    return A_.V, A_.F, A_.UV
put('BA', 'Basílica paleocristã', ruin_m, [basilica(.35)], 'A', 'hip')
put('BA', 'Basílica paleocristã', stone_m, [basilica(1.4), basil_cols(1.4)], 'B', 'hip')
item(id='BA', name='Basílica paleocristã', kind='Igreja', phase='séc. V-VI', ev='hip', evB='hip',
     dims='25 × 16 m · três naves: central 7,2 m, laterais 3,5 m · abside inscrita a nascente · orientada nascente-poente (publicado)',
     note='Escavada em 1953-54 por Arlindo da Cunha e Russell Cortez: igreja de três naves, fachada ocidental reta, abside de ferradura inscrita (curva por dentro e reta por fora) e dois compartimentos ao lado dela (diaconicon a norte, prothesis a sul); seis bases de pilares ou colunas. Russell Cortez considerou-a a melhor igreja paleocristã do Norte de Portugal. A planta do relatório de 1954 não pôde ser consultada: as medidas são as publicadas, mas a posição dos pilares e a espessura dos muros são esquemáticas. A posição segue uma das coordenadas publicadas (ver lacunas). Hoje está tapada pelo mato; no estado atual aparece como um cordão baixo de pedra. Na reconstituição o muro sobe a 1,4 m só para se ler a planta (alçado não publicado).',
     src=['barroca', 'wiki'])
gp = float(hz(*loc(PALACE_C))) - .2
def palace(h, th=.8):
    L_, W_ = 34.2, 12.6; ue = L_ / 2; ve = W_ / 2; ux = ue - 7.0; vn = ve - 3.4
    segs = [(-ue, -ve, ue, -ve), (-ue, ve, ue, ve), (-ue, -ve, -ue, ve), (ue, -ve, ue, ve),
            (ux, -ve, ux, ve),                                  # rooms at the east end
            (-ue, vn, ux, vn), (-3, vn, -3, ve),                # two elongated rooms on the north side
            (ux, 0, ue, 0), (ux + 1.4, -ve, ux + 1.4, 0)]       # two rooms and a narrow passage at the east end
    return plan_walls(*loc(PALACE_C), PALACE_A, segs, th, gp - .3, gp + h)
def pal_pillars(h):
    A_ = Acc(); t = T2(*loc(PALACE_C), PALACE_A); ve = 12.6 / 2; vn = ve - 3.4; vm = (-ve + vn) / 2
    for k in range(7):
        u_ = -17.1 + (17.1 - 7.0 + 17.1) * (k + 1) / 8
        A_.add(boxv(*t(u_, vm), PALACE_A, .6, .6, gp - .2, gp + h))
    return A_.V, A_.F, A_.UV
put('PA', 'Edifício palatino', ruin_m, [palace(.35)], 'A', 'hip')
put('PA', 'Edifício palatino', stone_m, [palace(1.4), pal_pillars(1.4)], 'B', 'hip')
# the column Tiago saw in 2022 against a wall of the palace (one standing shaft)
_tc = T2(*loc(PALACE_C), PALACE_A)(-4.0, -12.6 / 2 + .9)
put('PC', 'Coluna junto a um muro do palácio', gran_m, [prism(*_tc, .25, gp - .2, gp + 2.2, 12, 0, .22)], 'A', 'hip')
item(id='PA', name='Edifício palatino («palácio suevo»)', kind='Palácio', phase='séc. VI', ev='hip', evB='hip',
     dims='34,2 × 12,6 m · grande sala de duas naves com sete pilares de secção quadrada (publicado)',
     note='Escavado por Rigaud de Sousa em 1966-70, a pouca distância a sul da basílica e com um alinhamento ligeiramente divergente (imposto pelo terreno e pelos penedos). Grande sala de duas naves separadas por sete pilares, dois compartimentos alongados a norte e, no topo leste, dois compartimentos e um corredor estreito. Capitéis jónicos e um coríntio de acantos lisos (séc. VI-VII). A planta faz lembrar o palácio visigótico de Recópolis; a destruição violenta, talvez em 585, na conquista visigoda, apoia a atribuição a um palácio suevo. A planta de 1970 não pôde ser consultada: a divisão interior é esquemática, segundo a descrição, e a posição e o ângulo são aproximados (ver lacunas).',
     src=['barroca', 'wiki', 'tese'])
item(id='PC', name='Coluna junto a um muro do palácio', kind='Ruína', phase='séc. VI', ev='hip', evB='hip',
     dims='posição e altura aproximadas', note='Na visita de 2022 o Tiago ainda viu, entre o mato, uma parede do palácio com uma coluna pegada a ela; em 2025 a vegetação tapava tudo. Posição aproximada.', src=['tese'])

# ---------- modern landmarks (current state only): TV tower, fire lookout, mast, geodetic vertex, swing, wayside cross
def lattice(cx, cy, z0, h, b0, b1, legs=4, rings=8):
    A_ = Acc(); P = lambda k, t: (cx + (b0 + (b1 - b0) * t) / 2 * math.cos(math.pi / 4 + k / legs * 2 * np.pi), cy + (b0 + (b1 - b0) * t) / 2 * math.sin(math.pi / 4 + k / legs * 2 * np.pi), z0 + h * t)
    def bar(a, b, r):
        a = np.array(a); b = np.array(b); m = (a + b) / 2; L_ = np.linalg.norm(b - a); ax = (b - a) / L_
        u = np.cross(ax, [0, 0, 1] if abs(ax[2]) < .9 else [1, 0, 0]); u /= np.linalg.norm(u); w_ = np.cross(ax, u)
        V = [tuple(p + (u * math.cos(t) + w_ * math.sin(t)) * r) for p in (a, b) for t in (0, 2.1, 4.2)]
        return V, [(0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)], [(0, 0)] * 6
    for k in range(legs):
        for i in range(rings):
            t0, t1 = i / rings, (i + 1) / rings
            A_.add(bar(P(k, t0), P(k, t1), .12)); A_.add(bar(P(k, t1), P((k + 1) % legs, t1), .05))
            A_.add(bar(P(k, t0), P((k + 1) % legs, t1), .04))
    return A_.V, A_.F, A_.UV
gt = float(hz(*loc(TV))) - .3
put('TV', 'Torre de telecomunicações', steel_m, [lattice(*loc(TV), gt, 41.5, 6.0, 1.4, 4, 12), prism(*loc(TV), .5, gt + 41.5, gt + 44, 6)], 'A', 'conf')
gl = float(hz(*loc(LOOKOUT))) - .3
put('LK', 'Posto de vigia', steel_m, [lattice(*loc(LOOKOUT), gl, 8.6, 3.2, 1.8, 4, 4), boxv(*loc(LOOKOUT), 0, 2.4, 2.4, gl + 8.6, gl + 10.6)], 'A', 'conf')
put('MS', 'Mastro do repetidor', steel_m, [prism(*loc(MAST), .18, float(hz(*loc(MAST))) - .3, float(hz(*loc(MAST))) + 10.3, 6, 0, .08)], 'A', 'conf')
put('VG', 'Vértice geodésico Santa Marta', white_m, [prism(*loc(VERTEX), .45, float(hz(*loc(VERTEX))) - .2, float(hz(*loc(VERTEX))) + 3.0, 12, 0, .3)], 'A', 'conf')
gs = float(hz(*loc(SWING))) - .2; ts = T2(*loc(SWING), math.radians(30))
put('SW', 'Baloiço panorâmico', wood_m, [plan_walls(*loc(SWING), math.radians(30), [(-1.6, 0, -1.6, 0)], .2, gs, gs + .1),
     boxv(*ts(-1.5, -.7), math.radians(30), .2, .2, gs, gs + 4.2), boxv(*ts(-1.5, .7), math.radians(30), .2, .2, gs, gs + 4.2),
     boxv(*ts(1.5, -.7), math.radians(30), .2, .2, gs, gs + 4.2), boxv(*ts(1.5, .7), math.radians(30), .2, .2, gs, gs + 4.2),
     boxv(*ts(0, 0), math.radians(30), 3.4, .22, gs + 4.1, gs + 4.35), boxv(*ts(0, 0), math.radians(30), 1.2, .5, gs + .6, gs + .7)], 'A', 'conf')
gx_ = float(hz(*loc(CROSS))) - .2
put('CR', 'Cruzeiro', gran_m, [boxv(*loc(CROSS), 0, .8, .8, gx_, gx_ + .5), boxv(*loc(CROSS), 0, .22, .22, gx_ + .5, gx_ + 3.2), boxv(*loc(CROSS), 0, 1.0, .2, gx_ + 2.4, gx_ + 2.62)], 'A', 'conf')
item(id='TV', name='Torre de telecomunicações «Braga»', kind='Equipamento moderno', phase='atual', ev='conf', evB='conf', dims='≈ 41 m (LiDAR)', note='Torre metálica treliçada de televisão e telemóvel, a noroeste do alto. Só no estado atual.', src=['osm', 'lidar'])
item(id='LK', name='Posto de vigia de incêndios', kind='Equipamento moderno', phase='atual', ev='conf', evB='conf', dims='≈ 11 m (LiDAR; OSM: 10 m)', note='Torre metálica com cabine, junto ao vértice geodésico. Só no estado atual.', src=['osm', 'lidar'])
item(id='MS', name='Mastro do repetidor de radioamador', kind='Equipamento moderno', phase='atual', ev='conf', evB='conf', dims='≈ 10 m (LiDAR)', note='Só no estado atual.', src=['osm', 'lidar'])
item(id='VG', name='Vértice geodésico Santa Marta', kind='Marco', phase='atual', ev='conf', evB='conf', dims='561,84 m de altitude; pilar de 3 m (DGT)', note='Ponto mais alto do monte, num grande penedo de granito.', src=['osm'])
item(id='SW', name='Baloiço panorâmico de Esporões', kind='Equipamento moderno', phase='2023', ev='conf', evB='conf', dims='forma e altura aproximadas',
     note='Inaugurado em 2023. Segundo a tese, foi a única obra feita do projeto de valorização prometido para o sítio (espaço museológico orçado em 130 mil euros). Só no estado atual.', src=['tese', 'osm'])
item(id='CR', name='Cruzeiro', kind='Cruzeiro', phase='—', ev='conf', evB='conf', dims='forma e altura aproximadas', note='Posição do OpenStreetMap. Só no estado atual.', src=['osm'])
cp = np.array([T2(*cc, ca_)(u_, v_) for u_, v_ in [(-CHAPEL_L / 2, -CHAPEL_W / 2), (CHAPEL_L / 2, -CHAPEL_W / 2), (CHAPEL_L / 2, CHAPEL_W / 2), (-CHAPEL_L / 2, CHAPEL_W / 2)]])
# ---------- trees from the LiDAR canopy height model (MDS − MDT, 25 cm): local maxima above 3 m, real heights
from scipy.ndimage import maximum_filter as _mf
rS, cS = _rc(np.array([-R, R]), np.array([R, -R])); r0_, r1_ = int(rS.min()), int(rS.max()) + 1; c0_, c1_ = int(cS.min()), int(cS.max()) + 1
CH = gaussian_filter(CHM[r0_:r1_, c0_:c1_], 2.4)
pk = (CH == _mf(CH, 13)) & (CH > 3)
ys, xs = np.nonzero(pk); tp = []; TH = {}
for yy_, xx_ in zip(ys, xs):
    lx = LB['x0'] + (c0_ + xx_ + .5) * LB['cs'] - X0L; ly = LB['y1'] - (r0_ + yy_ + .5) * LB['cs'] - Y0L
    x, y = lx - CX, ly - CY
    if math.hypot(x, y) < R - 2.5: tp.append((x, y)); TH[(x, y)] = float(CHM[r0_ + yy_ - 2:r0_ + yy_ + 3, c0_ + xx_ - 2:c0_ + xx_ + 3].max())
# canopy cover (for undergrowth and ground colour), 512² over the disc
_cg = np.linspace(-R, R, 512)
can = gaussian_filter((_samp(CHM, *np.meshgrid(_cg, -_cg)) > 2.5).astype(float), 1.2)
_bt = lambda c_, a_, L_, W_: [T2(*loc(c_), a_)(u_, v_) for u_, v_ in [(-L_ / 2, -W_ / 2), (L_ / 2, -W_ / 2), (L_ / 2, W_ / 2), (-L_ / 2, W_ / 2), (-L_ / 2, -W_ / 2)]]
STRUCT = [np.array(_bt(BASIL_C, BASIL_A, 25, 16)), np.array(_bt(PALACE_C, PALACE_A, 34.2, 12.6)), np.vstack([cp, cp[:1]]), np.vstack([ap, ap[:1]])]
wallpts = np.vstack([dense(line(k)) for k in ('M1', 'M2')] + [dense(q_, .8) for q_ in STRUCT] + [dense(np.array([mc + [math.cos(a_) * 4, math.sin(a_) * 4] for a_ in np.linspace(0, 6.3, 20)]), .8)])
from scipy.spatial import cKDTree
kd = cKDTree(wallpts)
from matplotlib.path import Path as MPath
_encl = MPath(line('M1'))
_upper = _encl
ntp0 = len(tp)
# real trees, thinned inside the first line (10 %) and within 14 m of the banks so the ruins stay readable; the trees of the chapel yard
# (two big oaks beside the chapel in the 2023 photograph) are kept
YARD = []
def _keep(p):
    dw = kd.query(p)[0]; dch = math.hypot(p[0] - cc[0], p[1] - cc[1])
    if 6 < dch < 16 and dw > 2.5: YARD.append(p); return True
    return (dw > 14 and not _encl.contains_point(p)) or (dw > 6 and rng.random() < .1)
tp = [p for p in tp if _keep(p)]
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
    if (x, y) in YARD: kind = 'oak2' if rng.random() < .6 else 'cork'      # the broad oaks of the chapel yard (photo)
    TREES.append([round(x, 2), round(y, 2), round(g, 2), round(min(22, h_ * EX), 1), TYPES.index(kind), int(rng.integers(0, len(PAL[kind]))), round(rng.random() * 6.28, 2), round(wf * (.92 + .16 * rng.random()), 2)])
# undergrowth: gorse/broom at the forest edges and on the slopes, grass tufts everywhere but the path and the structures
canm = lambda x, y: can[min(511, max(0, int((R - y) / (2 * R) * 512))), min(511, max(0, int((x + R) / (2 * R) * 512)))]
pathpts = np.vstack([dense(loc(r), 1.5) for r in ROADS]); kp = cKDTree(pathpts)
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

# ---------- labels (empties named LBL-...)
def lbl(t, p, dz=3):
    e = bpy.data.objects.new(f'LBL-{t}-{len(bpy.data.objects)}', None); e.location = (float(p[0]), float(p[1]), float(hz(p[0], p[1])) + dz)
    bpy.context.scene.collection.objects.link(e)
lbl('Capela de Santa Marta das Cortiças', cc, 9)
lbl('Monumento a N.ª Sr.ª da Assunção', mc, 19)
lbl('Basílica paleocristã (posição aproximada)', loc(BASIL_C), 4)
lbl('Edifício palatino (posição aproximada)', loc(PALACE_C), 4)
lbl('Vértice geodésico Santa Marta · 562 m', loc(VERTEX), 5)
lbl('Torre de telecomunicações', loc(TV), 46)
lbl('Baloiço panorâmico', loc(SWING), 6)
lbl('Parque de merendas', np.mean(loc(PICNIC), 0), 2)
for k, t, i in [('M1', 'Primeira muralha', .6), ('M2', 'Segunda muralha', .3)]:
    q = line(k); lbl(t, q[int(len(q) * i)], 4)

# ---------- stylised ground: grass, cleared enclosure, earthy banks, granite outcrops, paved road, chapel yard
TS = 3072; mpp = 2 * R / TS
jj, ii = np.mgrid[0:TS, 0:TS]; GX = (ii + .5) * mpp - R; GY = R - (jj + .5) * mpp
def noise(sig, seed):
    return gaussian_filter(np.random.default_rng(seed).normal(0, 1, (TS, TS)), sig, mode='wrap')
n1 = noise(40, 1); n1 /= n1.std(); n2 = noise(10, 2); n2 /= n2.std(); n3 = noise(2, 3); n3 /= n3.std()
from PIL import ImageDraw
def m2px(p): return [((x + R) / mpp, (R - y) / mpp) for x, y in p]
def mask_draw(fn):
    im = Image.new('L', (TS, TS), 0); fn(ImageDraw.Draw(im)); return np.asarray(im, float) / 255
inside = gaussian_filter(mask_draw(lambda d: d.polygon(m2px(line('M1')), fill=255)), 6)
def near(d):
    for k in ('M1', 'M2'): d.line(m2px(line(k)), fill=255, width=int(6 / mpp))
    d.polygon(m2px(cp), fill=255); X, Y = m2px([cc])[0]; q = 14 / mpp; d.ellipse([X - q, Y - q, X + q, Y + q], fill=220)   # chapel yard
    d.polygon(m2px(loc(MON_RING)), fill=200); d.polygon(m2px(loc(PICNIC)), fill=150)
    for q_ in STRUCT[:2]: d.polygon(m2px(q_), fill=170)                                  # excavated areas (now under scrub)
dirt = gaussian_filter(mask_draw(near), 5)
path = gaussian_filter(mask_draw(lambda d: [d.line(m2px(dense(loc(r), 2)), fill=255, width=int(4.5 / mpp), joint='curve') for r in ROADS] + [d.line(m2px(loc(MON_RING)), fill=255, width=int(2 / mpp))]), 1.6)
forest = gaussian_filter(np.asarray(Image.fromarray((can * 255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR), float) / 255, 8)
# slope and granite outcrops from the 25 cm ground model (boulders stand out from the 3 m smoothed surface)
_g = np.linspace(-R, R, 1024); _GX, _GY = np.meshgrid(_g, -_g)
_rr, _cc = _rc(_GX, _GY); _lo = gaussian_filter(_dtm, 12)
relief = map_coordinates(_dtm - _lo, [_rr.ravel(), _cc.ravel()], order=1).reshape(_GX.shape)
zz = hz(GX[::3, ::3], GY[::3, ::3]); gy_, gx_ = np.gradient(zz, mpp * 3); slope = np.hypot(gx_, gy_)
slope = np.asarray(Image.fromarray(slope.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
rock = np.asarray(Image.fromarray(np.clip((relief - .5) / .8, 0, 1).astype(np.float32)).resize((TS, TS), Image.BILINEAR)) * np.clip((slope - .5) / .5, 0, 1)
rock = np.clip(gaussian_filter(rock, 1.2) * 1.8, 0, 1)
def lerp(a, b, t): t = np.clip(t, 0, 1)[..., None]; return a * (1 - t) + b * t
C = lambda *c: np.array(c, float)
col = lerp(C(96, 118, 52), C(132, 146, 68), .5 + .22 * n1 + .12 * n2)                 # meadow / scrub
col = lerp(col, C(140, 146, 78), np.clip(inside * (.6 + .06 * n2), 0, 1))           # enclosure (scrub, partly cleared)
col = lerp(col, C(72, 92, 44), forest * .75 * (1 - inside * .5))                     # shaded forest floor (eucalyptus)
col = lerp(col, C(128, 104, 72), np.clip((slope - .7) * 1.2, 0, .6))               # earthy steep banks
col = lerp(col, C(150, 132, 98), np.clip(dirt * .9, 0, .6))           # trodden earth by the banks, the chapel and the picnic site
col = lerp(col, C(136, 130, 120), rock * (.85 + .1 * n3))             # granite boulders
col = lerp(col, C(156, 150, 138), np.clip(path * (1.1 + .15 * n3), 0, 1))            # paved road
zz2 = hz(GX[::4, ::4], GY[::4, ::4]); gy2, gx2 = np.gradient(zz2, mpp * 4)
nx, ny, nz = -gx2, gy2, np.ones_like(gx2); nn = np.sqrt(nx * nx + ny * ny + 1); L_ = np.array([-.55, .45, .7]); L_ /= np.linalg.norm(L_)
shade = (nx * L_[0] + ny * L_[1] + nz * L_[2]) / nn; shade = np.asarray(Image.fromarray(shade.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
col *= np.clip(.78 + .3 * (shade - shade.mean()) / (shade.std() + 1e-6) * .35 + .22, .7, 1.15)[..., None]
clump = gaussian_filter(np.random.default_rng(5).normal(0, 1, (TS, TS)), 4); clump /= clump.std()
col = lerp(col, col * C(.84, .9, .8) / 1, np.clip(clump * .35, 0, .6) * (1 - path) * (1 - rock))      # darker clumps
spk = np.random.default_rng(6).random((TS, TS))
col = np.where(((spk > .9965) & (path < .3))[..., None], C(176, 170, 158), col)               # pebbles
col = np.where(((spk < .0012) & (inside < .3) & (forest < .3) & (path < .3))[..., None], C(232, 214, 96), col)   # gorse flowers
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
SOURCES = {
 "barroca": "Barroca, M. J.; Arezes, A.; Morais, R. A basílica paleocristã e o edifício palatino de St.ª Marta das Cortiças (Falperra): as escavações de F. Russell Cortez e de J. J. Rigaud de Sousa (pp. 129-148). Repositório Aberto da U. Porto. Medidas da basílica (25 × 16 m; naves de 7,2 e 3,5 m) e do edifício palatino (34,2 × 12,6 m; sete pilares), coordenadas dos núcleos A e B (nota 2), duas linhas de muralha segundo Martins Sarmento, escavação de Belino (1899) entre a primeira e a segunda muralhas. As plantas (fig. 2 a 6) não puderam ser descarregadas.",
 "wiki": "Wikipédia — Estação Arqueológica de Santa Marta das Cortiças (consultada em 2026-11): castro com três muralhas, do Bronze Final à época romana; basílica de três naves (séc. V-VI); edifício palatino; 46 referências a um castelo (900-1147); capela de 1520 (D. Diogo de Sousa); monumento de Nossa Senhora da Assunção, com muros à sua base; escavações de 1899, 1953-56, 1966-68, 1973-74 e 1984-85.",
 "tese": "Pinto, T. — Castros do Noroeste de Portugal (tese de doutoramento, Univ. de Santiago de Compostela); visitas em 2022 e 2025: em 2022 viam-se, entre o mato, buracos das escavações, ruínas de casas e do palácio com uma parede e uma coluna; em 2025 a vegetação tapava tudo; baloiço panorâmico inaugurado em 2023; projeto de espaço museológico não realizado.",
 "osm": "OpenStreetMap (extrato de 2026): capela, monumento (estátua), vértice geodésico Santa Marta (561,84 m), posto de vigia, torre de telecomunicações, mastro, cruzeiro, baloiço, parque de merendas, estrada de acesso e caminhos.",
 "photo": "Fotografias enviadas pelo Tiago (2026-11): fachada da capela com o anexo lateral, o muro do adro e as árvores (fotografia de Ana Ferreira, 03/2023, Google Maps); monumento de coluna com a imagem branca sobre o penedo.",
 "lidar": "DGT — LiDAR 2025, blocos 177505, 177506, 178505 e 178506: nuvens de pontos classificadas (LO-*-07-2025, ≈ 7,4 pontos de solo por m²) e MDT/MDS de 50 cm. Terreno de 25 cm interpolado dos pontos de solo; as duas linhas foram traçadas no relevo (com os penedos retirados) e ajustadas ao ponto de maior declive de cada talude; capela e monumento pela classe edifício e pelo MDS; árvores com a altura real do modelo de copas (MDS − MDT). Relevo exagerado 1,15×.",
}
os.makedirs('app/dio', exist_ok=True)
for o in sc.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.abspath(f'app/dio/{SID}.glb'), export_format='GLB', export_apply=True, export_yup=True,
                          export_image_format='JPEG', export_jpeg_quality=86, export_materials='EXPORT', use_selection=False, export_extras=True,
                          export_draco_mesh_compression_enable=False)
json.dump({'cat': CAT, 'sources': SOURCES, 'R': R, 'ex': EX, 'h0': H0, 'cx': CX, 'cz': -CY, 'trees': TREES, 'types': TYPES, 'pal': {k: [list(c) for c in v] for k, v in PAL.items()}}, open(f'app/dio/{SID}.json', 'w'))
print('ok', os.path.getsize(f'app/dio/{SID}.glb'))
