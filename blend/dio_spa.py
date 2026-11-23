# Builds a castillos-style disc diorama of one castro in Blender (bpy) and exports a GLB for three.js.
# Castro de São Paio (Labruge, Vila do Conde). Usage: /opt/bvenv/bin/python blend/dio_spa.py vila-do-conde-castro-de-sao-paio
# No published plan. Terrain: DGT LiDAR 2025, point cloud LO-150480 on the land side (25 cm) and the 50 cm MDT/MDS of block
# 149480 on the castro itself (lidar/spa_laz.py -> lidar/spa_*25.npy). The east talude is traced on the LiDAR
# (lidar/spa_lines.py -> blend/spa_lines.json). Excavation areas, the round structure, paths, beach and rocks are read on the
# orthophoto (Google satellite, aligned on the LiDAR by lidar/spa_orto.py, ≈ 1 m). Buildings: roofs at the MDS height.
# Local frame: x east, y north (Blender Z up), metres, origin = disc centre.
import sys, json, math, os
import numpy as np
import bpy, bmesh
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter, map_coordinates, label, binary_opening, binary_closing, uniform_filter, median_filter, binary_dilation

SID = sys.argv[-1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
LN = json.load(open('blend/spa_lines.json'))
rng = np.random.default_rng(17)
LB = json.load(open('lidar/spa_box.json'))
X0L, Y0L = LB['xc'], LB['yc']                    # local frame origin (PT-TM06): box centre
# ---------- disc: holds the castro, the chapel, the interpretation centre, the rocks and the Praia dos Castros
CX, CY, R = -15.0, -12.0, 100.0
def loc(p): p = np.asarray(p, float); return np.stack([p[..., 0] - CX, p[..., 1] - CY], -1)
# ---------- terrain: LiDAR ground (25 cm TIN on the land side, 50 cm MDT on the castro), lightly smoothed; sea set flat
_dtm = np.load('lidar/spa_dtm25.npy').astype(np.float32)
DTM = gaussian_filter(_dtm, .8)
_dsm = np.load('lidar/spa_dsm25.npy').astype(np.float32)
CHM = _dsm - _dtm
SEA = 0.3                                          # water level drawn (the LiDAR returns over the sea sit at 0-0.3 m)
def _rc(x, y):  # Blender xy -> grid row/col
    lx = np.asarray(x, float) + CX; ly = np.asarray(y, float) + CY
    return (LB['y1'] - (Y0L + ly)) / LB['cs'] - .5, (X0L + lx - LB['x0']) / LB['cs'] - .5
def _samp(A, x, y, order=1):
    r, c = _rc(x, y); return map_coordinates(A, [np.atleast_1d(r).ravel(), np.atleast_1d(c).ravel()], order=order, mode='nearest').reshape(np.shape(r))
def hraw(x, y): return _samp(DTM, x, y)
H0 = float(hraw(0, 0)); EX = 1.0
# orthophoto (aligned on the LiDAR, lidar/spa_orto.py) on the box grid: z20 where captured, z19 elsewhere; surface classes
sys.path.insert(0, os.path.join(ROOT, 'blend')); import spa_tex as TX
_o19 = np.asarray(Image.open('lidar/spa/orto_z19.png').convert('RGB'), float)
_o20 = np.asarray(Image.open('lidar/spa/orto_z20.png').convert('RGB'), float)
ORT = np.where((_o20.sum(2) > 30)[..., None], _o20, _o19)
CLS = TX.classify(ORT, _dtm, SEA, _dtm - gaussian_filter(_dtm, 12))
# waves and foam: the LiDAR puts returns on the breaking waves 0.3-1.6 m above the sea; they are taken down under the water
# (otherwise the sea shows as white and blue blotches stretched over the rocks)
_wat = gaussian_filter(CLS['WATER'].astype(np.float32), 1.5)
# shore rocks: the MDT of the castro block (50 cm) rounds off the granite outcrops, and part of each boulder is left in the MDS as
# non-ground; on the rock class the surface takes back up to 1.2 m of MDS − MDT (low vegetation does not grow on these rocks)
_rkw = gaussian_filter((CLS['ROCK'] & (_dtm < 10)).astype(np.float32), 1.0)
DTM = np.where(_rkw > .5, gaussian_filter(_dtm, .4), DTM) + _rkw * np.clip(gaussian_filter(CHM, .6), 0, 1.2)   # less smoothing on the rocks
# waves and foam taken down under the water on the grid itself, with a ramp of ≈ 1.5 m into the rocks next to them (a drop of up to
# 2 m from one 25 cm cell to the next made a saw-tooth edge once the terrain was meshed and simplified)
_W = CLS['WATER']
_T = np.where(_W, SEA - .45, DTM)
from scipy.ndimage import distance_transform_edt as _edt0
_near = (_edt0(~_W) * LB['cs'] < 1.5) & ~_W
DTM = np.where(_W, np.minimum(DTM, SEA - .45), np.where(_near, np.minimum(DTM, gaussian_filter(_T, 2.0)), DTM)).astype(np.float32)
# cuts in the ground model: the trench of E1 (local box coordinates, measured on the orthophoto), 0.45 m deep
def inset(poly, d):   # convex quadrilateral moved inwards by d metres (offset of each edge)
    poly = np.asarray(poly, float); n_ = len(poly); out = []
    _a2 = .5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1]); sgn = 1 if _a2 > 0 else -1
    L = []
    for i in range(n_):
        a, b = poly[i], poly[(i + 1) % n_]; t = (b - a) / np.linalg.norm(b - a); nn = np.array([-t[1], t[0]]) * sgn
        L.append((a + nn * d, t))
    for i in range(n_):
        (p1, t1), (p2, t2) = L[i - 1], L[i]
        A = np.array([t1, -t2]).T; s = np.linalg.solve(A, p2 - p1); out.append(p1 + t1 * s[0])
    return np.array(out)
E1_BOX = [(-29.75, -31.7), (-20.1, -30.75), (-19.6, -34.2), (-29.75, -35.1)]
CUTS = []                      # (the E1 trench is a hole in the terrain mesh, see below)
E1_HOLE = inset(loc(E1_BOX), .12)
def _cut_depth(x, y):
    d = np.zeros(np.shape(x))
    for poly, depth in CUTS:
        from matplotlib.path import Path as _P
        P = np.c_[np.ravel(x), np.ravel(y)]; ins = _P(poly).contains_points(P).reshape(np.shape(x)); d = np.where(ins, depth, d)
    return d
def hz(x, y):
    h = hraw(x, y)
    return (np.maximum(h, SEA - 1.2) - _cut_depth(x, y) - H0) * EX
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
Image.new('RGB', (64, 64), (120, 130, 70)).save('blend/spa/ground_raw.jpg')
# ---------- terrain disc (polar grid, ≈ 0.3 m radial step)
NR, NA = 330, 2400
rr = np.linspace(0, R, NR + 1)[1:]; aa = np.linspace(0, 2 * np.pi, NA, endpoint=False)
X = np.concatenate([[0], (rr[:, None] * np.cos(aa)[None]).ravel()]); Y = np.concatenate([[0], (rr[:, None] * np.sin(aa)[None]).ravel()])
Z = hz(X, Y); V = np.stack([X, Y, Z], 1); F = []
for a in range(NA): F.append((0, 1 + a, 1 + (a + 1) % NA))
for r in range(NR - 1):
    o0, o1 = 1 + r * NA, 1 + (r + 1) * NA
    for a in range(NA): b = (a + 1) % NA; F.append((o0 + a, o1 + a, o1 + b, o0 + b))
# The ground texture is split in four tiles (one per quadrant, 2048 px each after tools/gltf/lighten.mjs = 5 cm per pixel instead of
# 10 cm for one texture over the whole disc); faces steeper than 55° (rock faces of the shore, banks) take a granite texture with
# box-projected UVs instead of the orthophoto stretched down the face.
QM = 1.0; TW = R + 2 * QM
QX0 = [-R - QM, -QM, -R - QM, -QM]; QY1 = [R + QM, R + QM, QM, QM]          # west and north edge of each tile: 0 NW, 1 NE, 2 SW, 3 SE
Image.new('RGB', (64, 64), (120, 130, 70)).save('blend/spa/ground_q.jpg')
GQ = [img_mat(f'ground{k}', 'blend/spa/ground_q.jpg') for k in range(4)]
gmat, gtex = GQ[0]
Image.fromarray(TX.granite_tile()).save('blend/spa/granite.jpg', quality=88)
rockf_m, _ = img_mat('rockface', 'blend/spa/granite.jpg', .9)
from matplotlib.path import Path as _MPh
me = bpy.data.meshes.new('terrain'); me.from_pydata([tuple(v) for v in V], [], [tuple(f) for f in F]); me.validate(); me.update()
# the E1 trench: the terrain is cut exactly along its outline (bisected by the four vertical planes of its sides) and the faces inside
# removed; the trench has its own floor and boards
_bm = bmesh.new(); _bm.from_mesh(me)
_c0 = E1_HOLE.mean(0); _rad = np.max(np.linalg.norm(E1_HOLE - _c0, axis=1)) + 1.0
for i in range(len(E1_HOLE)):
    a, b = E1_HOLE[i], E1_HOLE[(i + 1) % len(E1_HOLE)]; t = (b - a) / np.linalg.norm(b - a)
    reg = [f for f in _bm.faces if np.hypot(f.calc_center_median().x - _c0[0], f.calc_center_median().y - _c0[1]) < _rad]
    geom = list({e for f in reg for e in f.edges}) + reg + list({v for f in reg for v in f.verts})
    bmesh.ops.bisect_plane(_bm, geom=geom, plane_co=(a[0], a[1], 0), plane_no=(-t[1], t[0], 0))
_poly = _MPh(inset(E1_HOLE, -1e-3))
_del = [f for f in _bm.faces if np.hypot(f.calc_center_median().x - _c0[0], f.calc_center_median().y - _c0[1]) < _rad and _poly.contains_point((f.calc_center_median().x, f.calc_center_median().y))]
bmesh.ops.delete(_bm, geom=_del, context='FACES'); _bm.to_mesh(me); _bm.free(); me.update()
for m_ in [g[0] for g in GQ] + [rockf_m]: me.materials.append(m_)
FN = np.zeros((len(me.polygons), 3)); FC = np.zeros((len(me.polygons), 3))
me.polygons.foreach_get('normal', FN.ravel()); me.polygons.foreach_get('center', FC.ravel())
_rockd = binary_dilation(CLS['ROCK'] | CLS['SEA'], iterations=6).astype(np.float32)
_gy, _gx = np.gradient(gaussian_filter(DTM, 1.5), LB['cs']); _slope = np.degrees(np.arctan(np.hypot(_gx, _gy))).astype(np.float32)
# steepness from the smoothed slope map at the face centre, not from each face's normal: per-face normals flip around the threshold
# along a rock edge and made a saw-tooth of granite and ground triangles
steep = np.zeros(len(FC), bool) & (_samp(_slope, FC[:, 0], FC[:, 1]) > 52)   # granite tile on the rock faces turned off (seams);  & (FN[:, 2] < math.cos(math.radians(40))) & (_samp(_rockd, FC[:, 0], FC[:, 1]) > .5)   # granite only on the shore rocks, not on the earth banks
mi = np.where(steep, 4, (FC[:, 0] >= 0).astype(int) + 2 * (FC[:, 1] < 0).astype(int))
me.polygons.foreach_set('material_index', mi.astype(np.int32))
uvl = me.uv_layers.new(name='UVMap')
LV = np.zeros(len(me.loops), int); me.loops.foreach_get('vertex_index', LV)
LP = np.repeat(np.arange(len(me.polygons)), [len(p.vertices) for p in me.polygons])
Vn = np.zeros((len(me.vertices), 3)); me.vertices.foreach_get('co', Vn.ravel()); lx, ly, lz = Vn[LV, 0], Vn[LV, 1], Vn[LV, 2]; q = mi[LP]
qq = np.clip(q, 0, 3)
U = (lx - np.array(QX0)[qq]) / TW; Vv = 1 - (np.array(QY1)[qq] - ly) / TW
xdom = np.abs(FN[LP, 0]) > np.abs(FN[LP, 1])
U = np.where(q == 4, np.where(xdom, ly, lx) / 2.5, U); Vv = np.where(q == 4, lz / 2.5, Vv)
uvl.data.foreach_set('uv', np.c_[U, Vv].ravel())
terrain = new_obj('terrain', me)
for p in terrain.data.polygons: p.use_smooth = True
print('terrain faces', len(mi), 'steep', int(steep.sum()))
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
Image.fromarray(np.clip(st[::-1] + rng.normal(0, 6, st.shape), 0, 255).astype(np.uint8)).resize((64, 256)).save('blend/spa/strata.jpg', quality=90)
smat, _ = img_mat('earth', 'blend/spa/strata.jpg')
skirt = new_obj('skirt', mesh_from('skirt', SV, SF, SUV), smat)# ---------- sea: a flat water surface at the level of the LiDAR returns over the water, clipped to the disc
# the water carries a texture: deeper blue-green offshore, lighter over the shallow rock shelves, a white foam band along the rocks
# (where the surf breaks in the photographs and the orthophoto) broken up with noise; nothing of it is measured, it is look only
_WG = 2048; _wm = 2 * R / _WG; _wj, _wi = np.mgrid[0:_WG, 0:_WG]; _wx = (_wi + .5) * _wm - R; _wy = R - (_wj + .5) * _wm
_wh = _samp(_dtm.astype(np.float32), _wx, _wy)
_land = (_wh > SEA + .05) & ~(_samp(_wat, _wx, _wy) > .5)
from scipy.ndimage import distance_transform_edt as _edt
_wd = _edt(~_land) * _wm
_wrng = np.random.default_rng(7)
_wn1 = TX._noise((_WG, _WG), 3, _wrng); _wn2 = TX._noise((_WG, _WG), 12, _wrng); _wn3 = TX._noise((_WG, _WG), (1.2, 6), _wrng)
_dep = np.clip((SEA - _wh) / 2.5, 0, 1)
_wc = np.array([62, 128, 126.]) * (1 - _dep[..., None]) + np.array([24, 74, 90.]) * _dep[..., None]
_wc *= (1 + .05 * _wn2[..., None])
_fo = np.exp(-_wd / .9) * np.clip(.6 + .35 * _wn1 + .25 * _wn2, 0, 1) + np.exp(-_wd / 2.5) * np.clip(_wn2 - .8, 0, 1) * .35
_fo = np.clip(_fo, 0, 1)[..., None]
_wc = _wc * (1 - _fo) + np.array([232, 238, 234.]) * _fo
Image.fromarray(np.clip(_wc, 0, 255).astype(np.uint8)).save('blend/spa/water.jpg', quality=88)
del _wj, _wi, _wx, _wy, _wh, _wd, _wn1, _wn2, _wn3, _dep, _wc, _fo, _land
water_m, _wt = img_mat('water', 'blend/spa/water.jpg', .25)
_wb = water_m.node_tree.nodes['Principled BSDF']
_wb.inputs['Alpha'].default_value = .82; water_m.blend_method = 'BLEND' if hasattr(water_m, 'blend_method') else None
NWA = 360; wa = np.linspace(0, 2 * np.pi, NWA, endpoint=False); wz = (SEA - H0) * EX
WV = [(0, 0, wz)] + [(math.cos(a) * (R - .02), math.sin(a) * (R - .02), wz) for a in wa]
WF = [(0, 1 + k, 1 + (k + 1) % NWA) for k in range(NWA)]
WVs = [(math.cos(a) * (R - .03), math.sin(a) * (R - .03), z) for z in (wz, wz - 1.6) for a in wa]   # side band: inside the earth skirt on land, visible over the sea
WFs = [(k, (k + 1) % NWA, NWA + (k + 1) % NWA, NWA + k) for k in range(NWA)]
sea_o = new_obj('sea', mesh_from('sea', WV + WVs, WF + [tuple(i + len(WV) for i in f) for f in WFs], [(v[0] / (2 * R) + .5, v[1] / (2 * R) + .5) for v in WV + WVs]), water_m)
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
Image.fromarray(np.clip(_st * [.74, .72, .64] + [6, 6, 2], 0, 255).astype(np.uint8)).save('blend/spa/rubble.jpg', quality=88)
rub_m, _ = img_mat('rubble', 'blend/spa/rubble.jpg', .95)
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
# ---------- structures: one object per structure, mode A (current state) and B (reconstitution)
CAT = []
def put(sid, name, mat, geo, mode, ev):
    A = Acc()
    for g in geo: A.add(g)
    o = A.obj(f'{mode}-{sid}', mat)
    if o: o['sid'] = sid; o['mode'] = mode; o['ev'] = ev
    return o
def item(**k): CAT.append(k)
def line(k): return loc(np.array(LN[k]['pts']))
_st = np.asarray(Image.open('blend/stone.jpg').convert('RGB'), float)
Image.fromarray(np.clip(_st * [.5, .56, .42] + [8, 12, 4], 0, 255).astype(np.uint8)).save('blend/spa/rubble.jpg', quality=88)
rub_m, _ = img_mat('rubble', 'blend/spa/rubble.jpg', .95)
def bank_drop(pts, half=7.0):   # median height drop (m) across the line in the LiDAR ground model
    p = dense(pts, 2); d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9; nr = np.stack([-d[:, 1], d[:, 0]], 1)
    o = np.linspace(-half, half, 11); pr = hraw(p[:, 0, None] + nr[:, 0, None] * o, p[:, 1, None] + nr[:, 1, None] * o)
    return float(np.median(pr.max(1) - pr.min(1)))
def bank_rise(pts):     # how far the crest stands above the interior 6-10 m inside (the bank left by the wall)
    p = dense(pts, 2); d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9; nr = np.stack([-d[:, 1], d[:, 0]], 1)
    c = hraw(p[:, 0], p[:, 1]); i_ = np.median([hraw(p[:, 0] + nr[:, 0] * o, p[:, 1] + nr[:, 1] * o) for o in (6, 8, 10)], 0)
    return float(np.median(c - i_))
# T1: the east talude. Walking along T1 (north-west to south-east) the inside is on the right; nr in rampart() points left = outside.
T1 = line('T1'); T1_DROP = bank_drop(T1); T1_RISE = bank_rise(T1[::-1])
_pT = dense(T1, 1.0); _dT = np.gradient(_pT, axis=0); _dT /= np.linalg.norm(_dT, axis=1, keepdims=True); _nT = np.stack([-_dT[:, 1], _dT[:, 0]], 1)
_rise = hraw(*_pT.T) - np.median([hraw(*(_pT - _nT * o).T) for o in (6, 8, 10)], 0)      # inside = right of the line
_on = gaussian_filter1d(_rise, 2) > .3
_runs = []; _i = 0
while _i < len(_on):
    if _on[_i]:
        _j = _i
        while _j < len(_on) and _on[_j]: _j += 1
        if _j - _i >= 3: _runs.append(_pT[_i:_j])
        _i = _j
    else: _i += 1
T1_STONE = sum(len(r_) - 1 for r_ in _runs)
put('T1', 'Talude e muralha nascente', rub_m, [rampart(r_, 1.2, -.07, .09, taper=.4) for r_ in _runs], 'A', 'conf')
put('T1', 'Talude e muralha nascente', stone_m, [rampart(T1, 2.5, 1.6, .1, taper=.92)], 'B', 'hip')
item(id='T1', name='Talude coroado por muralha, a nascente', kind='Muralha', phase='Idade do Ferro', ev='conf', evB='hip',
     dims=f'comprimento ≈ {LN["T1"]["len"]:.0f} m · talude com ≈ {T1_DROP:.1f} m de desnível (LiDAR) · crista ≈ {max(T1_RISE, 0):.1f} m acima do interior · reconstituição: muro com 2,5 m de largura e 1,6 m acima da crista (hipotético)',
     note=f'«Talude coroado por uma muralha de pedra, da qual apenas resta o seu alicerce», bem demarcado sobretudo na vertente Este (Almeida et al. 2012). No LiDAR de 2025 é o rebordo nascente do povoado: uma crista ligeiramente elevada sobre o interior e um talude de cerca de {T1_DROP:.1f} m para os campos. Traçado no modelo do terreno e ajustado à crista. No estado atual o talude é de terra e erva: só se mostra pedra nos {T1_STONE:.0f} m onde a crista sobressai mais de 0,3 m do interior (restos do alicerce, por confirmar no terreno). Largura e altura da muralha não publicadas: valores da reconstituição hipotéticos.',
     src=['alm', 'pa', 'lidar'])
print('T1 drop', round(T1_DROP, 2), 'rise', round(T1_RISE, 2))
# excavation areas protected under gravel, measured on the orthophoto (local box coordinates -> Blender)
E1 = loc([(-29.75, -31.7), (-20.1, -30.75), (-19.6, -34.2), (-29.75, -35.1)])     # «Ruínas de Habitação» (round house, lajeado)
E2 = loc([(-34.2, 4.6), (-27.6, 4.75), (-26.7, 1.5), (-34.2, .25)])              # house complex around a yard (panel «Family house»)
C1 = loc([-30.6, 26.6]); C1_RO, C1_W = 2.6, .5                                    # round structure by the interpretation centre
gravel_m = col_mat('gravel', (186, 178, 160), .95)
def pad(poly, dz=.08):
    z = float(np.median(hz(*poly.T))) + dz; V = [(x, y, z) for x, y in poly]
    return V, [tuple(range(len(poly)))], [(0, 0)] * len(V)
def poly_walls(poly, w, h): return sweep(np.vstack([poly, poly[:1]]), w, h, .05, .25, closed=False)
cyl = lambda c, rad, n=32: np.array([(c[0] + math.cos(a) * rad, c[1] + math.sin(a) * rad) for a in np.linspace(0, 2 * np.pi, n + 1)[:-1]])
def area(p): return .5 * abs(np.dot(p[:, 0], np.roll(p[:, 1], 1)) - np.dot(p[:, 1], np.roll(p[:, 0], 1)))
def sides(p): return [float(np.linalg.norm(p[(i + 1) % len(p)] - p[i])) for i in range(len(p))]
# C1: round structure by the interpretation centre, visible on the orthophoto (unidentified in the sources read)
put('C1', 'Estrutura circular', stone_m, [sweep(cyl(C1, C1_RO - C1_W / 2), C1_W, .45, .05, .3, closed=True)], 'AB', 'conf')
item(id='C1', name='Estrutura circular junto ao Centro Interpretativo', kind='Estrutura', phase='—', ev='conf', evB='conf',
     dims=f'diâmetro exterior ≈ {2 * C1_RO:.1f} m · parede ≈ {C1_W:.1f} m (ortofotografia)', note='Estrutura circular de pedra à vista, entre o parque do Centro Interpretativo e o caminho para a capela. Não foi encontrada nas fontes consultadas: pode ser uma casa castreja consolidada ou uma estrutura moderna. Altura aproximada.', src=['orto'])
STRUCT_POLYS = [E1, E2, cyl(C1, C1_RO, 16)]
def boxv(cx, cy, a, lx, ly, z0, z1):
    ca, sa = math.cos(a), math.sin(a); P_ = [(-lx / 2, -ly / 2), (lx / 2, -ly / 2), (lx / 2, ly / 2), (-lx / 2, ly / 2)]
    Q = [(cx + u * ca - v * sa, cy + u * sa + v * ca) for u, v in P_]
    V = [(x, y, z0) for x, y in Q] + [(x, y, z1) for x, y in Q]
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return V, F, [(0, 0), (1, 0), (1, 1), (0, 1)] * 2
def gable(cx, cy, a, lx, ly, z0, h, ov=.35):   # ridge along local u
    ca, sa = math.cos(a), math.sin(a); T_ = lambda u, v, z: (cx + u * ca - v * sa, cy + u * sa + v * ca, z)
    hx, hy = lx / 2 + ov, ly / 2 + ov; dz = h * ov / (ly / 2)
    V = [T_(-hx, -hy, z0 - dz), T_(hx, -hy, z0 - dz), T_(hx, hy, z0 - dz), T_(-hx, hy, z0 - dz), T_(-hx, 0, z0 + h), T_(hx, 0, z0 + h)]
    F = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5)]
    return V, F, [(0, 0)] * 6
def gable_wall(cx, cy, a, lx, ly, z0, h):   # triangular end walls under the gable
    ca, sa = math.cos(a), math.sin(a); T_ = lambda u, v, z: (cx + u * ca - v * sa, cy + u * sa + v * ca, z)
    V = [T_(-lx / 2, -ly / 2, z0), T_(-lx / 2, ly / 2, z0), T_(-lx / 2, 0, z0 + h), T_(lx / 2, ly / 2, z0), T_(lx / 2, -ly / 2, z0), T_(lx / 2, 0, z0 + h)]
    return V, [(0, 1, 2), (3, 4, 5)], [(0, 0)] * 6
# ---------- excavation areas and the visitor route (current state), read on the photographs of 2025 and the orthophoto
def _T(cx, cy, a):
    ca, sa = math.cos(a), math.sin(a); return lambda u, v, z: (cx + u * ca - v * sa, cy + u * sa + v * ca, z)
Image.fromarray(TX.gravel()).save('blend/spa/gravel.jpg', quality=88); gravel_m, _ = img_mat('gravel', 'blend/spa/gravel.jpg', .95)
Image.fromarray(TX.drystone()).save('blend/spa/drystone.jpg', quality=88); dry_m, _ = img_mat('drystone', 'blend/spa/drystone.jpg', .9)
Image.fromarray(TX.planks(base=(146, 136, 120))).save('blend/spa/deck.jpg', quality=88); deck_m, _ = img_mat('deck', 'blend/spa/deck.jpg', .85)
Image.fromarray(TX.planks(m=1.0, w=.2, base=(78, 56, 40), gap=(40, 30, 22))).save('blend/spa/taipal.jpg', quality=88); taipal_m, _ = img_mat('taipal', 'blend/spa/taipal.jpg', .9)
log_m = col_mat('log', (112, 82, 56), .9); rope_m = col_mat('rope', (196, 176, 136), .9); corten_m = col_mat('corten', (122, 62, 30), .7)
_pan = np.full((140, 200, 3), 238, np.uint8); _pan[:34, 70:] = (70, 110, 200); _pan[12:22, 6:60] = (90, 120, 200)
for k in range(9): _pan[46 + k * 9:50 + k * 9, 8:62] = 120
_pan[60:120, 80:180] = 205; _pan[:, :3] = _pan[:, -3:] = _pan[:3] = _pan[-3:] = 150
Image.fromarray(_pan).save('blend/spa/panel.png'); panel_m, _ = img_mat('panel', 'blend/spa/panel.png', .5)
from matplotlib.path import Path as _MP2
def draped(poly, dz=.05, cell=.25):   # a surface that follows the ground model (and the trench cut) inside a polygon
    poly = np.asarray(poly); x0, y0 = poly.min(0); x1, y1 = poly.max(0)
    xs = np.arange(x0, x1 + cell, cell); ys = np.arange(y0, y1 + cell, cell); GXd, GYd = np.meshgrid(xs, ys)
    Z = hz(GXd, GYd) + dz; ins = _MP2(poly).contains_points(np.c_[GXd.ravel(), GYd.ravel()]).reshape(GXd.shape)
    V = [(float(GXd.flat[i]), float(GYd.flat[i]), float(Z.flat[i])) for i in range(GXd.size)]; F = []
    ny_, nx_ = GXd.shape
    for i in range(ny_ - 1):
        for j in range(nx_ - 1):
            if ins[i, j] and ins[i + 1, j] and ins[i, j + 1] and ins[i + 1, j + 1]: F.append((i * nx_ + j, i * nx_ + j + 1, (i + 1) * nx_ + j + 1, (i + 1) * nx_ + j))
    UV = [(v[0] / 2, v[1] / 2) for v in V]; return V, F, UV
def tube(a, b, r, n=8):   # log or rope between two 3D points
    a = np.asarray(a, float); b_ = np.asarray(b, float); ax = b_ - a; L = np.linalg.norm(ax); ax /= L
    u = np.cross(ax, [0, 0, 1] if abs(ax[2]) < .9 else [1, 0, 0]); u /= np.linalg.norm(u); w_ = np.cross(ax, u); V = []
    for k in range(n):
        t = k / n * 2 * np.pi; d = u * math.cos(t) + w_ * math.sin(t); V += [tuple(a + d * r), tuple(b_ + d * r)]
    F = [(2 * k, 2 * ((k + 1) % n), 2 * ((k + 1) % n) + 1, 2 * k + 1) for k in range(n)] + [tuple(2 * k for k in range(n))[::-1], tuple(2 * k + 1 for k in range(n))]
    return V, F, [(0, 0)] * len(V)
def ground_nocut(x, y): return (np.maximum(hraw(x, y), SEA - 1.2) - H0) * EX
def outward(poly, d):
    return inset(poly, -d)
def fence_posts(poly, off, step, h, r):
    ring = dense(np.vstack([outward(poly, off), outward(poly, off)[:1]]), step)[:-1]; P = []
    for p in ring:
        z = float(ground_nocut(*p)); P.append((p[0], p[1], z))
    return P
E1C = inset(E1, .12)
# E1 «Ruínas de Habitação»: a long trench (≈ 9.9 × 3.4 m) with a gravel floor about 0.45 m down, its sides lined with dark wooden
# boards (taipais), a fence of logs on posts and the panel at its west end (photograph of 2025 taken from the panel looking east)
def draped_nc(poly, dz, cell=.25):     # like draped() on the uncut ground model
    poly = np.asarray(poly); x0, y0 = poly.min(0) - cell; x1, y1 = poly.max(0) + cell
    xs = np.arange(x0, x1 + cell, cell); ys = np.arange(y0, y1 + cell, cell); GXd, GYd = np.meshgrid(xs, ys)
    Z = gaussian_filter(ground_nocut(GXd, GYd), 2) + dz; V = [(float(GXd.flat[i]), float(GYd.flat[i]), float(Z.flat[i])) for i in range(GXd.size)]; F = []
    ny_, nx_ = GXd.shape
    for i in range(ny_ - 1):
        for j in range(nx_ - 1):
            if _MP2(poly).contains_point(((GXd[i, j] + GXd[i, j + 1]) / 2, (GYd[i, j] + GYd[i + 1, j]) / 2)): F.append((i * nx_ + j, i * nx_ + j + 1, (i + 1) * nx_ + j + 1, (i + 1) * nx_ + j))
    return V, F, [(v[0] / 2, v[1] / 2) for v in V]
_rv = []
ring = inset(E1C, .02); ring = dense(np.vstack([ring, ring[:1]]), .5)
_zt = gaussian_filter1d(np.array([float(ground_nocut(*(q_ + (q_ - E1C.mean(0)) / np.linalg.norm(q_ - E1C.mean(0)) * .65))) for q_ in ring]) + .06, 1.5, mode='wrap')
# ground level around the trench as a plane (the LiDAR inside the trench already shows the dug floor): the gravel floor, the bottom of
# the boards and the reconstitution's cover all follow it, so no gap opens between them
_pl = np.linalg.lstsq(np.c_[ring, np.ones(len(ring))], _zt - .06, rcond=None)[0]
def e1_plane(x, y): return _pl[0] * np.asarray(x) + _pl[1] * np.asarray(y) + _pl[2]
def qgrid(Q, zf, nu=24, nv=8):   # bilinear grid over a quadrilateral: its border is exactly the quadrilateral
    Q = np.asarray(Q, float); V = []; F = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u, v = i / nu, j / nv; p = (1 - u) * (1 - v) * Q[0] + u * (1 - v) * Q[1] + u * v * Q[2] + (1 - u) * v * Q[3]
            V.append((float(p[0]), float(p[1]), float(zf(*p))))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; F.append((a, a + 1, a + nu + 2, a + nu + 1))
    return V, F, [(v[0] / 2, v[1] / 2) for v in V]
put('E1', 'Ruínas de Habitação (área escavada protegida)', gravel_m, [qgrid(outward(E1C, .05), lambda x, y: e1_plane(x, y) - .45)], 'A', 'conf')
_s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))])
for i in range(len(ring) - 1):
    a, b = ring[i], ring[i + 1]; za, zb_ = _zt[i], _zt[i + 1]
    _ba, _bb = float(e1_plane(*a)) - .6, float(e1_plane(*b)) - .6
    _rv.append(([(a[0], a[1], min(_ba, za - .62)), (b[0], b[1], min(_bb, zb_ - .62)), (b[0], b[1], zb_), (a[0], a[1], za)], [(0, 1, 2, 3), (3, 2, 1, 0)], [(_s[i], 0), (_s[i + 1], 0), (_s[i + 1], .62), (_s[i], .62)]))
_fr = []                              # heavy timbers lying along the edge of the trench (photograph), 0.2 × 0.2 m: they also hide the edge of the hole
def beam(a, b, za, zb, w, h):        # square beam from a to b following the ground
    a = np.asarray(a, float); b = np.asarray(b, float); t = (b - a) / np.linalg.norm(b - a); n_ = np.array([-t[1], t[0]]) * w / 2; V = []
    for p, z in ((a, za), (b, zb)):
        V += [(p[0] - n_[0], p[1] - n_[1], z - .05), (p[0] + n_[0], p[1] + n_[1], z - .05), (p[0] + n_[0], p[1] + n_[1], z + h), (p[0] - n_[0], p[1] - n_[1], z + h)]
    F = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return V, F, [(0, 0), (1, 0), (1, .2), (0, .2)] * 2
_fo = outward(E1C, .1)
for i in range(4):
    a, b = _fo[i], _fo[(i + 1) % 4]; t = (b - a) / np.linalg.norm(b - a); a, b = a - t * .1, b + t * .1
    _fr.append(beam(a, b, max(float(ground_nocut(*a)), float(e1_plane(*a))), max(float(ground_nocut(*b)), float(e1_plane(*b))), .2, .2))
put('E1t', 'Taipais de madeira da vala', taipal_m, _rv + _fr, 'A', 'conf')
_fe = []; P = fence_posts(E1C, .75, 2.4, 1.0, .07)
for p in P: _fe.append(tube((p[0], p[1], p[2] - .2), (p[0], p[1], p[2] + 1.0), .07))
for a, b in zip(P, P[1:] + P[:1]): _fe.append(tube((a[0], a[1], a[2] + .92), (b[0], b[1], b[2] + .92), .065))
put('E1f', 'Vedação de troncos', log_m, _fe, 'A', 'conf')
_ax1 = E1[1] - E1[0]; _ax1 /= np.linalg.norm(_ax1); _w1 = (E1[0] + E1[3]) / 2 - _ax1 * 1.9     # panel 1.9 m west of the trench
def panel(p, facing, w=1.0, hgt=.7, tilt=35):
    a = math.atan2(facing[1], facing[0]); z = float(ground_nocut(*p)); T = _T(p[0], p[1], a)
    post = boxv(p[0], p[1], a, .12, .25, z - .2, z + .75)
    ti = math.radians(tilt); dx, dzz = hgt / 2 * math.cos(ti), hgt / 2 * math.sin(ti)
    V = [T(-dx, -w / 2, z + .85 - dzz), T(-dx, w / 2, z + .85 - dzz), T(dx, w / 2, z + .85 + dzz), T(dx, -w / 2, z + .85 + dzz)]
    return post, (V, [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)])
_p1 = panel(_w1, _ax1)
put('E1p', 'Painel «Ruínas de Habitação»', corten_m, [_p1[0]], 'A', 'conf'); put('E1pf', 'Painel «Ruínas de Habitação» (face)', panel_m, [_p1[1]], 'A', 'conf')
sd = sorted(sides(E1))
item(id='E1', name='Ruínas de Habitação (área escavada protegida)', kind='Área escavada', phase='atual', ev='conf', evB='conf',
     dims=f'≈ {np.mean(sd[2:]):.1f} × {np.mean(sd[:2]):.1f} m ({area(E1):.0f} m², medido na ortofotografia) · fundo ≈ 0,45 m abaixo do terreno (fotografia, aproximado)',
     note='Vala comprida coberta de gravilha, com as paredes forradas de taipais de madeira escura, uma vedação de troncos em postes e o painel interpretativo na ponta poente (fotografia de 2025, tirada do painel para nascente, com a capela ao fundo). Segundo o painel, a construção circular era o compartimento de uma habitação associada a um pátio e a um lajeado, com lareira central e piso de argila decorado com círculos; pertence ao nível mais recente do povoado (séculos II–I a.C.). Contorno na ortofotografia; profundidade e alturas da vedação aproximadas, lidas na fotografia. As paredes antigas estão tapadas e não se veem.',
     src=['foto', 'pan', 'hmdb', 'alm', 'orto'])
# E2: dry-stone wall around a gravel floor, logs stacked as steps along the north side, rope on wooden posts, boardwalk to the south,
# bench at the west end towards the sea (photograph of 2025 looking west)
E2I = inset(E2, .32)
put('E2', 'Conjunto habitacional (área escavada protegida)', gravel_m, [qgrid(E2I, lambda x, y: float(hz(x, y)) + .06, 16, 8)], 'A', 'conf')
put('E2w', 'Muro de pedra seca da área escavada', dry_m, [sweep(np.vstack([inset(E2, .1), inset(E2, .1)[:1]]), .5, .5, .04, .3, closed=False, top_taper=.9)], 'A', 'conf')
_n0, _n1 = E2I[0], E2I[1]; _tn = (_n1 - _n0) / np.linalg.norm(_n1 - _n0); _nin = np.array([_tn[1], -_tn[0]])      # north edge, inwards = south
if _MP2(E2I).contains_point((_n0 + _n1) / 2 + _nin * .5) is False: _nin = -_nin
_lg = []; zf = float(np.median(hz(*E2I.T))) + .04
for i in range(5):
    off = .22 + i * .24; z = zf + .11 + (4 - i) * .14
    a = _n0 + _tn * .25 + _nin * off; b = _n1 - _tn * .25 + _nin * off
    _lg.append(tube((a[0], a[1], z), (b[0], b[1], z), .11, 9))
put('E2l', 'Troncos em degrau do lado norte', log_m, _lg, 'A', 'conf')
_rp = []; P2 = fence_posts(E2, .9, 2.3, .85, .06)
for p in P2: _rp.append(tube((p[0], p[1], p[2] - .2), (p[0], p[1], p[2] + .85), .055))
put('E2f', 'Postes da vedação de corda', log_m, _rp, 'A', 'conf')
put('E2r', 'Corda da vedação', rope_m, [tube((a[0], a[1], a[2] + .7), (b[0], b[1], b[2] + .7), .025, 6) for a, b in zip(P2, P2[1:] + P2[:1])], 'A', 'conf')
_ax2 = E2[0] - E2[1]; _ax2 /= np.linalg.norm(_ax2); _bp = (E2[0] + E2[3]) / 2 + _ax2 * 5.0      # bench ≈ 5 m west of the wall
_ab = math.atan2(_ax2[1], _ax2[0]); _zb = float(ground_nocut(*_bp))
put('E2b', 'Banco de madeira', log_m, [boxv(_bp[0], _bp[1], _ab, .45, 1.8, _zb + .38, _zb + .46), boxv(_bp[0], _bp[1], _ab, .4, .12, _zb - .1, _zb + .38),
    boxv(_bp[0] + math.cos(_ab + 1.5708) * .75, _bp[1] + math.sin(_ab + 1.5708) * .75, _ab, .4, .12, _zb - .1, _zb + .38),
    boxv(_bp[0] - math.cos(_ab + 1.5708) * .75, _bp[1] - math.sin(_ab + 1.5708) * .75, _ab, .4, .12, _zb - .1, _zb + .38)], 'A', 'conf')
sd = sorted(sides(E2))
item(id='E2', name='Conjunto habitacional à volta de um pátio (área escavada protegida)', kind='Área escavada', phase='atual', ev='conf', evB='conf',
     dims=f'≈ {np.mean(sd[2:]):.1f} × {np.mean(sd[:2]):.1f} m ({area(E2):.0f} m², medido na ortofotografia) · muro ≈ 0,5 m (fotografia, aproximado)',
     note='Área escavada coberta de gravilha, dentro de um muro baixo de pedra seca; do lado norte, cinco troncos deitados em degrau seguram a terra; à volta, corda em postes de madeira; a sul passa o passadiço e a poente há um banco virado ao mar (fotografia de 2025). O painel descreve um conjunto de três ou quatro compartimentos à volta de um pequeno pátio, talvez fechado por um muro de pedra ou de madeira, do nível mais recente; no interior apareceram uma fíbula, uma mó manual redonda e uma lareira central decorada. Contorno na ortofotografia; medidas dos troncos, da vedação e posição do banco aproximadas. As paredes antigas estão tapadas e não se veem.',
     src=['foto', 'pan', 'alm', 'orto'])
for _n in list(bpy.data.objects.keys()):
    for _k in ('E1t', 'E1f', 'E1p', 'E1pf', 'E2w', 'E2l', 'E2f', 'E2r', 'E2b'):
        if _n.split('.')[0] == f'A-{_k}': bpy.data.objects[_n]['sid'] = _k[:2]
# boardwalks of weathered wood (orthophoto: planks across, 1.3 and 2 m wide; photograph of 2025 by E2)
BW = [(np.array([(-40.0, -3.5), (-24.6, -3.5)]), 1.3), (np.array([(-24.6, -3.5), (-21.3, 0.0), (-19.5, 5.0), (-18.8, 10.0), (-19.3, 15.0), (-20.5, 20.0), (-22.0, 25.0), (-23.0, 28.0)]), 2.0)]
def deck(pts, w, above=.18):
    p = dense(loc(pts), .5); n = len(p); d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True); nr = np.stack([-d[:, 1], d[:, 0]], 1)
    zs = np.array([max(float(ground_nocut(*(p[i] + nr[i] * o))) for o in (-w / 2, 0, w / 2)) for i in range(n)]) + above
    zs = gaussian_filter1d(zs, 1.5); s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    V = []; UV = []; F = []
    for i in range(n):
        L_, R_ = p[i] + nr[i] * w / 2, p[i] - nr[i] * w / 2; gl, gr = float(ground_nocut(*L_)) - .1, float(ground_nocut(*R_)) - .1
        V += [(L_[0], L_[1], gl), (L_[0], L_[1], zs[i]), (R_[0], R_[1], zs[i]), (R_[0], R_[1], gl)]
        UV += [(0, s[i] / 2), (.02, s[i] / 2), (w / 2, s[i] / 2), (w / 2 + .02, s[i] / 2)]
    for i in range(n - 1):
        for j in range(3): a = i * 4 + j; F.append((a + 1, a + 5, a + 4, a) if False else (a, a + 4, a + 5, a + 1))
    return V, F, UV
put('BW', 'Passadiço de madeira', deck_m, [deck(pts, w) for pts, w in BW], 'A', 'conf')
item(id='BW', name='Passadiço de madeira', kind='Equipamento de visita', phase='atual', ev='conf', evB='conf', dims='≈ 1,3 m e 2 m de largura (ortofotografia)',
     note='Passadiço de tábuas que liga o parque do Centro Interpretativo às áreas escavadas e à capela; traçado na ortofotografia, tábuas como na fotografia de 2025 junto a E2. Altura sobre o terreno aproximada.', src=['orto', 'foto'])
# reconstitution of the houses under the two areas: round stone houses with conical thatch (hypothetical diameters and positions);
# the later phase had «a vestibule whose shape recalls the claws of a crab» added to some of the round rooms (Almeida et al. 2012,
# p. 19), as drawn on the panel of E2; H1 follows the single round house of the E1 panel. Pátios with flagstones (panels).
th_m, _ = img_mat('thatch', 'blend/thatch.jpg', 1)
HD = 2 * (C1_RO - C1_W)          # 4.2 m: inner diameter of the round structure C1, the only one measurable on the site today
def ring_wall(c, r_in, w, z0, z1, door=None, dw=.9, n=40):
    """Round wall with a flat top (z1) and an optional door gap (door = angle of the door), world-scale UVs."""
    r_out = r_in + w; V = []; F = []; UV = []
    if door is None: angs = np.linspace(0, 2 * np.pi, n + 1)
    else:
        g = dw / 2 / (r_in + w / 2); angs = np.linspace(door + g, door + 2 * np.pi - g, n)
    for k, a in enumerate(angs):
        ca, sa = math.cos(a), math.sin(a); s = a * (r_in + w / 2)
        V += [(c[0] + ca * r_out, c[1] + sa * r_out, z0), (c[0] + ca * r_out, c[1] + sa * r_out, z1), (c[0] + ca * r_in, c[1] + sa * r_in, z1), (c[0] + ca * r_in, c[1] + sa * r_in, z0)]
        UV += [(s / 2.2, z0 / 2.2), (s / 2.2, z1 / 2.2), (s / 2.2, z1 / 2.2 + .2), (s / 2.2, z0 / 2.2)]
    for k in range(len(angs) - 1):
        a = 4 * k; F += [(a, a + 4, a + 5, a + 1), (a + 1, a + 5, a + 6, a + 2), (a + 2, a + 6, a + 7, a + 3)]
    if door is not None:
        a = 4 * (len(angs) - 1); F += [(0, 1, 2, 3)[::-1], (a, a + 1, a + 2, a + 3)]
    return V, F, UV
def house(sid, c, rad, label_, door, vest=False):
    zg = hz(*cyl(c, rad + .5, 24).T); z0 = float(zg.min()) - .3; z1 = float(zg.max()) + 2.1
    geo = [ring_wall(c, rad, .5, z0, z1, door)]
    if vest:   # two curved walls in front of the door, like the claws of a crab
        for s_ in (-1, 1):
            arc = []
            for t in np.linspace(0, 1, 9):
                a = door + s_ * (.9 / 2 / (rad + .25) + .05) * (1 - t) ; rr_ = rad + .25 + 1.7 * t
                a2 = a + s_ * .35 * math.sin(t * math.pi)
                arc.append((c[0] + math.cos(a2) * rr_, c[1] + math.sin(a2) * rr_))
            geo.append(sweep(np.array(arc), .45, 1.5, .02, .3, top_taper=1))
    put(sid, label_, stone_m, geo, 'B', 'hip')
    Rb = rad + .5 + .45; hr = rad * 1.15 + .4
    rv = [(c[0], c[1], z1 + hr)] + [(c[0] + math.cos(k / 32 * 2 * np.pi) * Rb, c[1] + math.sin(k / 32 * 2 * np.pi) * Rb, z1 - .25) for k in range(32)]
    ro = put(sid + 'R', 'Cobertura', th_m, [(rv, [(0, 1 + k, 1 + (k + 1) % 32) for k in range(32)], [(.5, .5)] + [(k / 32 * 4, 1.6) for k in range(32)])], 'B', 'hip')
    if ro:
        for p in ro.data.polygons: p.use_smooth = True
lajes_m, _ = img_mat('lajes', 'blend/spa/drystone.jpg', .9)
HN = 'O diâmetro das casas de São Paio não está publicado: a reconstituição usa {d:.1f} m de diâmetro interior, o da estrutura circular C1 medida na ortofotografia, e paredes de 2,1 m com o topo horizontal. A cobertura cónica de colmo segue o livro do Centro Interpretativo («telhados de forma cónica», de colmo, sem telha) e o desenho do painel, ambos reconstituições. Posição, orientação das portas e tamanho dos pátios: hipotéticos.'.format(d=HD)
e1c = E1.mean(0); _d1 = -_ax1 * 0 + np.array([-_ax1[1], _ax1[0]])
_d1 = _d1 if _d1[1] < 0 else -_d1                  # door to the south (sheltered from the north wind; hypothetical)
house('H1', e1c, HD / 2, 'Casa circular (reconstituição)', math.atan2(_d1[1], _d1[0]))
_pa1 = e1c + _d1 * (HD / 2 + .5 + 1.8)
earth_m = col_mat('earthpatch', (148, 132, 108), .95)
put('E1', 'Terreno sobre a vala (reconstituição)', earth_m, [qgrid(outward(E1C, .02), lambda x, y: e1_plane(x, y) + .02)], 'B', 'hip')
put('E1', 'Pátio lajeado (reconstituição)', lajes_m, [draped(np.array([_pa1 + _ax1 * 2 + _d1 * 1.2, _pa1 - _ax1 * 2 + _d1 * 1.2, _pa1 - _ax1 * 2 - _d1 * 1.2, _pa1 + _ax1 * 2 - _d1 * 1.2]), .04)], 'B', 'hip')
item(id='H1', name='Casa circular das «Ruínas de Habitação»', kind='Habitação', phase='Idade do Ferro, fase recente', ev='doc', evB='hip', roof='hip',
     dims=f'diâmetro interior {HD:.1f} m (hipotético)', note='Construção circular em pedra do nível mais recente (meados do séc. II a.C. a meados do séc. I a.C.), com lareira central e piso decorado com círculos estampilhados; associada a um pátio e a um lajeado (painel; Almeida et al. 2012). ' + HN, src=['pan', 'alm', 'hmdb'])
_ax = E2[1] - E2[0]; _ax /= np.linalg.norm(_ax); e2c = E2.mean(0); _off = (HD / 2 + .55)
_d2 = np.array([_ax[1], -_ax[0]]); _d2 = _d2 if _d2[1] < 0 else -_d2       # doors to the yard on the south side (hypothetical)
for sid, sg in (('H2', -1), ('H3', 1)):
    c_ = e2c + _ax * sg * _off; dv = (e2c + _d2 * 3.2) - c_; house(sid, c_, HD / 2, 'Compartimento circular (reconstituição)', math.atan2(dv[1], dv[0]), vest=True)
_pa2 = e2c + _d2 * 3.6
put('E2', 'Pátio lajeado (reconstituição)', lajes_m, [draped(np.array([_pa2 + _ax * 3 + _d2 * 1.4, _pa2 - _ax * 3 + _d2 * 1.4, _pa2 - _ax * 3 - _d2 * 1.4, _pa2 + _ax * 3 - _d2 * 1.4]), .04)], 'B', 'hip')
for sid in ('H2', 'H3'):
    item(id=sid, name='Compartimento circular do conjunto habitacional', kind='Habitação', phase='Idade do Ferro, fase recente', ev='doc', evB='hip', roof='hip',
         dims=f'diâmetro interior {HD:.1f} m, vestíbulo com ≈ 1,7 m (hipotéticos)', note='O painel mostra dois compartimentos circulares lado a lado, ligados a um pátio; o conjunto teria três ou quatro construções. Na fase mais recente, a alguns compartimentos circulares «acrescentou-se um vestíbulo, cuja forma faz lembrar as patas de um caranguejo» (Almeida et al. 2012, p. 19): dois muros curvos à frente da porta. ' + HN, src=['pan', 'alm'])
# ---------- buildings (LiDAR MDS − MDT): chapel = nave + two lower annexes on the north side, each a gabled volume fitted to
# the MDS; the other buildings (outside the castro, only in the current state) are simple neutral grey volumes: outline of the
# MDS − MDT mask, flat roof at the median MDS height. The Interpretation Centre is built into the slope and the LiDAR classifies
# its roof as ground: its outline is the 3-4 m step of the ground model on the sea side (traced on the slope map), roof at the
# ground height, walls down to the ground outside.
import cv2
nd = _dsm - _dtm
_ci = np.arange(LB['n']); _GXl = LB['x0'] + (_ci + .5) * LB['cs'] - X0L; _GYl = LB['y1'] - (_ci + .5) * LB['cs'] - Y0L
lime_m = col_mat('lime', (204, 203, 198), .85); grey_m = col_mat('roofgrey', (150, 150, 146), .85)
Image.fromarray(TX.ashlar_tile()).save('blend/spa/ashlar.jpg', quality=88)
ashlar_m, _ = img_mat('ashlar', 'blend/spa/ashlar.jpg', .9)
Image.fromarray(TX.roof_tile()).save('blend/spa/rooftile.jpg', quality=88)
tile_m, _ = img_mat('rooftile', 'blend/spa/rooftile.jpg', .8)
gran_m = col_mat('granite_light', (176, 173, 164), .85)        # copings, window frames, crosses: lighter dressed granite
glass_m = col_mat('window', (52, 62, 74), .25)
def _T(cx, cy, a):
    ca, sa = math.cos(a), math.sin(a); return lambda u, v, z: (cx + u * ca - v * sa, cy + u * sa + v * ca, z)
def box_uv(cx, cy, a, lx, ly, z0, z1, m=4.0, top=True):
    """Box with world-scale UVs (m metres per texture tile): faces in local u (length lx) and v (width ly)."""
    T = _T(cx, cy, a); hx, hy = lx / 2, ly / 2; V = []; F = []; UV = []
    sides = [((-hx, -hy), (hx, -hy)), ((hx, -hy), (hx, hy)), ((hx, hy), (-hx, hy)), ((-hx, hy), (-hx, -hy))]
    for (u0, v0), (u1, v1) in sides:
        L = math.hypot(u1 - u0, v1 - v0); o = len(V)
        V += [T(u0, v0, z0), T(u1, v1, z0), T(u1, v1, z1), T(u0, v0, z1)]
        UV += [(0, z0 / m), (L / m, z0 / m), (L / m, z1 / m), (0, z1 / m)]; F.append((o, o + 1, o + 2, o + 3))
    if top:
        o = len(V); V += [T(-hx, -hy, z1), T(hx, -hy, z1), T(hx, hy, z1), T(-hx, hy, z1)]; UV += [(0, 0), (lx / m, 0), (lx / m, ly / m), (0, ly / m)]; F.append((o, o + 1, o + 2, o + 3))
    return V, F, UV
def gable_ends_uv(cx, cy, a, lx, ly, z0, h, m=4.0):
    T = _T(cx, cy, a); V = []; F = []; UV = []
    for s_ in (-1, 1):
        o = len(V); u = s_ * lx / 2
        V += [T(u, -ly / 2 * s_, z0), T(u, ly / 2 * s_, z0), T(u, 0, z0 + h)]
        UV += [(0, z0 / m), (ly / m, z0 / m), (ly / 2 / m, (z0 + h) / m)]; F.append((o, o + 1, o + 2))
    return V, F, UV
def gable_roof_uv(cx, cy, a, lx, ly, z0, h, ov=.3, th=.12, m=2.0):
    """Two roof planes (ridge along u) with eaves overhang ov and a visible thickness th; tile UVs along the slope."""
    T = _T(cx, cy, a); hx, hy = lx / 2 + ov, ly / 2 + ov; dz = h * ov / (ly / 2); zl = z0 - dz; S = math.hypot(hy, h + dz)
    V = []; F = []; UV = []
    for s_ in (-1, 1):
        o = len(V); V += [T(-hx, s_ * hy, zl), T(hx, s_ * hy, zl), T(hx, 0, z0 + h), T(-hx, 0, z0 + h)]
        UV += [(0, 0), (2 * hx / m, 0), (2 * hx / m, S / m), (0, S / m)]
        F.append((o, o + 1, o + 2, o + 3) if s_ > 0 else (o + 3, o + 2, o + 1, o))
        o = len(V); V += [T(-hx, s_ * hy, zl - th), T(hx, s_ * hy, zl - th), T(hx, s_ * hy, zl), T(-hx, s_ * hy, zl)]   # eave edge
        UV += [(0, 0), (2 * hx / m, 0), (2 * hx / m, .06), (0, .06)]; F.append((o, o + 1, o + 2, o + 3) if s_ > 0 else (o + 3, o + 2, o + 1, o))
    for s_ in (-1, 1):   # verge thickness at both gable ends
        u = s_ * hx; o = len(V)
        V += [T(u, -hy, zl - th), T(u, -hy, zl), T(u, 0, z0 + h), T(u, 0, z0 + h - th), T(u, hy, zl), T(u, hy, zl - th)]
        UV += [(0, 0)] * 6; F += [(o, o + 1, o + 2, o + 3), (o + 3, o + 2, o + 4, o + 5)]
    return V, F, UV
def coping(cx, cy, a, lx, ly, z0, h, w=.32, t=.16):   # dressed granite copings along the two slopes of each gable end
    T = _T(cx, cy, a); V = []; F = []
    for s_ in (-1, 1):
        u0, u1 = s_ * lx / 2 - w / 2, s_ * lx / 2 + w / 2
        for side in (-1, 1):
            o = len(V); y0_ = side * (ly / 2 + .05)
            P = [(u0, y0_, z0 - .05), (u1, y0_, z0 - .05), (u1, 0, z0 + h), (u0, 0, z0 + h)]
            V += [T(u, v, z) for u, v, z in P] + [T(u, v, z + t) for u, v, z in P]
            F += [(o, o + 1, o + 2, o + 3)[::-1], (o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4), (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7)]
    return V, F, [(0, 0)] * len(V)
def cross(p, z, ang, hgt=1.1):
    return [boxv(p[0], p[1], ang, .16, .16, z, z + hgt), boxv(p[0], p[1], ang, .16, .66, z + hgt * .55, z + hgt * .55 + .16)]
def window(cx, cy, a, u_face, wdt, z0, z1, side):   # on the end face u = u_face (side = +1/-1 outward along u)
    T = _T(cx, cy, a); g = []
    for off, ext, mat in ((.02, .12, 'f'), (.035, 0, 'g')):
        u = u_face + side * off; V = [T(u, -wdt / 2 - ext, z0 - ext), T(u, wdt / 2 + ext, z0 - ext), T(u, wdt / 2 + ext, z1 + ext), T(u, -wdt / 2 - ext, z1 + ext)]
        g.append((mat, (V, [(0, 1, 2, 3) if side > 0 else (3, 2, 1, 0)], [(0, 0)] * 4)))
    return g
def extrude(poly, z0, z1):
    poly = [tuple(p) for p in poly]; n_ = len(poly); V = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    walls = [(i, (i + 1) % n_, n_ + (i + 1) % n_, n_ + i) for i in range(n_)]
    ccw = sum((poly[(i + 1) % n_][0] - poly[i][0]) * (poly[(i + 1) % n_][1] + poly[i][1]) for i in range(n_)) < 0
    if not ccw: walls = [w[::-1] for w in walls]
    roofF = [tuple(range(n_, 2 * n_)) if ccw else tuple(range(2 * n_ - 1, n_ - 1, -1))]
    return (V, walls, [(0, 0)] * len(V)), (V, roofF, [(0, 0)] * len(V))
def outline(mask_sub, r0, c0, eps=.45):
    cs_, _ = cv2.findContours(mask_sub.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs_:
        if cv2.contourArea(c) * LB['cs'] ** 2 < 6: continue
        c = cv2.approxPolyDP(c, eps / LB['cs'], True)[:, 0]
        out.append(np.c_[_GXl[c0 + c[:, 0]] - CX, _GYl[r0 + c[:, 1]] - CY])
    return out
BLDM = np.zeros(nd.shape, bool); BLD_PTS = []; BINFO = {}; CHFIT = {}
# --- chapel
_cp = np.array([13.9, -25.8]); _r, _c = int((LB['y1'] - (Y0L + _cp[1])) / LB['cs']), int((X0L + _cp[0] - LB['x0']) / LB['cs'])
_sub = nd[_r - 40:_r + 40, _c - 40:_c + 40] > 2.0; _sub = binary_opening(_sub, iterations=2)
_lb, _ = label(_sub); _m = _lb == _lb[40, 40]; rr_, cc_ = np.nonzero(_m); rr_ += _r - 40; cc_ += _c - 40
BLDM[rr_, cc_] = True
P_ = np.c_[_GXl[cc_], _GYl[rr_]]; zt_ = _dsm[rr_, cc_]; base_ = float(_dtm[rr_, cc_].min()); g0 = (base_ - .3 - H0) * EX
top = nd[rr_, cc_] > np.percentile(nd[rr_, cc_], 80)
_pc = P_[top] - P_[top].mean(0); ax_ = np.linalg.svd(_pc, full_matrices=False)[2][0]; ax_ = ax_ if ax_[0] > 0 else -ax_
nv_ = np.array([-ax_[1], ax_[0]]); c_top = P_[top].mean(0)
u_ = (P_ - c_top) @ ax_; v_ = (P_ - c_top) @ nv_
side_n = 1 if (v_ > 0).sum() > (v_ < 0).sum() else -1                   # the annexes make the north side wider
hw = float(np.percentile(np.abs(v_[np.sign(v_) == -side_n]), 99))
nave = np.abs(v_) <= hw + .25
u0n, u1n = np.percentile(u_[nave], [.5, 99.5]); L_n = float(u1n - u0n); W_n = 2 * hw
cn = c_top + ax_ * (u0n + u1n) / 2
ridge = float(np.percentile(zt_[nave & (np.abs(v_) < .7) & (np.abs(u_ - (u0n + u1n) / 2) < L_n / 2 - 1)], 80))
eave = float(np.median(zt_[nave & (np.abs(np.abs(v_) - hw) < .5)]))
ang_ = math.atan2(ax_[1], ax_[0]); ze, zr = (eave - H0) * EX, (ridge - H0) * EX; cnb = cn - [CX, CY]
put('CHw', 'Capela de São Paio (paredes)', ashlar_m, [box_uv(cnb[0], cnb[1], ang_, L_n - .2, W_n - .2, g0, ze, top=False), gable_ends_uv(cnb[0], cnb[1], ang_, L_n - .2, W_n - .2, ze, zr - ze)], 'AB', 'conf')
put('CH', 'Capela de São Paio', tile_m, [gable_roof_uv(cnb[0], cnb[1], ang_, L_n - .2, W_n - .2, ze, zr - ze, .25)], 'AB', 'conf')
_crz = []
geo_g = [coping(cnb[0], cnb[1], ang_, L_n - .2, W_n - .2, ze, zr - ze)]
for s_ in (-1, 1):   # the MDS has a 1.3-1.6 m spike over each gable apex: a cross on both ends (seen on the west one, photograph 2025)
    e_ = cnb + ax_ * s_ * (L_n / 2 - .1)
    pk = float(np.max(zt_[(np.abs(u_ - (u0n + u1n) / 2 - s_ * L_n / 2) < 1.2) & (np.abs(v_) < 1)]))
    _crz.append(round(pk - ridge, 2)); geo_g += cross(e_, zr + .1, ang_, max(.8, min(1.4, pk - ridge)))
wend = -1 if ax_[0] > 0 else 1         # west end of the nave (smaller x)
# tall narrow window in the middle of the west gable (photograph 2025; size read on the photograph, approximate)
WIN = window(cnb[0], cnb[1], ang_, wend * (L_n - .2) / 2, .55, g0 + .3 + 1.3, g0 + .3 + 3.2, wend)
annexes = []
_rest = ~nave & (np.sign(v_) == side_n)
_g = np.zeros(_m.shape, bool); _g[rr_[_rest] - (_r - 40), cc_[_rest] - (_c - 40)] = True; _g = binary_opening(_g, iterations=2)
_la, _na = label(_g)
for k in range(1, _na + 1):
    sel = _la[rr_ - (_r - 40), cc_ - (_c - 40)] == k
    if sel.sum() * LB['cs'] ** 2 < 4: continue
    ua0, ua1 = np.percentile(u_[sel], [2, 98]); va1 = float(np.percentile(np.abs(v_[sel]), 98))
    za_e = float(np.percentile(zt_[sel], 25)); za_r = float(np.percentile(zt_[sel], 95))
    ca = c_top + ax_ * (ua0 + ua1) / 2 + nv_ * side_n * (hw + va1) / 2 - [CX, CY]
    La, Wa = float(ua1 - ua0), float(va1 - hw)
    zae, zar = (za_e - H0) * EX, (max(za_r, za_e + .6) - H0) * EX
    annexes.append(dict(c=ca, L=La, W=Wa, eave=za_e - base_, ridge=za_r - base_))
    put(f'CHa{k}w', 'Capela de São Paio (anexo, paredes)', ashlar_m, [box_uv(ca[0], ca[1], ang_, La, Wa + .1, g0, zae, top=False), gable_ends_uv(ca[0], ca[1], ang_, La, Wa + .1, zae, zar - zae)], 'AB', 'conf')
    put(f'CHa{k}', 'Capela de São Paio (anexo)', tile_m, [gable_roof_uv(ca[0], ca[1], ang_, La, Wa + .1, zae, zar - zae, .2)], 'AB', 'conf')
    geo_g.append(coping(ca[0], ca[1], ang_, La, Wa + .1, zae, zar - zae, .26, .12))
    if (ca - cnb) @ ax_ * wend > 0:      # the west annex has a small window on its west face (photograph 2025, approximate)
        WIN += window(ca[0], ca[1], ang_, wend * La / 2, .42, g0 + .3 + 1.0, g0 + .3 + 1.9, wend)
put('CHx', 'Capela de São Paio (cruzes, cunhais e molduras)', gran_m, geo_g + [g for t, g in WIN if t == 'f'], 'AB', 'conf')
put('CHv', 'Capela de São Paio (janelas)', glass_m, [g for t, g in WIN if t == 'g'], 'AB', 'conf')
CHFIT = dict(L=L_n, W=W_n, eave=eave - base_, ridge=ridge - base_, az=(90 - math.degrees(ang_)) % 180, ann=annexes, crz=_crz)
BINFO['CH'] = dict(area=float(len(rr_) * LB['cs'] ** 2), top=ridge, base=base_, c=tuple(cn))
BLD_PTS.append(P_[::7] - [CX, CY])
print('chapel', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in CHFIT.items() if k != 'ann'}, [(round(a['L'], 1), round(a['W'], 1), round(a['eave'], 1), round(a['ridge'], 1)) for a in annexes])
# --- other buildings: grey neutral volumes
def bld_simple(bid, nm, cxy, rad=12):
    r, c = int((LB['y1'] - (Y0L + cxy[1])) / LB['cs']), int((X0L + cxy[0] - LB['x0']) / LB['cs'])
    sub = binary_opening(nd[r - rad * 4:r + rad * 4, c - rad * 4:c + rad * 4] > 2.0, iterations=2); lb_, _ = label(sub)
    k = lb_[rad * 4, rad * 4] or np.bincount(lb_.ravel())[1:].argmax() + 1; m_ = lb_ == k
    rr, cc = np.nonzero(m_); rr += r - rad * 4; cc += c - rad * 4; BLDM[rr, cc] = True
    zt = _dsm[rr, cc]; base = float(_dtm[rr, cc].min()) - .3; topz = float(np.median(zt))
    geo_w, geo_r = [], []
    for poly in outline(m_, r - rad * 4, c - rad * 4):
        w_, rf_ = extrude(poly, (base - H0) * EX, (topz - H0) * EX); geo_w.append(w_); geo_r.append(rf_)
    put(bid + 'w', nm + ' (paredes)', lime_m, geo_w, 'A', 'conf'); put(bid, nm, grey_m, geo_r, 'A', 'conf')
    BINFO[bid] = dict(area=float(m_.sum() * LB['cs'] ** 2), top=float(np.percentile(zt, 97)), base=base + .3, c=(float(_GXl[cc].mean()), float(_GYl[rr].mean())))
    BLD_PTS.append(np.c_[_GXl[cc] - CX, _GYl[rr] - CY][::7])
bld_simple('B1', 'Edifício a norte do castro', (-22.2, 47.1)); bld_simple('B2', 'Anexo agrícola', (32.5, 66.0))
# --- Interpretation Centre: roof = ground model inside the outline of its 3-4 m step (slope map), walls down to the ground outside
CI_POLY = [(-61.0, 27.5), (-53.3, 28.6), (-53.3, 24.6), (-48.6, 25.2), (-46.0, 20.0), (-43.5, 13.5), (-41.0, 7.2), (-46.0, 5.6), (-51.0, 5.9),
           (-52.0, 9.0), (-52.2, 12.0), (-53.2, 15.0), (-54.2, 17.2), (-55.5, 20.0), (-57.5, 22.0), (-60.5, 24.0)]
_cip = loc(np.array(CI_POLY))
from matplotlib.path import Path as _MP
_ctr = _cip.mean(0); _cipo = _ctr + (_cip - _ctr) * (1 + .6 / np.linalg.norm(_cip - _ctr, axis=1, keepdims=True))   # 0.6 m outwards: covers the steep ground faces
_gx, _gy = np.meshgrid(np.arange(-55, -35, .25), np.arange(-10, 45, .25))
_ins = _MP(_cip).contains_points(np.c_[_gx.ravel(), _gy.ravel()])
_roofz = float(np.median(hz(_gx.ravel()[_ins], _gy.ravel()[_ins]))) + .06
_ring = _MP(_cipo + (_cipo - _ctr) * .15).contains_points(np.c_[_gx.ravel(), _gy.ravel()]) & ~_MP(_cipo).contains_points(np.c_[_gx.ravel(), _gy.ravel()])
_low = float(np.percentile(hz(_gx.ravel()[_ring], _gy.ravel()[_ring]), 10)) - .3
_rz = np.maximum(hz(*_cipo.T) + .06, _roofz)        # roof edge follows the ground where it rises above the median (east side)
Vr = [(x, y, z) for (x, y), z in zip(_cipo, _rz)]; n_ = len(Vr)
ci_w = (Vr + [(x, y, _low) for x, y in _cipo], [(i, (i + 1) % n_, n_ + (i + 1) % n_, n_ + i) for i in range(n_)], [(0, 0)] * (2 * n_))
ci_r = (Vr, [tuple(range(n_))], [(0, 0)] * n_)
_bm = bmesh.new()
put('CIw', 'Centro Interpretativo (paredes)', lime_m, [ci_w], 'A', 'conf'); put('CI', 'Centro Interpretativo', grey_m, [ci_r], 'A', 'conf')
for nm_ in ('A-CIw', 'A-CI'):
    o_ = bpy.data.objects.get(nm_)
    if o_:
        _bm = bmesh.new(); _bm.from_mesh(o_.data); bmesh.ops.recalc_face_normals(_bm, faces=_bm.faces); _bm.to_mesh(o_.data); _bm.free()
BLD_PTS.append(dense(np.vstack([_cip, _cip[:1]]), 1.0))
# the lower wing of the same building on the sea side (café-restaurant): MDS − MDT > 1.8 m next to the outline
_r0, _c0 = int((LB['y1'] - (Y0L + 32)) / LB['cs']), int((X0L - 64 - LB['x0']) / LB['cs'])
_sw = binary_opening(nd[_r0:_r0 + int(30 / LB['cs']), _c0:_c0 + int(26 / LB['cs'])] > 1.8, iterations=2)
_gw, _gr = [], []
for poly in outline(_sw, _r0, _c0):
    if _MP(_cip).contains_points(poly).mean() > .5: continue
    pr_ = _MP(poly); sel = [(i, j) for i in range(_sw.shape[0]) for j in range(_sw.shape[1]) if _sw[i, j] and pr_.contains_point((_GXl[_c0 + j] - CX, _GYl[_r0 + i] - CY))]
    if not sel: continue
    ii_, jj_ = np.array(sel).T; zt = _dsm[_r0 + ii_, _c0 + jj_]; b0 = float(_dtm[_r0 + ii_, _c0 + jj_].min()) - .3
    w_, rf_ = extrude(poly, (b0 - H0) * EX, (float(np.median(zt)) - H0) * EX); _gw.append(w_); _gr.append(rf_); BLDM[_r0 + ii_, _c0 + jj_] = True
put('CI2w', 'Centro Interpretativo, ala do lado do mar (paredes)', lime_m, _gw, 'A', 'conf'); put('CI2', 'Centro Interpretativo, ala do lado do mar', grey_m, _gr, 'A', 'conf')
BLD_PTS = np.vstack(BLD_PTS) if BLD_PTS else np.zeros((0, 2))
print('buildings', {k: (round(v['area']), round(v['top'] - v['base'], 1)) for k, v in BINFO.items()}, 'CI roof', round(_roofz + H0, 2), 'low', round(_low + H0, 2))
_ann = '; '.join(f'anexo de {a["L"]:.1f} × {a["W"]:.1f} m, beirado ≈ {a["eave"]:.1f} m e cumeeira ≈ {a["ridge"]:.1f} m' for a in CHFIT['ann'])
item(id='CH', name='Capela de São Paio', kind='Edifício moderno', phase='séc. XVII (?), remodelada em 1885 (?) e nos anos 70 do séc. XX', ev='conf', evB='conf',
     dims=f'nave ≈ {CHFIT["L"]:.1f} × {CHFIT["W"]:.1f} m · beirado ≈ {CHFIT["eave"]:.1f} m e cumeeira ≈ {CHFIT["ridge"]:.1f} m acima do solo · eixo a {CHFIT["az"]:.0f}° do norte; {_ann} (LiDAR)',
     note='No extremo sul do castro. Apesar do aspeto recente, incorpora elementos provavelmente do século XVII; no interior há a data de 1885, talvez de obras; nos anos 70 do século XX foi largamente remodelada e só restou a fachada principal. O altar-mor é um rochedo tirado da penedia (Almeida et al. 2012). '
          'Volumes e alturas do LiDAR (MDS): nave de duas águas e dois anexos mais baixos do lado norte; o MDS tem um pico de 1,3–1,6 m sobre cada empena, as cruzes. Silharia de granito em fiadas, cunhais e remates das empenas de granito mais claro, janela alta e estreita na empena poente e janela pequena no anexo poente, como na fotografia de 2025 (medidas das janelas aproximadas, lidas na fotografia). '
          'A porta não se vê nas fotografias consultadas e não foi desenhada.', src=['alm', 'lidar', 'tese', 'pan'])
for bid, nm in (('B1', 'Edifício a norte do castro'), ('B2', 'Anexo agrícola')):
    if bid in BINFO:
        item(id=bid, name=nm, kind='Edifício moderno', phase='atual', ev='conf', evB='conf', dims=f'planta ≈ {BINFO[bid]["area"]:.0f} m² · altura ≈ {BINFO[bid]["top"] - BINFO[bid]["base"]:.1f} m (LiDAR)',
             note='Edifício atual, fora do castro: volume simples em cinzento neutro, com o contorno e a altura mediana do LiDAR (MDS).', src=['lidar', 'orto'])
item(id='CI', name='Centro Interpretativo do Castro de São Paio', kind='Edifício moderno', phase='2012', ev='conf', evB='conf', dims=f'cobertura ≈ {_roofz + H0:.1f} m de altitude, à cota do terreno do lado do castro; fachadas até ≈ {_low + H0:.1f} m do lado do mar (LiDAR)',
     note='Aberto no fim de 2012, no mesmo edifício de um café-restaurante; mostra o espólio do castro e painéis de arqueologia, geologia e biologia. O edifício está encaixado na encosta e o LiDAR classifica a cobertura como solo: o contorno é o degrau de 3–4 m do modelo do terreno do lado do mar (mapa de declives), e a ala mais baixa do lado do mar vem do MDS. Volume simples em cinzento neutro.', src=['alm', 'muni', 'tese', 'lidar'])
# ---------- orthophoto (aligned on the LiDAR, lidar/spa_orto.py) on the box grid: z20 where captured, z19 elsewhere
def orto_at(x, y): return np.stack([_samp(ORT[..., k], x, y) for k in range(3)], -1)
# masks on a 0.5 m grid over the disc: paved paths and boardwalk (grey, low saturation), granite on the shore (relief + grey)
_g5 = np.arange(-R, R, .5) + .25; _GX5, _GY5 = np.meshgrid(_g5, -_g5)
_O5 = orto_at(_GX5, _GY5); _mx = _O5.max(2); _mn = _O5.min(2); _sat = (_mx - _mn) / (_mx + 1)
_relief = _samp(_dtm - gaussian_filter(_dtm, 12), _GX5, _GY5); _h5 = hraw(_GX5, _GY5)
PAVED_G = binary_opening((_sat < .1) & (_mx > 175) & (_h5 > 3), iterations=1)
ROCK_G = binary_opening(((_relief > .35) | ((_sat < .16) & (_mx < 150) & (_h5 < 9))) & (_h5 > SEA + .2) & (_h5 < 12), iterations=1)
def ROCKY(x, y):
    i = int((R - y) / .5); j = int((x + R) / .5)
    return 0 <= i < len(_g5) and 0 <= j < len(_g5) and bool(ROCK_G[i, j])
# outline of the village used only to thin the vegetation and tint the ground: the T1 crest, then the edge of the plateau to the
# chapel and along the shore (break of slope read on the LiDAR; not a structure)
ENC = np.vstack([T1, loc([(10.0, -36.0), (-8.0, -42.0), (-24.0, -40.0), (-36.0, -22.0), (-41.0, 0.0), (-40.0, 30.0), (-38.0, 55.0)])])
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
wallpts = np.vstack([dense(line('T1'))] + [dense(np.vstack([p, p[:1]]), .8) for p in STRUCT_POLYS] + [BLD_PTS] + [dense(loc(pts), .5) for pts, w in BW])
from scipy.spatial import cKDTree
kd = cKDTree(wallpts)
from matplotlib.path import Path as MPath
_encl = MPath(ENC)
_upper = _encl
ntp0 = len(tp)
# canes (Arundo donax) in the south-east thicket and the hedges of the fields: the orthophoto shows them as a fine, even texture and
# the canopy model as a flat top 2-6 m high without crowns; LiDAR "trees" there are replaced by clumps of canes
_chs = gaussian_filter(CHM, 2); _sd = np.sqrt(np.maximum(uniform_filter(CHM ** 2, 13) - uniform_filter(CHM, 13) ** 2, 0))
REED = binary_opening(binary_closing((_chs > 1.8) & (_chs < 6.5) & (_sd < 1.0), iterations=2), iterations=3)
_lr, _nr = label(REED); _szr = np.bincount(_lr.ravel()); REED = (_szr[_lr] > 30 / LB['cs'] ** 2) & (_lr > 0)
def is_reed(x, y): return _samp(REED.astype(np.float32), x, y) > .5
tp = [p for p in tp if not is_reed(*p)]
tp = [p for p in tp if (kd.query(p)[0] > 8 and not _encl.contains_point(p)) or (kd.query(p)[0] > 5 and rng.random() < .12)]   # real trees, thinned inside the enclosure (10-15 %) and none within 5 m of the structures
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
def blades(n=6, w=.045):   # two-sided (back faces would render black)
    V = []; F = []
    for k in range(n):
        a = k / n * 2 * np.pi + rng.random() * .5; lean = .18 + rng.random() * .2
        bx, by = math.cos(a + 1.57) * w, math.sin(a + 1.57) * w; tx, ty = math.cos(a) * lean, math.sin(a) * lean
        o = len(V); V += [(-bx, -by, 0), (bx, by, 0), (tx, ty, .75 + rng.random() * .25)]; F += [(o, o + 1, o + 2), (o + 2, o + 1, o)]
    return V, F, [(0, 0)] * len(V)
def reeds(n=16):   # a clump of canes: thin upright stems with a few drooping leaves near the top, two-sided
    V = []; F = []; g = np.random.default_rng(11)
    for k in range(n):
        x0, y0 = g.normal(0, .12, 2); h = .75 + .25 * g.random(); lx, ly = g.normal(0, .06, 2); w = .012
        o = len(V); V += [(x0 - w, y0, 0), (x0 + w, y0, 0), (x0 + lx, y0 + ly, h)]; F += [(o, o + 1, o + 2), (o + 2, o + 1, o)]
        for j in range(3):
            a = g.random() * 6.28; z = h * (.55 + .14 * j); L = .18 + .1 * g.random(); px, py = x0 + lx * z / h, y0 + ly * z / h
            o = len(V); V += [(px, py, z), (px + math.cos(a) * L * .5, py + math.sin(a) * L * .5, z + .03 + .02 * g.random()), (px + math.cos(a) * L, py + math.sin(a) * L, z - .06), (px + math.cos(a + 1.57) * .02, py + math.sin(a + 1.57) * .02, z)]
            F += [(o, o + 1, o + 2), (o + 2, o + 1, o), (o, o + 3, o + 1), (o + 1, o + 3, o)]
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
 'shrub': [('leaf', tblobs([(0, 0, .45, .4, .8), (.3, .12, .38, .3, .6), (-.27, -.14, .36, .3, .58), (.05, -.3, .34, .26, .5), (-.1, .3, .4, .26, .55)], 2))],
 'reed': [('leaf', reeds(16))],
 'tuft': [('leaf', blades(9, .1))],
}
_oak = [(96, 128, 54), (112, 140, 60), (84, 116, 48), (122, 138, 58), (78, 108, 50), (104, 122, 52)]
_cork = [(70, 88, 52), (80, 96, 56), (62, 80, 48), (88, 100, 58), (66, 84, 54)]
_euc = [(124, 140, 100), (136, 148, 108), (116, 132, 96), (144, 152, 112), (120, 138, 106), (130, 142, 92)]
_chest = [(92, 130, 50), (104, 140, 56), (84, 120, 46), (112, 146, 62), (98, 128, 52)]
PAL = {'oak': _oak, 'oak2': _oak, 'oak3': _oak, 'cork': _cork, 'cork2': _cork, 'euc': _euc, 'euc2': _euc, 'chest': _chest, 'chest2': _chest,
       'shrub': [(98, 114, 58), (90, 106, 54), (110, 122, 62), (102, 116, 56), (156, 146, 66)], 'reed': [(150, 168, 100), (138, 158, 92), (162, 170, 108), (128, 146, 84)],
       'tuft': [(150, 156, 90), (162, 164, 98), (138, 146, 82)]}
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
pathpts = np.argwhere(PAVED_G)[:, ::-1].astype(float); pathpts = np.stack([pathpts[:, 0] * .5 - R, R - pathpts[:, 1] * .5], 1) if len(pathpts) else np.zeros((1, 2)) + 1e6; kp = cKDTree(pathpts)
_SP = [_MP2(p_) for p_ in STRUCT_POLYS + [outward(E1, 1.0), outward(E2, 1.2)]]
def free(x, y, dw, dp=2.5): return math.hypot(x, y) < R - 2 and kd.query((x, y))[0] > dw and kp.query((x, y))[0] > dp and float(hraw(x, y)) > 1.2 and not ROCKY(x, y) and not any(q_.contains_point((x, y)) for q_ in _SP)
n_sh = 0
# shrubs where the LiDAR sees low vegetation: local maxima of the canopy model between 0.7 and 2.8 m (gorse, broom, brambles)
_low = gaussian_filter(np.where((CHM > .7) & (CHM < 2.8), CHM, 0), 2)[r0_:r1_, c0_:c1_]
_lp = (_low == _mf(_low, 17)) & (_low > .5)
for yy_, xx_ in zip(*np.nonzero(_lp)):
    lx = LB['x0'] + (c0_ + xx_ + .5) * LB['cs'] - X0L; ly = LB['y1'] - (r0_ + yy_ + .5) * LB['cs'] - Y0L; x, y = lx - CX, ly - CY
    if n_sh > 260 or not free(x, y, 3) or is_reed(x, y) or (_encl.contains_point((x, y)) and rng.random() > .25): continue
    hs_ = float(CHM[r0_ + yy_, c0_ + xx_])
    TREES.append([round(x, 2), round(y, 2), round(float(hz(x, y)), 2), round(max(1.0, hs_), 2), TYPES.index('shrub'), 4 if rng.random() < .12 else int(rng.integers(0, 4)), round(rng.random() * 6.28, 2)]); n_sh += 1
n_rd = 0
for x in np.arange(-R, R, 1.1):
    for y in np.arange(-R, R, 1.1):
        x_, y_ = x + rng.normal(0, .35), y + rng.normal(0, .35)
        if math.hypot(x_, y_) > R - 1.5 or not is_reed(x_, y_) or kd.query((x_, y_))[0] < 2: continue
        h_ = float(np.clip(_samp(_chs, x_, y_), 1.8, 5.5)) * (.85 + .3 * rng.random())
        TREES.append([round(x_, 2), round(y_, 2), round(float(hz(x_, y_)), 2), round(h_, 2), TYPES.index('reed'), int(rng.integers(0, 4)), round(rng.random() * 6.28, 2)]); n_rd += 1
print('reed clumps', n_rd)
n_tu = 0
for _ in range(20000):
    x, y = (rng.random(2) * 2 - 1) * R
    if n_tu > 420 or not free(x, y, 1.6, 1.8) or is_reed(x, y): continue
    ins = _encl.contains_point((x, y))
    if rng.random() < (.22 if ins else .8):
        TREES.append([round(x, 2), round(y, 2), round(float(hz(x, y)), 2), round(.35 + rng.random() * .35, 2), TYPES.index('tuft'), int(rng.integers(0, 3)), round(rng.random() * 6.28, 2)]); n_tu += 1
print('trees', len(tp), 'shrubs', n_sh, 'tufts', n_tu, 'R', R)
# ---------- labels (empties named LBL-...)
def lbl(t, p, dz=3):
    e = bpy.data.objects.new(f'LBL-{t}-{len(bpy.data.objects)}', None); e.location = (float(p[0]), float(p[1]), float(hz(p[0], p[1])) + dz)
    bpy.context.scene.collection.objects.link(e)
lbl('Capela de São Paio', loc(BINFO['CH']['c']) if 'CH' in BINFO else loc([14, -26]), 8)
lbl('Talude e muralha nascente', T1[int(len(T1) * .45)], 4)
lbl('Ruínas de Habitação', e1c, 3)
lbl('Conjunto habitacional', e2c, 3)
lbl('Estrutura circular', C1, 2.5)
lbl('Centro Interpretativo', loc([-50.0, 16.0]), 4)
lbl('Praia dos Castros', loc([-2.0, -88.0]), 2)
lbl('Penedos amoladoiros (aprox.)', loc([10.5, -86.9]), 2)
lbl('Oceano Atlântico', loc([-95.0, -40.0]), 2)

# ---------- ground texture: the orthophoto as surface classes and low-frequency colour, procedural detail per class at 5 cm
# (blend/spa_tex.py): no car, parasol or building shadow of the satellite image; violet scrub toned down; light hillshade and AO
TS = 4096; mpp = 2 * R / TS
_dark = binary_dilation(BLDM, iterations=40) if 'BLDM' in globals() else np.zeros_like(CLS['SEA'])
ORTC = TX.clean_ortho(ORT, _dark)
import cv2 as _cv2                         # surf foam on the rocks (white in the photograph) painted over with the rock around it
_fm = _cv2.dilate(CLS['FOAM'].astype(np.uint8) * 255, np.ones((5, 5), np.uint8))
ORTC = _cv2.inpaint(np.clip(ORTC, 0, 255).astype(np.uint8), _fm, 8, _cv2.INPAINT_TELEA).astype(float)
def _samp_c(x, y): return np.stack([_samp(ORTC[..., k], x, y) for k in range(3)], -1)
_CLF = {k: gaussian_filter(CLS[k].astype(np.float32), 1.0) for k in ('SEA', 'SAND', 'ROCK', 'PAVED', 'GREEN', 'VIOLET', 'EARTH')}
def _classes_at(x, y):
    W = {k: _samp(v, x, y) for k, v in _CLF.items()}; s_ = sum(W.values()) + 1e-6
    return {k: v / s_ for k, v in W.items()}
col, GX, GY = TX.ground(_samp_c, TS, R, _classes_at, np.random.default_rng(1), hgt=lambda x, y: _samp(DTM, x, y), sea=SEA)
zz2 = hz(GX[::4, ::4], GY[::4, ::4]); gy2, gx2 = np.gradient(zz2, mpp * 4)
nx, ny = -gx2, gy2; nn = np.sqrt(nx * nx + ny * ny + 1); L_ = np.array([-.55, .45, .7]); L_ /= np.linalg.norm(L_)
shade = (nx * L_[0] + ny * L_[1] + L_[2]) / nn; shade = np.asarray(Image.fromarray(shade.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
col *= np.clip(1 + .25 * (shade - np.median(shade)), .78, 1.15)[..., None]
rim = np.clip((np.hypot(GX, GY) - (R - 1.0)) / 1.0, 0, 1)[..., None]; col = col * (1 - rim * .25)
del GX, GY
# ---------- ambient occlusion (Cycles) baked through a temporary disc UV map, then multiplied into the texture
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.device = 'CPU'
aouv = terrain.data.uv_layers.new(name='AOUV')
LV = np.zeros(len(terrain.data.loops), int); terrain.data.loops.foreach_get('vertex_index', LV)
_VV = np.zeros((len(terrain.data.vertices), 3)); terrain.data.vertices.foreach_get('co', _VV.ravel())
aouv.data.foreach_set('uv', uv_of(_VV[LV, 0], _VV[LV, 1]).ravel())
terrain.data.uv_layers.active = aouv
ao = bpy.data.images.new('ao', 1024, 1024, float_buffer=False); ANs = []
for m_ in terrain.data.materials:
    an = m_.node_tree.nodes.new('ShaderNodeTexImage'); an.image = ao; m_.node_tree.nodes.active = an; ANs.append((m_, an))
for o in sc.objects: o.select_set(False)
for o in sc.objects:
    if o.name.startswith('B-') or o.name == 'sea': o.hide_render = True
terrain.select_set(True); bpy.context.view_layer.objects.active = terrain
sc.world = sc.world or bpy.data.worlds.new('w')
sc.render.bake.margin = 4
bpy.ops.object.bake(type='AO')
aopx = np.array(ao.pixels[:]).reshape(1024, 1024, 4)[::-1, :, 0]
aoi = Image.fromarray((np.clip(aopx, 0, 1) * 255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.5))
col *= (.72 + .28 * np.asarray(aoi, float)[..., None] / 255)
for m_, an in ANs: m_.node_tree.nodes.remove(an)
terrain.data.uv_layers.remove(terrain.data.uv_layers['AOUV']); terrain.data.uv_layers.active = terrain.data.uv_layers['UVMap']
for o in sc.objects: o.hide_render = False
# four tiles with a 1 m margin (QX0/QY1/TW of the terrain)
col = np.clip(col, 0, 255).astype(np.uint8)
for k in range(4):
    c0 = int(round((QX0[k] + R) / mpp)); r0 = int(round((R - QY1[k]) / mpp)); n_ = int(round(TW / mpp))
    pad = np.pad(col, ((int(QM / mpp) + 2,) * 2, (int(QM / mpp) + 2,) * 2, (0, 0)), mode='edge'); o_ = int(QM / mpp) + 2
    tile = pad[r0 + o_:r0 + o_ + n_, c0 + o_:c0 + o_ + n_]
    Image.fromarray(tile).resize((2048, 2048), Image.LANCZOS).save(f'blend/spa/ground{k}.jpg', quality=90)
    GQ[k][1].image = bpy.data.images.load(os.path.abspath(f'blend/spa/ground{k}.jpg'))
Image.fromarray(col).resize((1024, 1024)).save('blend/spa/ground_preview.jpg', quality=85)

_ids = {c['id'] for c in CAT}
for o in bpy.data.objects:
    sd_ = o.get('sid')
    if sd_ and sd_ not in _ids and not (sd_.endswith('R') and sd_[:-1] in _ids):
        par = max((i for i in _ids if sd_.startswith(i)), key=len, default=None)
        if par: o['sid'] = par
        else: print('sid without catalogue entry', sd_)
# ---------- export
SOURCES = {
 "alm": "Almeida, P. B. de; Araújo, M. A.; Abrunhosa, M. J.; Teixeira, J.; Cruz, V. (2012). O Castro de S. Paio (Labruge, Vila do Conde). Vila do Conde: Câmara Municipal (livro do Centro Interpretativo; arqueologia por P. Brochado de Almeida, pp. 15-26). ISBN 978-972-9453-95-3. Cópia no Repositório Aberto da U. Porto: https://hdl.handle.net/10216/22268",
 "pa": "DGPC — Portal do Arqueólogo, sítio «São Paio» (CNS 3560): povoado fortificado da Idade do Ferro; escavações de C. A. Brochado de Almeida e P. J. L. Costa Pinto (1993-1996), sondagem (2004) e levantamento (2005). https://arqueologia.patrimoniocultural.pt/index.php?sid=sitios&subsid=49316",
 "pan": "Painéis interpretativos da Câmara Municipal de Vila do Conde no sítio («Ruínas de Habitação / Family House» e outros), fotografados por T. Pinto em 2025.",
 "hmdb": "The Historical Marker Database — «Ruínas de Habitação / Family House» (n.º 233697), «Os penedos amoladoiros» (233600), «Gravuras da área de S. Paio» (233448), com as coordenadas dos painéis (2023). https://www.hmdb.org/m.asp?m=233697",
 "muni": "Município de Vila do Conde (Visit Vila do Conde) — Castro de São Paio; Rota do Castro de São Paio. https://www.visitviladoconde.pt/fazer/patrimonio/patrimonio-arqueologico/geo_artigo/castro-de-sao-paio-43",
 "tese": "Pinto, T. — Castros do Noroeste de Portugal (tese de doutoramento, Univ. de Santiago de Compostela); visitas em 2022 e 2025: casas circulares, vestígios de fosso e muralha, capela na acrópole, passadiço com painéis, Centro Interpretativo de 2012.",
 "foto": "Fotografias de T. Pinto, 2025: área escavada E2 vista para poente (muro de pedra seca, troncos, corda, passadiço, banco), vala E1 com taipais e painel vista para nascente com a capela ao fundo (empena poente com janela alta e cruz, anexo poente com janela pequena), painéis municipais.",
 "orto": "Ortofotografia de satélite (Google, consultada em novembro de 2026, 0,11-0,22 m por píxel), alinhada ao LiDAR pelos edifícios e muros (desvio corrigido ≈ 1 m): áreas escavadas, estrutura circular, caminhos, passadiço, praia e cores do solo.",
 "lidar": "DGT — LiDAR 2025: nuvem de pontos classificada do bloco 150480 (LO-150480-07-2025, ≈ 21 pontos de solo por m², terreno de 25 cm no lado de terra) e MDT/MDS de 50 cm dos blocos 149480 e 150480 (o castro fica no 149480, a 40-60 m da junção). Talude traçado no relevo e ajustado à crista; edifícios e árvores com a altura do MDS. Sem exagero vertical.",
}
os.makedirs('app/dio', exist_ok=True)
for o in sc.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.abspath(f'app/dio/{SID}.glb'), export_format='GLB', export_apply=True, export_yup=True,
                          export_image_format='JPEG', export_jpeg_quality=86, export_materials='EXPORT', use_selection=False, export_extras=True,
                          export_draco_mesh_compression_enable=False)
import re as _re   # Portuguese decimal comma in the texts of the catalogue
for _it in CAT:
    for _k in ('dims', 'note', 'name'):
        if isinstance(_it.get(_k), str): _it[_k] = _re.sub(r'(?<=\d)\.(?=\d)', ',', _it[_k])
json.dump({'cat': CAT, 'sources': SOURCES, 'R': R, 'ex': EX, 'h0': H0, 'cx': CX, 'cz': -CY, 'trees': TREES, 'types': TYPES, 'pal': {k: [list(c) for c in v] for k, v in PAL.items()}}, open(f'app/dio/{SID}.json', 'w'))
print('ok', os.path.getsize(f'app/dio/{SID}.glb'))
