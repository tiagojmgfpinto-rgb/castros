# Builds a castillos-style disc diorama of one castro in Blender (bpy) and exports a GLB for three.js.
# Castro Máximo (Monte Castro, São Vicente, Braga). Usage: /opt/bvenv/bin/python blend/dio_cmx.py braga-castro-maximo
# Nothing of the castro is visible today: the quarry and the Estádio Municipal (Euro 2004) took most of the hill, and the houses
# excavated in 2001 under the west car park were destroyed. No plan could be consulted, so no wall or house is drawn.
# The model shows the hill as it is: terrain, quarry faces, stadium and houses from the DGT LiDAR 2025 point cloud LO-175511
# (lidar/cmx_laz.py -> lidar/cmx_*25.npy). The DGT left a hole of ≈ 190 m radius over the prison, which covers the east slope of the
# summit: there the relief is approximate (lidar/cmx_fill.py) and the houses come from the orthophoto (lidar/cmx_roofs.py).
# Roads, car parks, pitch and quarry rock from OpenStreetMap (lidar/cmx_osm.py -> blend/cmx_osm.json).
# Local frame: x east, y north (Blender Z up), metres, origin = disc centre.
import sys, json, math, importlib, os
import numpy as np
import bpy, bmesh
from PIL import Image, ImageFilter, ImageEnhance
from scipy.ndimage import gaussian_filter, maximum_filter, label, binary_closing, binary_opening, binary_dilation

SID = sys.argv[-1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, 'blend')
rng = np.random.default_rng(17)
OSM = json.load(open('blend/cmx_osm.json')); W_ = {w['id']: w for w in OSM['ways']}
def way(i): return np.array(W_[i]['pts'], float)
RW = {'residential': 6.0, 'service': 4.0, 'pedestrian': 4.0, 'track': 3.0, 'footway': 2.0, 'path': 1.6, 'steps': 2.0}
ROADS = [w['pts'] for w in OSM['ways'] if w['tags'].get('highway') in RW]
ROADW = [RW[w['tags']['highway']] for w in OSM['ways'] if w['tags'].get('highway') in RW]
PITCH = way(166248899); STADIUM = way(116650252); PITCH2 = way(149578802)
PARK_W, PARK_NW = way(1266855373), way(1266855372)          # car parks west of the stadium («estacionamentos da bancada poente»)
PARKS = [way(i) for i in (1266855373, 1266855372, 152233150, 485158330, 485158331)]
ROCKS = [way(485203843), way(1305558276)]                    # natural=bare_rock: the quarry floor and faces
GRASS = [way(i) for i in (485199233, 1429211145, 1495303882) if i in W_]
ALLOT = way(1470431193) if 1470431193 in W_ else None                                     # Horta Urbana de São Vicente
ROOFS = json.load(open('blend/cmx_roofs.json'))
ORTO = np.asarray(Image.open('blend/cmx_orto.png').convert('RGB'), float)
OS_, OX_, OY_ = 1.07, 305.0, 212.0                           # orthophoto px = OX + (x + 160)·S, OY − (y − 232)·S (local metres)

# ---------- disc: holds the summit, the quarry faces, the whole stadium and the west car parks
CX, CY, R = -120.0, 120.0, 225.0
def loc(p): p = np.asarray(p, float); return np.stack([p[..., 0] - CX, p[..., 1] - CY], -1)

# ---------- terrain heights: DGT LiDAR 2025 ground points (class 2), TIN on a 25 cm grid, the prison hole filled, lightly smoothed
from scipy.ndimage import map_coordinates
X0L, Y0L = -24590.1, 210181.1                     # site point in PT-TM06
LB = json.load(open('lidar/cmx_box.json'))
_dtm = np.load('lidar/cmx_dtmf25.npy').astype(np.float32); _dtm = np.where(np.isnan(_dtm), np.nanmean(_dtm), _dtm)
VOID = np.load('lidar/cmx_void25.npy')
DTM = gaussian_filter(_dtm, 1.)
_dsm = np.load('lidar/cmx_dsm25.npy').astype(np.float32)
CHM = np.where(VOID, 0, _dsm - _dtm)
BLD = np.load('lidar/cmx_bld25.npy') & ~VOID
def _rc(x, y):  # Blender xy -> grid row/col
    lx = np.asarray(x, float) + CX; ly = np.asarray(y, float) + CY
    return (LB['y1'] - (Y0L + ly)) / LB['cs'] - .5, (X0L + lx - LB['x0']) / LB['cs'] - .5
def _samp(A, x, y, order=1):
    r, c = _rc(x, y); return map_coordinates(A, [np.atleast_1d(r).ravel(), np.atleast_1d(c).ravel()], order=order, mode='nearest').reshape(np.shape(r))
def hraw(x, y): return _samp(DTM, x, y)
H0 = float(hraw(0, 0)); EX = 1.0
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


from matplotlib.path import Path as MPath
from scipy.spatial import cKDTree
def inside_any(polys, x, y):
    P = np.stack([np.ravel(x), np.ravel(y)], 1); m = np.zeros(len(P), bool)
    for q in polys: m |= MPath(q).contains_points(P)
    return m.reshape(np.shape(x))
ochre_m = col_mat('ochre', (204, 142, 58), .8); cream_m = col_mat('cream', (240, 232, 208), .8)
conc_m = col_mat('concrete', (206, 204, 198), .85); conc2_m = col_mat('concrete2', (172, 170, 164), .9); seat_m = col_mat('seats', (96, 100, 108), .7); rock_m = col_mat('rock', (124, 118, 108), .95)

# ---------- 1 m working grid over the disc (Blender xy), heights not exaggerated
K = 4; nB = LB['n'] // K
gxl = LB['x0'] + (np.arange(nB) + .5) - X0L - CX; gyl = LB['y1'] - (np.arange(nB) + .5) - Y0L - CY     # cell centres, row 0 = north
GXc, GYc = np.meshgrid(gxl, gyl); IN = np.hypot(GXc, GYc) < R - 1.5
VOID1 = VOID.reshape(nB, K, nB, K).mean(axis=(1, 3)) > .5
G1 = (DTM.reshape(nB, K, nB, K).min(axis=(1, 3)) - H0) * EX                 # ground (lowest in the cell)

# ---------- modern buildings from the LiDAR building class (6): roofs at the MDS height, walls down to the ground
bm = BLD.reshape(nB, K, nB, K).mean(axis=(1, 3)) > .15
bm = binary_opening(binary_closing(bm, iterations=1), iterations=1) & ~VOID1
_L0, _n0 = label(bm); _fr = np.bincount(_L0[bm & IN], minlength=_n0 + 1) / np.maximum(1, np.bincount(_L0.ravel(), minlength=_n0 + 1))
bm &= IN & (_fr[_L0] > .5)                                                   # drop buildings that are mostly outside the disc (the north-east stand)
top = (_dsm.reshape(nB, K, nB, K).max(axis=(1, 3)) - H0) * EX
_st = np.stack([np.roll(np.roll(np.where(bm, top, np.nan), a, 0), b, 1) for a in (-1, 0, 1) for b in (-1, 0, 1)])
import warnings; warnings.simplefilter('ignore')
top = np.where(bm, np.nanmedian(_st, 0), np.nan)                            # 3 × 3 median on the roof cells only
Lb, nb_ = label(bm)
cbase = np.full(nb_ + 1, np.inf); np.minimum.at(cbase, Lb[bm], G1[bm]); base = np.where(bm, cbase[Lb] - .4, np.nan)
in_st = inside_any([loc(STADIUM)], GXc, GYc)
st_ids = np.unique(Lb[bm & in_st]); STM = bm & np.isin(Lb, st_ids)
def hfield(G):   # heightfield blocks: one top quad per 1 m cell, walls where the neighbour is lower or empty
    ii, jj = np.nonzero(G); x0 = GXc[ii, jj] - .5; x1 = x0 + 1; y0 = GYc[ii, jj] - .5; y1 = y0 + 1; zt = top[ii, jj]
    TV = np.stack([np.stack([x0, y0, zt], 1), np.stack([x1, y0, zt], 1), np.stack([x1, y1, zt], 1), np.stack([x0, y1, zt], 1)], 1).reshape(-1, 3)
    TF = np.arange(len(TV)).reshape(-1, 4)
    WV = []
    for di, dj in ((0, 1), (0, -1), (-1, 0), (1, 0)):
        ni = np.clip(ii + di, 0, nB - 1); nj = np.clip(jj + dj, 0, nB - 1)
        zn = np.where(G[ni, nj], top[ni, nj], base[ii, jj]); k = zn < zt - .25
        a, b_, c_, d_, z0, z1 = x0[k], x1[k], y0[k], y1[k], zn[k], zt[k]
        if (di, dj) == (0, 1): q = [(b_, c_, z0), (b_, d_, z0), (b_, d_, z1), (b_, c_, z1)]
        elif (di, dj) == (0, -1): q = [(a, d_, z0), (a, c_, z0), (a, c_, z1), (a, d_, z1)]
        elif (di, dj) == (-1, 0): q = [(b_, d_, z0), (a, d_, z0), (a, d_, z1), (b_, d_, z1)]
        else: q = [(a, c_, z0), (b_, c_, z0), (b_, c_, z1), (a, c_, z1)]
        WV.append(np.stack([np.stack(v, 1) for v in q], 1).reshape(-1, 3))
    WV = np.vstack(WV); WF = np.arange(len(WV)).reshape(-1, 4)
    return (TV.tolist(), TF.tolist(), [(0, 0)] * len(TV)), (WV.tolist(), WF.tolist(), [(0, 0)] * len(WV))
# ---------- the stadium: the two stands are built from their measured outline and roof heights (the LiDAR sees only the roofs);
# the lower stadium buildings stay as 1 m heightfield blocks
SA = math.radians(-40.3)                                     # long axis of the pitch (OpenStreetMap pitch, minAreaRect)
PC = loc([-164.3, 210.3]); PZ = float(hz(*PC))               # pitch centre and level
_ca, _sa = math.cos(SA), math.sin(SA)
GU = (GXc - PC[0]) * _ca + (GYc - PC[1]) * _sa; GV = -(GXc - PC[0]) * _sa + (GYc - PC[1]) * _ca
tall = STM & (top > PZ + 25)
STANDS = []
for side in (1, -1):
    m = tall & (GV * side > 30)
    w_ = GV[m] * side; u_ = GU[m]; z_ = top[m]
    wf, wb = np.percentile(w_, 1.5), np.percentile(w_, 98.5); u0, u1 = np.percentile(u_, 1), np.percentile(u_, 99)
    A_ = np.stack([np.ones_like(w_), w_], 1); cf = np.linalg.lstsq(A_, z_, rcond=None)[0]
    zf, zb_ = cf[0] + cf[1] * wf, cf[0] + cf[1] * wb
    STANDS.append(dict(side=side, wf=float(wf), wb=float(wb), u0=float(u0), u1=float(u1), zf=float(zf), zb=float(zb_)))
    print('stand', side, 'w %.1f–%.1f u %.1f–%.1f roof %.1f–%.1f m' % (wf, wb, u0, u1, zf + H0, zb_ + H0))
STAND = np.zeros_like(bm)
for S_ in STANDS: STAND |= (GV * S_['side'] > S_['wf'] - 3) & (GV * S_['side'] < S_['wb'] + 3) & (GU > S_['u0'] - 3) & (GU < S_['u1'] + 3)
STAND &= STM
tS, wS = hfield(STM & ~STAND); tH, wH = hfield(bm & ~STM)
TP = T2(*PC, SA)
def P3(u, w, side, z): x, y = TP(u, w * side); return (x, y, z)
def slab(S_, u0, u1, w0, w1, z0f, z0b, th):   # sloped box: top from (w0, z0f) to (w1, z0b), thickness th
    s_ = S_['side']; V = []
    for (u, w, z) in ((u0, w0, z0f), (u1, w0, z0f), (u1, w1, z0b), (u0, w1, z0b)): V.append(P3(u, w, s_, z))
    V += [(x, y, z - th) for x, y, z in V]
    F = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    if s_ < 0: F = [f[::-1] for f in F]
    return V, F, [(0, 0)] * 8
RAKE = .5; TREAD = .8; ZG = PZ - 4
canopy, treads, risers, walls = [], [], [], []
for S_ in STANDS:
    s_ = S_['side']; u0, u1, wf, wb = S_['u0'], S_['u1'], S_['wf'], S_['wb']
    roof = lambda w: S_['zf'] + (S_['zb'] - S_['zf']) * (w - wf) / (wb - wf)
    canopy.append(slab(S_, u0, u1, wf, wb, S_['zf'], S_['zb'], 1.2))
    w0 = 45.0; ns = int((wb - 5 - w0) / TREAD); wt = w0 + ns * TREAD; zt = PZ + 1 + ns * TREAD * RAKE
    TV, TF, RV, RF = [], [], [], []
    for k in range(ns):
        wa, wb_ = w0 + k * TREAD, w0 + (k + 1) * TREAD; za = PZ + 1 + k * TREAD * RAKE; zr = za + TREAD * RAKE
        o = len(RV); RV += [P3(u0, wa, s_, za), P3(u1, wa, s_, za), P3(u1, wa, s_, zr), P3(u0, wa, s_, zr)]; RF.append((o, o + 1, o + 2, o + 3) if s_ > 0 else (o + 3, o + 2, o + 1, o))
        o = len(TV); TV += [P3(u0, wa, s_, zr), P3(u1, wa, s_, zr), P3(u1, wb_, s_, zr), P3(u0, wb_, s_, zr)]; TF.append((o, o + 1, o + 2, o + 3) if s_ > 0 else (o + 3, o + 2, o + 1, o))
    treads.append((TV, TF, [(0, 0)] * len(TV))); risers.append((RV, RF, [(0, 0)] * len(RV)))
    walls.append(slab(S_, u0, u1, w0 - .6, w0, PZ + 1, PZ + 1, 1 + 4))                        # front wall to the pitch
    walls.append(slab(S_, u0, u1, wt, wb - 1, zt, zt, zt - ZG))                               # concourse block behind the seats
    walls.append(slab(S_, u0, u1, wb - 1, wb, roof(wb - 1) - 1.2, roof(wb) - 1.2, roof(wb) - 1.2 - ZG))   # back wall up to the roof
    for ue, du in ((u0, 1), (u1, -1)):                                                          # end walls under the seats
        for k in range(0, ns, 4):
            wa = w0 + k * TREAD; wz = min(wt, wa + 4 * TREAD); zr = PZ + 1 + min(ns, k + 4) * TREAD * RAKE
            walls.append(slab(S_, min(ue, ue + du * .6), max(ue, ue + du * .6), wa, wz, zr, zr, zr - ZG))
# the cables that hang the two roofs across the pitch: the LiDAR point cloud has returns on them at 133.6–134.8 m (classes 6 and 7),
# 34 cables from u = −63.5 to 60.5 m (one every 3.76 m), about 0.8 m of sag in the middle
def tube(pts, r):
    V = []; F = []; pts = np.asarray(pts, float)
    for i, p in enumerate(pts):
        d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]; d /= np.linalg.norm(d)
        a = np.cross(d, [0, 0, 1]); a /= np.linalg.norm(a); b = np.cross(a, d)
        for k in range(4): t_ = k * math.pi / 2; V.append(tuple(p + (a * math.cos(t_) + b * math.sin(t_)) * r))
    for i in range(len(pts) - 1):
        for k in range(4): k2 = (k + 1) % 4; F.append((i * 4 + k, i * 4 + k2, (i + 1) * 4 + k2, (i + 1) * 4 + k))
    return V, F, [(0, 0)] * len(V)
SN, SS_ = STANDS
cu0, cu1, ncab = -63.5, 60.5, 34
cables = []
for uc in np.linspace(cu0, cu1, ncab):
    pa = np.array(P3(uc, SN['wf'] + .3, 1, SN['zf'] - .3)); pb = np.array(P3(uc, SS_['wf'] + .3, -1, SS_['zf'] - .3))
    tt = np.linspace(0, 1, 17); pts = pa[None] * (1 - tt[:, None]) + pb[None] * tt[:, None]; pts[:, 2] -= .8 * 4 * tt * (1 - tt)
    cables.append(tube(pts, .18))
goals = []
for e in (-1, 1):
    ug = e * 52.5
    for vv in (-3.66, 3.66): goals.append(boxv(*TP(ug, vv), SA, .14, .14, PZ, PZ + 2.44))
    goals.append(boxv(*TP(ug, 0), SA, .14, 7.46, PZ + 2.3, PZ + 2.44))
print('stadium: %d cables, %d steps per stand' % (ncab, ns))
put('ST', 'Coberturas do estádio', conc_m, [tS] + canopy, 'A', 'conf'); put('ST', 'Estádio', conc2_m, [wS] + walls, 'A', 'conf')
put('ST', 'Degraus das bancadas', conc_m, treads, 'A', 'doc'); put('ST', 'Cadeiras das bancadas', seat_m, risers, 'A', 'doc')
put('ST', 'Cabos das coberturas', steel_m, cables, 'A', 'conf'); put('ST', 'Balizas', white_m, goals, 'A', 'conf')
put('ED', 'Telhados das casas', tile_m, [tH], 'A', 'conf'); put('ED', 'Paredes das casas', lime_m, [wH], 'A', 'conf')
print('building cells: stadium', int(STM.sum()), 'houses', int((bm & ~STM).sum()))
item(id='ST', name='Estádio Municipal de Braga («A Pedreira»)', kind='Edifício moderno', phase='Euro 2004', ev='conf', evB='conf',
     dims=f'duas bancadas laterais com coberturas de {STANDS[0]["zf"] + H0:.0f} a {STANDS[0]["zb"] + H0:.0f} m de altitude (relvado a {PZ + H0:.0f} m); {ncab} cabos sobre o relvado, um a cada 3,8 m (LiDAR)',
     note='Projeto de Eduardo Souto de Moura com o engenheiro Rui Furtado, para o Euro 2004: só duas bancadas laterais, e nos topos os anfiteatros de rocha da encosta (Wikipédia). Foi construído na antiga pedreira do Monte Castro, dentro da zona de proteção do castro criada em 1985, que não foi respeitada. Nas obras, sobretudo na zona dos estacionamentos da bancada poente, apareceram casas de planta circular, estudadas numa escavação de emergência de cinco meses e depois destruídas (tese). Planta, altura e inclinação das coberturas e posição dos cabos medidas no LiDAR de 2025, que tem pontos nos próprios cabos. O LiDAR não vê debaixo das coberturas: os degraus das bancadas (inclinação de cerca de 27°) e as paredes são esquemáticos; as cores das cadeiras não estão representadas. As construções mais baixas do estádio são blocos de 1 m com a altura do LiDAR.',
     src=['wiki', 'tese', 'osm', 'lidar'])
item(id='ED', name='Casas do bairro', kind='Edifício moderno', phase='atual', ev='conf', evB='conf',
     dims='telhados com a altura medida no LiDAR (MDS), em blocos de 1 m',
     note='Casas a sul e a poente do cume, na Rua da Pedreira, na Rua do Muro e no Bairro de Nossa Senhora do Monte, sobre as encostas que Carlos Teixeira descreveu nos anos 1930 com fossos do lado da cidade. Só no estado atual.', src=['lidar', 'osm', 'sipa'])
# houses inside the LiDAR hole: roofs picked out of the orthophoto, two floors assumed
EV_t = []; EV_w = []
for rf in ROOFS:
    c = loc(rf['c']); w, h, a = rf['w'], rf['h'], math.radians(rf['a'])
    if w < h: w, h, a = h, w, a + math.pi / 2
    if math.hypot(*c) > R - w / 2 - 1: continue
    t = T2(*c, a); cs = np.array([t(u, v) for u, v in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))])
    g0 = float(np.min(hz(cs[:, 0], cs[:, 1]))) - .3; gt = float(np.max(hz(cs[:, 0], cs[:, 1])))
    EV_w.append(boxv(*c, a, w, h, g0, gt + 5.6)); EV_t.append(gable(*c, a, w, h, gt + 5.6, 1.7))
put('EV', 'Casas na zona sem LiDAR', lime_m, EV_w, 'A', 'doc'); put('EV', 'Telhados na zona sem LiDAR', tile_m, EV_t, 'A', 'doc')
item(id='EV', name='Casas na zona sem dados LiDAR', kind='Edifício moderno', phase='atual', ev='doc', evB='doc',
     dims=f'{len(EV_w)} casas · planta pelos telhados da ortofoto · altura não medida (dois pisos)',
     note='A DGT não publicou pontos LiDAR num círculo de cerca de 190 m de raio à volta do Estabelecimento Prisional, que apanha a encosta nascente do cume, o fim da Avenida Doutor Artur Soares e a Rua do Castro Máximo. Aqui as casas foram tiradas dos telhados da ortofoto enviada pelo Tiago, e o relevo é aproximado.', src=['orto', 'lidar'])

# ---------- the summit (the part of the hill the quarry left): 195 m contour of the LiDAR ground model, summit point
from skimage.measure import find_contours
Z1 = (DTM.reshape(nB, K, nB, K).mean(axis=(1, 3)))
zz = np.where(IN & ~VOID1, Z1, -1); im_ = np.unravel_index(np.argmax(zz), zz.shape); SUM = np.array([GXc[im_], GYc[im_]]); ZMAX = float(Z1[im_])
cl = [c for c in find_contours(np.where(IN, Z1, 0), 195.0) if len(c) > 30]
def c2xy(c): return np.stack([np.interp(c[:, 1], np.arange(nB), gxl), np.interp(c[:, 0], np.arange(nB), gyl)], 1)
cl = [c2xy(c) for c in cl]; CU = min(cl, key=lambda p: np.min(np.hypot(*(p - SUM).T)))
CU = CU[::2]; CU_closed = np.hypot(*(CU[0] - CU[-1])) < 3
CU_area = abs(np.sum(CU[:, 0] * np.roll(CU[:, 1], -1) - np.roll(CU[:, 0], -1) * CU[:, 1])) / 2
put('CU', 'Cume do Monte Castro', cream_m, [sweep(CU, .5, .14, 0, .3, closed=CU_closed)], 'A', 'conf')
print('summit', SUM + [CX, CY], 'z %.1f' % ZMAX, 'contour 195 m: %d pts, %.2f ha, closed %s' % (len(CU), CU_area / 1e4, CU_closed))
item(id='CU', name='Cume do Monte Castro', kind='Relevo', phase='—', ev='conf', evB='conf',
     dims=f'cota máxima 198,2 m (SIPA); {ZMAX:.1f} m no LiDAR de 2025 · a linha é a curva de nível dos 195 m ({CU_area / 1e4:.2f} ha)',
     note='O que resta do povoado (a «acrópole») ocupa o topo do monte (Avenida Central, 2008). É um dos pontos mais altos de Braga e domina o vale do Cávado a norte (SIPA). Nos anos 1930 Carlos Teixeira descreveu fossos do lado da cidade, talvez duas linhas de muralha e casas circulares de pedra; nas sondagens da Universidade do Minho (1976-78) só apareceu um muro com paramento externo aparelhado e um piso de argila batida. Nada disto se identifica hoje, nem no terreno nem no LiDAR. Nas visitas do Tiago, em 2022 e 2025, não havia nenhuma ruína visível. A linha creme não é uma muralha: marca só o alto do monte.',
     src=['sipa', 'blog', 'morais', 'tese', 'lidar'])

# ---------- quarry faces: ground steeper than 52° in the LiDAR (outside buildings and the hole), as bare granite
gy_, gx_ = np.gradient(Z1, 1.0); slope = np.hypot(gx_, gy_)
fq = (slope > 1.28) & IN & ~VOID1 & ~binary_dilation(bm, iterations=2)
Lq, nq = label(fq); sz = np.bincount(Lq.ravel()); fq &= np.isin(Lq, np.nonzero(sz > 25)[0]) & (Lq > 0)
ii, jj = np.nonzero(fq); vid = {}; QV = []; QF = []
def _v(i, j):
    k = (i, j)
    if k not in vid:
        x = gxl[0] - .5 + j; y = gyl[0] + .5 - i; vid[k] = len(QV); QV.append((x, y, float(hz(x, y)) + .1))
    return vid[k]
for i, j in zip(ii, jj): QF.append((_v(i + 1, j), _v(i + 1, j + 1), _v(i, j + 1), _v(i, j)))
put('PD', 'Frentes da pedreira', rock_m, [(QV, QF, [(0, 0)] * len(QV))], 'A', 'conf')
qdrop = float(np.percentile(Z1[binary_dilation(fq, iterations=3) & IN & ~VOID1], 95) - np.percentile(Z1[binary_dilation(fq, iterations=3) & IN & ~VOID1], 5))
print('quarry faces', int(fq.sum()), 'm2, height range %.0f m' % qdrop)
item(id='PD', name='Frentes da antiga pedreira', kind='Pedreira', phase='séc. XX', ev='conf', evB='conf',
     dims=f'≈ {int(fq.sum()):d} m² de rocha com mais de 52° de inclinação (LiDAR); escarpas de 15 e 30 m (OpenStreetMap)',
     note='As pedreiras abertas nas encostas do Monte Castro «desfiguraram em grande medida o povoado fortificado» (SIPA) e não deixam perceber a sua extensão original (Avenida Central, 2008). O estádio foi construído dentro da antiga pedreira; parte da zona arqueológica está hoje vedada pelo perigo de queda da ravina (tese). As frentes de rocha estão marcadas onde o modelo do terreno do LiDAR passa os 52°.',
     src=['sipa', 'blog', 'tese', 'osm', 'lidar'])

# ---------- the 2001 excavation: car parks west of the stadium (OpenStreetMap outline), where the round houses appeared
def clip_disc(p, m=1.5):
    p = loc(p); segs = []; cur = []
    for q in dense(p, 1.0):
        if math.hypot(*q) < R - m: cur.append(q)
        elif len(cur) > 3: segs.append(np.array(cur)); cur = []
        else: cur = []
    if len(cur) > 3: segs.append(np.array(cur))
    return segs
ex_geo = [sweep(s_, .9, .3, 0, .3) for P_ in (PARK_W, PARK_NW) for s_ in clip_disc(P_)]
put('EX', 'Zona da escavação de 2001', ochre_m, ex_geo, 'A', 'doc')
item(id='EX', name='Estacionamentos a poente do estádio: casas castrejas escavadas em 2001', kind='Escavação', phase='2001', ev='doc', evB='doc',
     dims='limite dos parques de estacionamento (OpenStreetMap); a área escavada exata não foi publicada nas fontes consultadas',
     note='Na construção do estádio, sobretudo na zona dos estacionamentos da bancada poente, apareceram várias casas de planta circular. O Gabinete de Arqueologia da Câmara Municipal de Braga (Armandino Cunha), com a Unidade de Arqueologia da U. Minho, fez uma escavação de emergência de cinco meses: encontraram-se unidades habitacionais e áreas de circulação, organizadas por vários cruzamentos de ruas (Morais 2020). O objetivo foi estudar as ruínas e retirar as peças mais importantes (duas lareiras foram para o Museu D. Diogo de Sousa; outras peças para o Museu Pio XII), não conservá-las: estão destruídas sob o asfalto. A linha ocre marca os parques de estacionamento, não a área escavada, que fica por localizar com as plantas da dissertação de D. Rocha (2017).',
     src=['tese', 'morais', 'rocha'])
# ---------- trees from the LiDAR canopy height model (MDS − MDT, 25 cm): local maxima above 3 m, real heights; none in the hole
from scipy.ndimage import maximum_filter as _mf
rS, cS = _rc(np.array([-R, R]), np.array([R, -R])); r0_, r1_ = max(0, int(rS.min())), int(rS.max()) + 1; c0_, c1_ = max(0, int(cS.min())), int(cS.max()) + 1
NOB = binary_dilation(BLD, iterations=8) | VOID
CH = gaussian_filter(np.where(NOB, 0, CHM)[r0_:r1_, c0_:c1_], 2.4)
pk = (CH == _mf(CH, 13)) & (CH > 3)
ys, xs = np.nonzero(pk); tp = []; TH = {}
for yy_, xx_ in zip(ys, xs):
    lx = LB['x0'] + (c0_ + xx_ + .5) * LB['cs'] - X0L; ly = LB['y1'] - (r0_ + yy_ + .5) * LB['cs'] - Y0L
    x, y = lx - CX, ly - CY
    if math.hypot(x, y) < R - 2.5: tp.append((x, y)); TH[(x, y)] = float(CHM[r0_ + yy_ - 2:r0_ + yy_ + 3, c0_ + xx_ - 2:c0_ + xx_ + 3].max())
_cg = np.linspace(-R, R, 512)
can = gaussian_filter((_samp(np.where(NOB, 0, CHM), *np.meshgrid(_cg, -_cg)) > 2.5).astype(float), 1.2)
# structures to keep clear: buildings (1 m cells), the summit line, the car park outline, the orthophoto houses
_bpts = np.stack([GXc[bm], GYc[bm]], 1)
wallpts = np.vstack([_bpts, dense(CU, .8)] + [np.array(g_[0])[:, :2] for g_ in ex_geo if g_[0]] + [np.array(w_[0])[:, :2] for w_ in EV_w])
kd = cKDTree(wallpts)
_encl = MPath(CU) if CU_closed else MPath(np.vstack([CU, CU[:1]]))
ntp0 = len(tp)
# the summit is kept fairly clear (it is scrub and grass today); elsewhere the real trees, but none on the car parks and the pitch
def _keep(p):
    dw = kd.query(p)[0]
    if inside_any([loc(q) for q in PARKS] + [loc(PITCH)], p[0], p[1]): return dw > 3 and rng.random() < .8
    return (dw > 4 and not _encl.contains_point(p)) or (dw > 4 and rng.random() < .35)
tp = [p for p in tp if _keep(p)]
YARD = []
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
    pass
    TREES.append([round(x, 2), round(y, 2), round(g, 2), round(min(22, h_ * EX), 1), TYPES.index(kind), int(rng.integers(0, len(PAL[kind]))), round(rng.random() * 6.28, 2), round(wf * (.92 + .16 * rng.random()), 2)])
# undergrowth: gorse/broom at the forest edges and on the slopes, grass tufts everywhere but the path and the structures
# undergrowth: gorse/broom at the forest edges and on the scrubby slopes, grass tufts on the open ground (not on paving)
canm = lambda x, y: can[min(511, max(0, int((R - y) / (2 * R) * 512))), min(511, max(0, int((x + R) / (2 * R) * 512)))]
pathpts = np.vstack([dense(loc(r), 1.5) for r in ROADS]); kp = cKDTree(pathpts)
PAVED = [loc(q) for q in PARKS] + [loc(PITCH), loc(PITCH2), loc(STADIUM)]
def free(x, y, dw, dp=2.5): return math.hypot(x, y) < R - 2 and kd.query((x, y))[0] > dw and kp.query((x, y))[0] > dp and not inside_any(PAVED, x, y) and not fq[min(nB - 1, max(0, int((gyl[0] + .5 - y)))), min(nB - 1, max(0, int(x - gxl[0] + .5)))]
n_sh = 0
for _ in range(9000):
    x, y = (rng.random(2) * 2 - 1) * R; c = canm(x, y)
    if n_sh > 360 or not free(x, y, 4): continue
    if rng.random() < (.9 if .12 < c < .6 else .1):
        TREES.append([round(x, 2), round(y, 2), round(float(hz(x, y)), 2), round(1.4 + rng.random() * 1.6, 2), TYPES.index('shrub'), int(rng.integers(0, 3)), round(rng.random() * 6.28, 2)]); n_sh += 1
n_tu = 0
for _ in range(24000):
    x, y = (rng.random(2) * 2 - 1) * R
    if n_tu > 2800 or not free(x, y, 1.6, 1.8): continue
    if rng.random() < (.85 if _encl.contains_point((x, y)) else .5):
        TREES.append([round(x, 2), round(y, 2), round(float(hz(x, y)), 2), round(.35 + rng.random() * .35, 2), TYPES.index('tuft'), int(rng.integers(0, 3)), round(rng.random() * 6.28, 2)]); n_tu += 1
print('trees', len(tp), 'shrubs', n_sh, 'tufts', n_tu, 'R', R)

# ---------- labels (empties named LBL-...)
def lbl(t, p, dz=3):
    e = bpy.data.objects.new(f'LBL-{t}-{len(bpy.data.objects)}', None); e.location = (float(p[0]), float(p[1]), float(hz(p[0], p[1])) + dz)
    bpy.context.scene.collection.objects.link(e)
lbl('Cume do Monte Castro · 198 m', SUM, 5)
lbl('Frentes da antiga pedreira', loc(ROCKS[1].mean(0)), 6)
lbl('Estacionamento poente · casas escavadas em 2001', loc(PARK_W.mean(0)), 5)
lbl('Estádio Municipal de Braga', PC, 44)
_vc = np.array([60.0, 30.0]) - [CX, CY]
lbl('Zona sem dados LiDAR (prisão)', _vc, 8)
lbl('Bairro de Nossa Senhora do Monte', loc([-133.3, -48.8]), 6)

# ---------- stylised ground: scrub and grass, forest floor, granite of the quarry, asphalt car parks, pitch, streets;
# in the LiDAR hole the colours come from the orthophoto (gardens, lawns, yards)
TS = 4096; mpp = 2 * R / TS
jj, ii = np.mgrid[0:TS, 0:TS]; GX = (ii + .5) * mpp - R; GY = R - (jj + .5) * mpp
def noise(sig, seed):
    return gaussian_filter(np.random.default_rng(seed).normal(0, 1, (TS, TS)), sig, mode='wrap')
n1 = noise(40, 1); n1 /= n1.std(); n2 = noise(10, 2); n2 /= n2.std(); n3 = noise(2, 3); n3 /= n3.std()
from PIL import ImageDraw
def m2px(p): return [((x + R) / mpp, (R - y) / mpp) for x, y in p]
def mask_draw(fn):
    im = Image.new('L', (TS, TS), 0); fn(ImageDraw.Draw(im)); return np.asarray(im, float) / 255
def polys(L_, fill=255):
    def f(d):
        for q in L_: d.polygon(m2px(loc(q)), fill=fill)
    return f
park = gaussian_filter(mask_draw(polys(PARKS)), 1.2)
pitch = mask_draw(polys([PITCH, PITCH2]))
rockp = gaussian_filter(mask_draw(polys(ROCKS)), 4)
grass = gaussian_filter(mask_draw(polys(GRASS + ([ALLOT] if ALLOT is not None else []))), 3)
inside = gaussian_filter(mask_draw(lambda d: d.polygon(m2px(CU), fill=255)), 6)
# streets by kind and surface (OpenStreetMap): granite setts or asphalt with lighter pavements, car park aisles, paths
RD = [w for w in OSM['ways'] if w['tags'].get('highway') in RW]
def rclass(t):
    h = t['highway']; sf = t.get('surface', '')
    if h == 'residential': return 'asph' if sf == 'asphalt' else 'sett'
    if h == 'service': return 'aisle' if t.get('service') == 'parking_aisle' or sf == 'asphalt' else 'serv'
    if h in ('pedestrian', 'footway', 'steps'): return 'walk'
    return 'earth'
def _rd(cls, extra=0.):
    def f(d):
        for w in RD:
            if rclass(w['tags']) in cls: d.line(m2px(dense(loc(w['pts']), 2)), fill=255, width=max(2, int((RW[w['tags']['highway']] + extra) / mpp)), joint='curve')
    return f
path = gaussian_filter(mask_draw(_rd(('sett', 'asph', 'aisle', 'serv', 'walk', 'earth'))), 1.4)
pave = gaussian_filter(mask_draw(_rd(('sett', 'asph'), 3.2)), 1.0)                    # pavements either side of the streets
r_sett = gaussian_filter(mask_draw(_rd(('sett',))), .8); r_asph = gaussian_filter(mask_draw(_rd(('asph', 'aisle'))), .8)
r_serv = gaussian_filter(mask_draw(_rd(('serv',))), .8); r_walk = gaussian_filter(mask_draw(_rd(('walk',))), .8); r_earth = gaussian_filter(mask_draw(_rd(('earth',))), 1.2)
# car park bays: white lines every 2.5 m, 2.8 to 8 m either side of each aisle, kept inside the car park outlines (schematic)
def _bays(d):
    for w in RD:
        if w['tags'].get('service') != 'parking_aisle': continue
        p = loc(np.array(w['pts'], float))
        for a, b in zip(p[:-1], p[1:]):
            L = np.linalg.norm(b - a)
            if L < 6: continue
            t_ = (b - a) / L; n_ = np.array([-t_[1], t_[0]])
            for s_ in np.arange(1.5, L - 1.4, 2.5):
                q = a + t_ * s_
                for sd in (1, -1): d.line(m2px([q + n_ * sd * 2.8, q + n_ * sd * 8.0]), fill=255, width=2)
            for sd in (1, -1): d.line(m2px([a + t_ * 1.5 + n_ * sd * 8.0, b - t_ * 1.4 + n_ * sd * 8.0]), fill=255, width=2)
park_in = mask_draw(polys(PARKS))
bays = mask_draw(_bays) * park_in * (1 - mask_draw(_rd(('aisle',), -.4)))
stad = gaussian_filter(mask_draw(polys([STADIUM])), 1.5)
# pitch markings of a 105 × 68 m field on the pitch centre (Laws of the Game; the real size of this field is not in the sources)
def _lines(d):
    def L(pts): d.line(m2px([TP(u, v) for u, v in pts]), fill=255, width=2)
    def circ(cu, cv, r, a0=0, a1=2 * math.pi, n=72): L([(cu + r * math.cos(a0 + (a1 - a0) * k / n), cv + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)])
    L([(-52.5, -34), (52.5, -34), (52.5, 34), (-52.5, 34), (-52.5, -34)]); L([(0, -34), (0, 34)]); circ(0, 0, 9.15)
    for e in (-1, 1):
        L([(e * 52.5, -20.16), (e * (52.5 - 16.5), -20.16), (e * (52.5 - 16.5), 20.16), (e * 52.5, 20.16)])
        L([(e * 52.5, -9.16), (e * (52.5 - 5.5), -9.16), (e * (52.5 - 5.5), 9.16), (e * 52.5, 9.16)])
        ang = math.acos(5.5 / 9.15); c_ = e * (52.5 - 11); circ(c_, 0, 9.15, (math.pi if e > 0 else 0) - ang, (math.pi if e > 0 else 0) + ang, 24)
        circ(c_, 0, .25, n=8); circ(e * 52.5, -34, 1, n=8); circ(e * 52.5, 34, 1, n=8)
    circ(0, 0, .25, n=8)
marks = mask_draw(_lines)
forest = gaussian_filter(np.asarray(Image.fromarray((can * 255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR), float) / 255, 8)
_vi = np.clip(((gyl[0] + .5) - GY) / 1.0, 0, nB - 1).astype(int); _vj = np.clip((GX - (gxl[0] - .5)) / 1.0, 0, nB - 1).astype(int)
hole = gaussian_filter(VOID1[_vi, _vj].astype(float), 6)
bld_t = gaussian_filter(bm[_vi, _vj].astype(float), 1)
_g = np.linspace(-R, R, 1024); _GX, _GY = np.meshgrid(_g, -_g)
_rr, _cc = _rc(_GX, _GY); _lo = gaussian_filter(_dtm, 12)
relief = map_coordinates(_dtm - _lo, [_rr.ravel(), _cc.ravel()], order=1).reshape(_GX.shape)
zz = hz(GX[::3, ::3], GY[::3, ::3]); gy_, gx_ = np.gradient(zz, mpp * 3); slope = np.hypot(gx_, gy_)
slope = np.asarray(Image.fromarray(slope.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
rock = np.asarray(Image.fromarray(np.clip((relief - .4) / .8, 0, 1).astype(np.float32)).resize((TS, TS), Image.BILINEAR)) * np.clip((slope - .45) / .5, 0, 1)
rock = np.clip(gaussian_filter(rock, 1.2) * 1.8 + np.clip((slope - 1.1) * 1.5, 0, 1), 0, 1)
def lerp(a, b, t): t = np.clip(t, 0, 1)[..., None]; return a * (1 - t) + b * t
C = lambda *c: np.array(c, float)
col = lerp(C(110, 124, 58), C(146, 146, 74), .5 + .22 * n1 + .12 * n2)                 # scrub and dry grass
col = lerp(col, C(118, 140, 64), np.clip(grass * .8 + inside * .3, 0, 1))              # mown grass, the allotments, the summit
col = lerp(col, C(72, 92, 44), forest * .75)                                           # shaded forest floor
col = lerp(col, C(132, 110, 80), np.clip((slope - .7) * 1.2, 0, .6))                  # earthy steep banks
col = lerp(col, C(150, 142, 128), np.clip(rockp * .8 + rock * (.85 + .1 * n3), 0, 1))  # granite of the quarry
# orthophoto colours inside the hole (desaturated a little towards the palette)
_ox = OX_ + (GX + CX + 160) * OS_; _oy = OY_ - (GY + CY - 232) * OS_
orto = np.stack([map_coordinates(ORTO[..., k], [_oy, _ox], order=1, mode='nearest') for k in range(3)], -1)
orto = orto * .75 + orto.mean(-1, keepdims=True) * .25 + 6
col = lerp(col, orto, hole * .85)
col = lerp(col, C(182, 178, 170) + 6 * n2[..., None], stad * .8)                     # paved ground of the stadium
col = lerp(col, C(150, 142, 128), np.clip(rockp * .8, 0, 1) * stad)                   # the rock amphitheatres at the ends
grain = np.random.default_rng(8).normal(0, 1, (TS, TS))
asph = C(88, 90, 93) + (4 * n2 + 3 * grain)[..., None]
col = lerp(col, asph, np.clip(park * 1.05, 0, 1))                                      # asphalt car parks
col = lerp(col, C(232, 232, 226), bays * .9)                                           # bay lines
_u = (GX - PC[0]) * _ca + (GY - PC[1]) * _sa
_str = (np.sin(_u / 5.25 * np.pi) > 0).astype(float)                                   # mowing stripes across the long axis
col = lerp(col, lerp(C(70, 138, 60), C(92, 160, 76), _str), pitch)                    # pitches
col = lerp(col, C(240, 242, 236), marks * pitch * .95)                                 # field markings
col = lerp(col, C(192, 186, 174) + (5 * grain)[..., None], pave * (1 - park_in))       # pavements (calçada)
col = lerp(col, C(140, 134, 124) + (14 * grain)[..., None], r_sett)                   # granite setts
col = lerp(col, asph, r_asph); col = lerp(col, C(112, 112, 110) + (6 * grain)[..., None], r_serv)
col = lerp(col, C(184, 178, 166), r_walk); col = lerp(col, C(164, 148, 116), r_earth)
col = lerp(col, C(120, 116, 110), bld_t * .8)                                         # under the buildings
zz2 = hz(GX[::4, ::4], GY[::4, ::4]); gy2, gx2 = np.gradient(zz2, mpp * 4)
nx, ny, nz = -gx2, gy2, np.ones_like(gx2); nn = np.sqrt(nx * nx + ny * ny + 1); L_ = np.array([-.55, .45, .7]); L_ /= np.linalg.norm(L_)
shade = (nx * L_[0] + ny * L_[1] + nz * L_[2]) / nn; shade = np.asarray(Image.fromarray(shade.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
col *= np.clip(.78 + .3 * (shade - shade.mean()) / (shade.std() + 1e-6) * .35 + .22, .7, 1.15)[..., None]
clump = gaussian_filter(np.random.default_rng(5).normal(0, 1, (TS, TS)), 4); clump /= clump.std()
col = lerp(col, col * C(.84, .9, .8), np.clip(clump * .35, 0, .6) * (1 - path) * (1 - rock) * (1 - park) * (1 - pitch) * (1 - hole))
spk = np.random.default_rng(6).random((TS, TS))
col = np.where(((spk > .9965) & (path < .3) & (park < .3) & (pitch < .3))[..., None], C(176, 170, 158), col)          # pebbles
col = np.where(((spk < .0012) & (forest < .3) & (path < .3) & (park < .3) & (hole < .3) & (pitch < .3))[..., None], C(232, 214, 96), col)   # gorse flowers
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
 "sipa": "Sereno, I.; Dordio, P. (1994). Castro Máximo / Monte de Castro, SIPA n.º 1721 (DGPC): cota máxima 198,2 m; a ação das pedreiras desfigurou em grande medida o povoado; Carlos Teixeira (1935) referiu fossos do lado da cidade, possivelmente duas linhas de muralha e casas circulares de pedra, que hoje não se identificam; Russell Cortez (1953-54); sondagens da U. Minho (1976-78): um muro com paramento externo aparelhado e um piso de argila batida; ocupação mais intensa entre meados do séc. I a.C. e meados do séc. I d.C. IIP (Decreto n.º 29/84) e ZEP (Portaria n.º 281/85).",
 "morais": "Morais, R. (2020). Transition from the Pre-Roman World to the Roman World in the Northwest of the Iberian Peninsula: the example of Bracara Augusta. Repositório Aberto da U. Porto: Teixeira descreveu uma linha dupla de muralhas reforçada por fossos a sul; escavação parcial do Gabinete de Arqueologia da Câmara de Braga (Armandino Cunha) no local do estádio, com unidades habitacionais e áreas de circulação organizadas por vários cruzamentos de ruas; ≈ 2 km de Bracara Augusta; abandono talvez no fim do séc. I a.C.",
 "rocha": "Rocha, D. (2017). O Castro Máximo: contributo para o estudo do povoamento proto-histórico da região de Braga. Dissertação de mestrado, U. Minho (resumo): escavação de 2001 antes do novo estádio, pelo Gabinete de Arqueologia da Câmara com a Unidade de Arqueologia da U. Minho; abandono entre o séc. I a.C. e o início do séc. I d.C. O texto e as plantas não puderam ser consultados.",
 "blog": "Avenida Central (blogue, 2008). O Castro Máximo: o que resta (a acrópole) ocupa o topo do monte primitivo, com acesso pela Av. Artur Soares; três linhas de muralha e fossos do lado da cidade; Albano Belino (fim do séc. XIX), Teixeira (1935-36), Cortez (anos 1950), sondagens da U. Minho (1977-78) e escavação de 2001.",
 "tese": "Pinto, T. — Castros do Noroeste de Portugal (tese de doutoramento, Univ. de Santiago de Compostela); visitas em 2022 e 2025: nenhuma ruína visível; as casas circulares apareceram na construção do estádio, sobretudo nos estacionamentos da bancada poente, e foram estudadas numa escavação de emergência de cinco meses; duas lareiras no Museu D. Diogo de Sousa; parte da zona vedada pela ravina da pedreira; evento Nómadas num estacionamento dentro da zona de proteção.",
 "wiki": "Estádio Municipal de Braga, Wikipédia em português (ligada no OpenStreetMap): projeto do arquiteto Eduardo Souto de Moura e do engenheiro Rui Furtado; 30 286 lugares; apenas duas bancadas laterais, com os topos formados pelos anfiteatros rupestres da encosta do monte; a cobertura inspira-se nas pontes incas; alcunha «A Pedreira».",
 "osm": "OpenStreetMap (extrato de 2026): estádio e relvado, parques de estacionamento, rocha nua da pedreira (escarpas de 15 e 30 m), ruas e caminhos, Estabelecimento Prisional, ponto «Castro Máximo».",
 "orto": "Ortofotografia enviada pelo Tiago (2026-11), ajustada aos dois relvados do OpenStreetMap (≈ 0,93 m por píxel): telhados das casas e cores do terreno na zona sem LiDAR.",
 "photo": "Fotografia enviada pelo Tiago (2026-11): o alto do monte com erva e um pequeno monte de terra, com a cidade de Braga ao fundo.",
 "lidar": "DGT — LiDAR 2025, bloco 175511: nuvem de pontos classificada (LO-175511-07-2025, ≈ 8,6 pontos de solo por m²) e MDT/MDS de 50 cm. Terreno de 25 cm interpolado dos pontos de solo; edifícios pela classe 6 e pelo MDS; árvores com a altura real do modelo de copas. Sem pontos num círculo de ≈ 190 m de raio à volta do Estabelecimento Prisional: aí o relevo vem dos AWS Terrain Tiles (SRTM, ≈ 30 m), ajustado à borda do LiDAR, e é aproximado. Relevo sem exagero.",
}
os.makedirs('app/dio', exist_ok=True)
for o in sc.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.abspath(f'app/dio/{SID}.glb'), export_format='GLB', export_apply=True, export_yup=True,
                          export_image_format='JPEG', export_jpeg_quality=86, export_materials='EXPORT', use_selection=False, export_extras=True,
                          export_draco_mesh_compression_enable=False)
json.dump({'cat': CAT, 'sources': SOURCES, 'R': R, 'ex': EX, 'h0': H0, 'cx': CX, 'cz': -CY, 'trees': TREES, 'types': TYPES, 'pal': {k: [list(c) for c in v] for k, v in PAL.items()}}, open(f'app/dio/{SID}.json', 'w'))
print('ok', os.path.getsize(f'app/dio/{SID}.glb'))
