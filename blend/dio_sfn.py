# Builds a castillos-style disc diorama of one castro in Blender (bpy) and exports a GLB for three.js.
# Citânia de Sanfins (Paços de Ferreira). Usage: /opt/bvenv/bin/python blend/dio_sfn.py pacos-de-ferreira-citania-de-sanfins
# No published plan could be read (see GAPS). Everything comes from the DGT LiDAR 2025 point clouds LO-178484/178485/179484/179485
# (lidar/sfn_laz.py -> lidar/sfn_*25.npy, terrain of 25 cm) and the DGT 2021 orthophoto:
#   - the excavated houses and walls stand out in MDS − MDT (lidar/sfn_walls.py -> lidar/sfn_walls.json): 138 round houses with their
#     own measured diameter and height, and the wall centre lines of the yards and rectangular buildings;
#   - the rampart and the long walls of the southern area are traced on the orthophoto and the LiDAR and snapped onto the standing
#     wall (blend/sfn_trace.py, lidar/sfn_lines.py -> blend/sfn_lines.json);
#   - the reconstructed family unit (1995) and the geodetic pillar on the acropolis from the LiDAR building class and surface heights;
#   - trees at the LiDAR crown positions and heights.
# Local frame: x east, y north (Blender Z up), metres, origin = disc centre. Site point PT-TM06 (-21224.03, 183783.55).
import sys, json, math, os
import numpy as np
import bpy, bmesh
from PIL import Image, ImageFilter, ImageDraw
from scipy.ndimage import gaussian_filter, maximum_filter, map_coordinates, gaussian_filter1d
from scipy.spatial import cKDTree
from matplotlib.path import Path as MPath

SID = sys.argv[-1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
TMP = '/tmp/sfn_blend'; os.makedirs(TMP, exist_ok=True)
rng = np.random.default_rng(14)
WJ = json.load(open('lidar/sfn_walls.json')); LN = json.load(open('blend/sfn_lines.json'))

# ---------- disc: holds the rampart, the excavated quarters, the acropolis and the southern area
CX, CY, R = 10.0, -15.0, 225.0
def loc(p): p = np.asarray(p, float); return np.stack([p[..., 0] - CX, p[..., 1] - CY], -1)

# ---------- terrain heights: DGT LiDAR 2025 ground points (class 2), TIN on a 25 cm grid (7 ground points per m²), no exaggeration
X0L, Y0L = -21224.03, 183783.55
LB = json.load(open('lidar/sfn_box.json'))
_dtm = np.load('lidar/sfn_dtm25.npy').astype(np.float32); _dtm = np.where(np.isnan(_dtm), np.nanmean(_dtm), _dtm)
DTM = gaussian_filter(_dtm, .6)
_dsm = np.load('lidar/sfn_dsm25.npy').astype(np.float32)
CHM = _dsm - _dtm
CHM3 = maximum_filter(_dsm, 3) - _dtm          # gaps between returns closed (0.75 m), for walls and roofs
BLD = np.load('lidar/sfn_bld25.npy')
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
def img_mat(name, path, rough=.95):
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
Image.new('RGB', (64, 64), (120, 130, 70)).save(f'{TMP}/ground_raw.jpg')
# ---------- terrain disc (polar grid, 0.5 m between rings, ≤ 0.7 m along the rim; simplified for the web by tools/gltf/lighten.mjs)
NR, NA = 450, 2000
rr = np.linspace(0, R, NR + 1)[1:]; aa = np.linspace(0, 2 * np.pi, NA, endpoint=False)
X = np.concatenate([[0], (rr[:, None] * np.cos(aa)[None]).ravel()]); Y = np.concatenate([[0], (rr[:, None] * np.sin(aa)[None]).ravel()])
Z = hz(X, Y); V = np.stack([X, Y, Z], 1)
F = [(0, 1 + a, 1 + (a + 1) % NA) for a in range(NA)]
a_ = np.arange(NA); b_ = (a_ + 1) % NA
for r in range(NR - 1):
    o0, o1 = 1 + r * NA, 1 + (r + 1) * NA
    F += list(zip(o0 + a_, o1 + a_, o1 + b_, o0 + b_))
gmat, gtex = img_mat('ground', f'{TMP}/ground_raw.jpg')
terrain = new_obj('terrain', mesh_from('terrain', V, F, uv_of(X, Y)), gmat)
terrain.data.polygons.foreach_set('use_smooth', [True] * len(terrain.data.polygons))
rim = np.arange(1 + (NR - 1) * NA, 1 + NR * NA)
print('terrain verts', len(V))

# ---------- earth skirt with strata, and base
zb = float(Z.min()) - 16
NS = 800; ks = (np.arange(NS) * NA // NS); sx, sy, sz = X[rim][ks], Y[rim][ks], Z[rim][ks]
# the skirt must meet the dense rim: use every rim vertex on the top row
sx, sy, sz = X[rim], Y[rim], Z[rim]; NS = NA
SV = []; SF = []; SUV = []
levels = [0, 1.2, 4, 7, 10, 13, None]
for li, d in enumerate(levels):
    for a in range(NS):
        z = zb if d is None else sz[a] - d
        SV.append((sx[a], sy[a], z)); SUV.append((a / NS * 12, (z - zb) / 40))
for li in range(len(levels) - 1):
    for a in range(NS):
        b = (a + 1) % NS; SF.append((li * NS + a, li * NS + b, (li + 1) * NS + b, (li + 1) * NS + a))
cap = len(SV); SV.append((0, 0, zb)); SUV.append((.5, .5))
for a in range(NS): SF.append(((len(levels) - 1) * NS + (a + 1) % NS, (len(levels) - 1) * NS + a, cap))
st = np.zeros((256, 64, 3)); yy = np.arange(256)[:, None] / 256
band = (np.sin(yy * 40 + np.sin(np.arange(64)[None] / 64 * 2 * np.pi * 3) * .6) * .5 + .5)
st[...] = np.array([120, 86, 56]) * (.78 + .3 * band[..., None]); st[:20] = [92, 120, 60]; st[20:26] = [88, 64, 42]
Image.fromarray(np.clip(st[::-1] + rng.normal(0, 6, st.shape), 0, 255).astype(np.uint8)).resize((64, 256)).save(f'{TMP}/strata.jpg', quality=90)
smat, _ = img_mat('earth', f'{TMP}/strata.jpg')
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
def sweep(pts, w, h, jitter=.1, sink=.4, closed=False, top_taper=.9, step=.8):
    p = dense(pts, step, closed=closed); n = len(p)
    if n < 2: return [], [], []
    d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    nr = np.stack([-d[:, 1], d[:, 0]], 1)
    g = hz(p[:, 0], p[:, 1])
    h = np.asarray(h, float)
    if h.ndim and len(h) != n: h = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(h)), h)
    hh = np.broadcast_to(h, (n,)) + gaussian_filter1d(rng.normal(0, jitter, n), 2.5, mode='wrap' if closed else 'nearest')
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    prof = [(-w / 2, -sink), (-w / 2 * top_taper, 1), (w / 2 * top_taper, 1), (w / 2, -sink)]
    V = []; UV = []
    for i in range(n):
        for j, (o, zz) in enumerate(prof):
            z = g[i] + (zz if zz < 0 else max(.08, hh[i]))
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
CAT = []
def put(sid, name, mat, geo, mode, ev):
    A = Acc()
    for g in geo: A.add(g)
    o = A.obj(f'{mode}-{sid}', mat)
    if o: o['sid'] = sid; o['mode'] = mode; o['ev'] = ev
    return o
def item(**k): CAT.append(k)
cyl = lambda c, rad, n=28: [(c[0] + math.cos(a) * rad, c[1] + math.sin(a) * rad) for a in np.linspace(0, 2 * np.pi, n + 1)[:-1]]
th_m, _ = img_mat('thatch', 'blend/thatch.jpg', 1)
def roof(sid, c, rad, z_eave, z_top, mode, ev, name='Cobertura'):
    rr2 = rad + .6
    rv = [(c[0], c[1], z_top)] + [(c[0] + math.cos(k / 24 * 2 * np.pi) * rr2, c[1] + math.sin(k / 24 * 2 * np.pi) * rr2, z_eave) for k in range(24)]
    ro = put(sid, name, th_m, [(rv, [(0, 1 + k, 1 + (k + 1) % 24) for k in range(24)], [(.5, .5)] + [(k / 24 * 3, 1.5) for k in range(24)])], mode, ev)
    if ro:
        for p in ro.data.polygons: p.use_smooth = True
    return ro

# ---------- the rampart and the long walls (traced, snapped onto the standing wall; height and width measured in the LiDAR)
WALLS = [
 ('M1', 'Muralha poente e norte', 'Muralha'),
 ('S1', 'Muro longo do setor sul (este–oeste, a sul)', 'Muro'),
 ('S2', 'Muro longo do setor sul (norte–sul)', 'Muro'),
 ('S3', 'Muro longo do setor sul (este–oeste, a norte)', 'Muro'),
]
def line(k): return loc(LN[k]['pts'])
for sid, name, kind in WALLS:
    L = LN[sid]; p = line(sid)
    hm = float(np.clip(L['h'], .3, 1.5)); w = float(np.clip(L['w'] - .4, .7, 2.0))   # the 0.75 m max filter widens the measured run by ≈ 0.4 m
    # height along the line from the LiDAR where the wall stands out, the median elsewhere
    pd = dense(p, .8); hv = _samp(np.where(CHM3 > 2.5, 0, CHM3), pd[:, 0], pd[:, 1]); hv = np.where(hv > .2, np.clip(hv, .2, 1.6), hm)
    hv = gaussian_filter1d(hv, 2, mode='nearest')
    put(sid, name, stone_m, [sweep(pd, w, hv, .04, .5, step=.8)], 'A', 'conf')
    item(id=sid, name=name, kind=kind, phase='—', ev='conf', evB='conf',
         dims=f'comprimento ≈ {L["len"]:.0f} m · largura ≈ {w:.1f} m · altura atual mediana ≈ {hm:.2f} m (LiDAR 2025; visível em {L["vis"] * 100:.0f} % do traçado)',
         note=('Traçada na ortofoto de 2021 e no LiDAR de 2025 e ajustada ao muro de pedra que sobressai no modelo de superfície (MDS − MDT). '
               'O nome e a numeração das linhas de muralha das publicações (três a seis linhas, conforme a fonte) não foram confirmados numa planta; '
               'a altura original não está publicada e não foi reconstituída.' if kind == 'Muralha' else
               'Muro de pedra visível na ortofoto de 2021 e no LiDAR de 2025, fora dos bairros escavados; função não identificada nas fontes consultadas.'),
         src=['lidar', 'orto', 'sipa', 'pa'])

# ---------- excavated round houses: centre, diameter and height measured on the LiDAR wall centre lines
EXC = [loc(P) for P in WJ['exc']]
hpos = []
HOUSES = sorted(WJ['houses'], key=lambda h: (-h[1], h[0]))      # north to south, west to east
for i, (x, y, dia, hh, cv) in enumerate(HOUSES):
    c = loc([x, y]); rad = dia / 2; sid = f'H{i + 1:03d}'; hpos.append((c[0], c[1], rad))
    hA = float(np.clip(hh, .25, 1.3))
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .5, hA, .06, .3, closed=True)], 'A', 'conf')
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .5, 2.0, .02, .3, closed=True, top_taper=1)], 'B', 'hip')
    gz = float(hz(c[0], c[1])) + 2.0
    roof(sid + 'R', c, rad, gz - .3, gz + rad * 1.15, 'B', 'hip')
    item(id=sid, name=f'Casa circular {i + 1}', kind='Habitação', phase='bairros escavados', ev='conf', evB='hip', roof='hip',
         dims=f'diâmetro ≈ {dia:.1f} m (eixo do muro) · paredes ≈ 0,5 m · altura atual ≈ {hA:.1f} m (LiDAR 2025)',
         note='Muro circular visível no modelo de superfície do LiDAR (MDS − MDT); centro e diâmetro ajustados por mínimos quadrados ao eixo do muro '
              f'(o anel coincide com {cv * 100:.0f} % do eixo). Espessura das paredes de 0,40 a 0,60 m (SIPA); uma casa escavada em 1977-78 tem 4,30 m de diâmetro interior e paredes de 0,50 m (Silva e Centeno 1980). '
              'Reconstituição: paredes com 2,0 m e cobertura cónica de colmo, por paralelo com o núcleo reconstruído no local em 1995 (hipotético); portas e vestíbulos não estão representados porque não se leem no LiDAR.',
         src=['lidar', 'sipa', 'silva1980', 'orto'])
print('houses', len(HOUSES))

# ---------- walls of the yards, streets and rectangular buildings (LiDAR centre lines), grouped by 30 m cells of the quarters
from collections import defaultdict
cells = defaultdict(list)
for L in WJ['lines']:
    p = loc(L['pts']); m = p.mean(0); cells[(int((m[0] + 300) // 30), int((300 - m[1]) // 30))].append((p, L))
for n, key in enumerate(sorted(cells)):
    grp = cells[key]; sid = f'W{n + 1:02d}'
    geoA = []; geoB = []; tot = 0; hs = []
    for p, L in grp:
        pd = dense(p, .5); hv = _samp(np.where(CHM3 > 2.5, 0, CHM3), pd[:, 0], pd[:, 1]); hv = np.clip(np.where(hv > .15, hv, L['h']), .15, 1.4)
        hv = gaussian_filter1d(hv, 1.5, mode='nearest')
        geoA.append(sweep(pd, .5, hv, .03, .3, step=.5)); geoB.append(sweep(pd, .5, np.maximum(hv, 1.6), .02, .3, step=.5, top_taper=1))
        tot += L['len']; hs.append(L['h'])
    put(sid, 'Muros', stone_m, geoA, 'A', 'conf'); put(sid, 'Muros', stone_m, geoB, 'B', 'hip')
    item(id=sid, name=f'Muros de pátios, arruamentos e construções retangulares (setor {n + 1})', kind='Muro', phase='bairros escavados', ev='conf', evB='hip',
         dims=f'{len(grp)} troços · {tot:.0f} m no total · altura atual mediana ≈ {np.median(hs):.2f} m · largura 0,5 m',
         note='Eixos dos muros de pedra seca que sobressaem no modelo de superfície do LiDAR (MDS − MDT, 0,15 a 2 m) dentro das áreas escavadas, fora dos anéis das casas. '
              'Arruamentos ortogonais (principal norte–sul com cerca de 4 m, transversais de 2 a 2,5 m) e núcleos de 4-5 construções em pátio lajeado cercado por muro, com 200 a 300 m² (SIPA, Portal do Arqueólogo). '
              'Reconstituição: muros com 1,6 m, hipotética.', src=['lidar', 'sipa', 'pa'])
print('wall groups', len(cells))

# ---------- reconstructed family unit (1995, ethno-archaeological reconstruction): read from the LiDAR surface model
# One covered block (≈ 14 × 18 m) under a single-pitch roof that rises from the west wall to the east wall, with the conical roofs of two round
# houses standing out of it (5.5 and 5.9 m): as in the photographs taken from the west (Commons, H. Matos 2008), long low west wall, cones behind.
nuc_box = (84, 106, -21, 3)                       # local metres from the site point (class 6 'building' blob)
gx_ = np.arange(nuc_box[0], nuc_box[1], .25); gy_ = np.arange(nuc_box[2], nuc_box[3], .25); NX, NY = np.meshgrid(gx_, gy_)
Hn = _samp(CHM3, NX - CX, NY - CY)
tops = []
for (px, py) in [(91, -8), (92, -14)]:                 # the two conical roof tops in the surface model
    m = np.hypot(NX - px, NY - py) < 3
    k = np.argmax(np.where(m, Hn, 0)); tops.append((float(NX.flat[k]), float(NY.flat[k]), float(Hn.flat[k])))
blk = (Hn > 1.4) & (NX > 86.5) & (NX < 104) & (NY > -19) & (NY < 1.5)
qx = np.percentile(NX[blk], [1, 99]); qy = np.percentile(NY[blk], [1, 99])
lx0, lx1, ly0, ly1 = float(qx[0]), float(qx[1]) + .25, float(qy[0]), float(qy[1]) + .25
far = blk & np.all([np.hypot(NX - tx, NY - ty) > 3.6 for tx, ty, _ in tops], axis=0)
A_ = np.c_[np.ones(far.sum()), NX[far] - lx0, NY[far] - ly0]
pl, *_ = np.linalg.lstsq(A_, Hn[far], rcond=None)                # roof plane: height above the ground = a + b·(x − west) + c·(y − south)
for _ in range(2):                                              # drop the cells off the plane (gaps, eaves) and fit again
    res = Hn[far] - A_ @ pl; ok = np.abs(res) < .5; pl, *_ = np.linalg.lstsq(A_[ok], Hn[far][ok], rcond=None)
zr = lambda x, y: float(pl[0] + pl[1] * (x - lx0) + pl[2] * (y - ly0))
cones = []
for tx, ty, top in tops:     # cone radius: median over 16 directions of the distance where the surface falls back to the roof plane (+ 0.35 m)
    rs = []
    for a in np.linspace(0, 2 * np.pi, 16, endpoint=False):
        for rr_ in np.arange(.5, 4.5, .25):
            x_, y_ = tx + rr_ * math.cos(a), ty + rr_ * math.sin(a)
            if float(_samp(CHM3, x_ - CX, y_ - CY)) < zr(x_, y_) + .35: break
        rs.append(rr_)
    cones.append((tx, ty, max(float(np.median(rs)), 1.5), top)); print('cone', [round(v, 2) for v in cones[-1]], 'plane', round(zr(tx, ty), 2))
corners = [(lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1)]
cl = loc(corners); gq = [float(hz(*p)) for p in cl]
hq = [zr(*p) for p in corners]
wall_top = [gq[k] + hq[k] - .25 for k in range(4)]
geo = []
for k in range(4):                                              # perimeter walls, top just under the roof edge
    a_, b_ = cl[k], cl[(k + 1) % 4]; n_ = max(2, int(np.hypot(*(np.array(b_) - a_)) / .5))
    pts = np.linspace(a_, b_, n_); hv = np.interp(np.linspace(0, 1, n_), [0, 1], [hq[k] - .25, hq[(k + 1) % 4] - .25])
    geo.append(sweep(pts, .5, hv, .02, .3, step=.5))
nA = put('N1', 'Núcleo familiar reconstruído', stone_m, geo, 'A', 'conf')
ql = loc([(lx0 - .4, ly0 - .4), (lx1 + .4, ly0 - .4), (lx1 + .4, ly1 + .4), (lx0 - .4, ly1 + .4)])
zq = [float(hz(*cl[k])) + zr(*[(lx0 - .4, ly0 - .4), (lx1 + .4, ly0 - .4), (lx1 + .4, ly1 + .4), (lx0 - .4, ly1 + .4)][k]) for k in range(4)]
put('N1L', 'Cobertura de uma água reconstruída', th_m, [([(ql[i][0], ql[i][1], zq[i]) for i in range(4)], [(0, 1, 2, 3)], [(0, 0), (3, 0), (3, 3), (0, 3)])], 'A', 'conf')
for j, (tx, ty, rad, top) in enumerate(cones):
    c = loc([tx, ty]); g = float(_samp(DTM, c[0], c[1])) - H0
    roof(f'N1R{j}' if j else 'N1R', c, rad - .6, g + zr(tx, ty) - .1, g + top, 'A', 'conf', 'Cobertura cónica reconstruída')
hw_, he_ = zr(lx0, (ly0 + ly1) / 2), zr(lx1, (ly0 + ly1) / 2)
item(id='N1', name='Núcleo familiar reconstruído (1995)', kind='Reconstrução moderna', phase='1995', ev='conf', evB='conf',
     dims=f'bloco coberto de {lx1 - lx0:.1f} × {ly1 - ly0:.1f} m com cobertura de colmo de uma água ({hw_:.1f} m na parede poente a {he_:.1f} m na nascente), '
          f'de onde sobressaem as coberturas cónicas de duas casas redondas (topos a {cones[0][3]:.1f} e {cones[1][3]:.1f} m do chão) (LiDAR 2025)',
     note='Reconstrução etnoarqueológica de um núcleo habitacional na plataforma central, feita em 1995 (restauro e beneficiação com o programa Prodiatec, a cargo da Etnos). '
          'Volumes medidos no modelo de superfície do LiDAR de 2025 e conferidos com fotografias do Wikimedia Commons; a reconstrução tem «pormenores discutíveis» e uma área inferior à média (Lemos e Cruz 2006).',
     src=['sipa', 'wikien', 'lemos2006', 'lidar', 'commons'])
# ---------- geodetic pillar on the acropolis (highest point of the Citânia, 570 m; built in the mid-19th century)
VX = (52.3, 92.8)
vh = float(_samp(np.where(BLD, CHM3, 0), *loc(VX)))
vh = max(vh, float(np.max([_samp(CHM3, *(loc(VX) + np.array([dx, dy]))) for dx in (-1, -.5, 0, .5, 1) for dy in (-1, -.5, 0, .5, 1)])))
c = loc(VX); g = float(hz(*c))
mk = col_mat('marco', (228, 224, 214), .7)
# shape measured in the 25 cm surface model: square base 2.5 × 2.5 m and 3.1 m high, shaft 1.0 m wide to 6.0 m, top 0.5 m wide to the highest return
c = c + np.array([-.25, -.12])
vv = []; vf = []
def box(w, z0, z1):
    o = len(vv); hw = w / 2
    vv.extend([(c[0] + sx * hw, c[1] + sy * hw, z) for z in (z0, z1) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    vf.extend([(o + k, o + (k + 1) % 4, o + 4 + (k + 1) % 4, o + 4 + k) for k in range(4)] + [(o + 4, o + 5, o + 6, o + 7)])
box(2.5, g - .3, g + 3.1); box(1.0, g + 3.1, g + 6.0); box(.5, g + 6.0, g + vh)
put('V1', 'Marco geodésico', mk, [(vv, vf, [(0, 0)] * len(vv))], 'A', 'conf')
item(id='V1', name='Marco geodésico da acrópole', kind='Elemento moderno', phase='meados do séc. XIX', ev='conf', evB='conf',
     dims=f'altura ≈ {vh:.1f} m; base quadrada de 2,5 m com 3,1 m de altura e pilar de 1,0 m (LiDAR 2025) · cota do terreno ≈ {g + H0:.1f} m',
     note='No ponto mais elevado da Citânia (570 m), a acrópole. Foi construído em meados do séc. XIX e destruiu parte das paredes sul e nascente da capela de S. Romão, '
          'que fica a poente, com a necrópole medieval de 34 sepulturas (Silva e Centeno 1980). A capela e as sepulturas não estão representadas: as suas posições exatas não foram publicadas nas fontes consultadas.',
     src=['silva1980', 'lidar', 'orto'])

# ---------- trees from the LiDAR canopy height model (MDS − MDT, 25 cm): local maxima above 3 m, real heights
SITE = [(45, 190), (80, 175), (110, 140), (125, 100), (128, 50), (125, 0), (118, -60), (115, -110), (110, -150), (100, -175), (60, -185), (20, -180), (-14, -142)]
SITE = loc([tuple(p) for p in LN['M1']['pts'][::-1]] + SITE)       # rampart (west) + edge of the cleared plateau (east), approximate: only to thin the trees and colour the ground
_site = MPath(SITE); _exc = [MPath(P) for P in EXC]
rS, cS = _rc(np.array([-R, R]), np.array([R, -R])); r0_, r1_ = int(rS.min()), int(rS.max()) + 1; c0_, c1_ = int(cS.min()), int(cS.max()) + 1
CH = gaussian_filter(np.where(BLD, 0, CHM)[r0_:r1_, c0_:c1_], 2.4)
pk = (CH == maximum_filter(CH, 13)) & (CH > 3)
ys, xs = np.nonzero(pk); tp = []; TH = {}
for yy_, xx_ in zip(ys, xs):
    lx = LB['x0'] + (c0_ + xx_ + .5) * LB['cs'] - X0L; ly = LB['y1'] - (r0_ + yy_ + .5) * LB['cs'] - Y0L
    x, y = lx - CX, ly - CY
    if math.hypot(x, y) < R - 2.5: tp.append((x, y)); TH[(x, y)] = float(CHM[r0_ + yy_ - 2:r0_ + yy_ + 3, c0_ + xx_ - 2:c0_ + xx_ + 3].max())
_cg = np.linspace(-R, R, 512)
can = gaussian_filter((_samp(CHM, *np.meshgrid(_cg, -_cg)) > 2.5).astype(float), 1.2)
wallpts = np.vstack([dense(line(k)) for k, *_ in WALLS] + [dense(loc(L['pts']), 1) for L in WJ['lines']] + [np.array([[h[0], h[1]] for h in hpos])])
kd = cKDTree(wallpts)
ntp0 = len(tp)
def _keep(p):
    dw = kd.query(p)[0]
    if any(e.contains_point(p) for e in _exc): return dw > 6 and rng.random() < .1
    if _site.contains_point(p): return dw > 5 and rng.random() < .15
    return dw > 3
tp = [p for p in tp if _keep(p)]
print('lidar trees', ntp0, 'kept', len(tp))
leaf = [col_mat('leaf1', (52, 86, 40)), col_mat('leaf2', (70, 104, 46)), col_mat('leaf3', (40, 70, 38))]
exec(open('blend/_sfn_trees.py').read())      # prototypes and species rules shared with Sabroso (blend/dio_sab.py)

# undergrowth: gorse/broom at the forest edges and on the slopes, grass tufts everywhere but the structures
canm = lambda x, y: can[min(511, max(0, int((R - y) / (2 * R) * 512))), min(511, max(0, int((x + R) / (2 * R) * 512)))]
def free(x, y, dw): return math.hypot(x, y) < R - 2 and kd.query((x, y))[0] > dw
n_sh = 0
for _ in range(12000):
    x, y = (rng.random(2) * 2 - 1) * R; c_ = canm(x, y)
    if n_sh > 420 or not free(x, y, 6) or _site.contains_point((x, y)): continue
    if rng.random() < (.9 if .12 < c_ < .6 else .08):
        TREES.append([round(x, 2), round(y, 2), round(float(hz(x, y)), 2), round(1.6 + rng.random() * 1.8, 2), TYPES.index('shrub'), int(rng.integers(0, 3)), round(rng.random() * 6.28, 2)]); n_sh += 1
n_tu = 0
for _ in range(30000):
    x, y = (rng.random(2) * 2 - 1) * R
    if n_tu > 3200 or not free(x, y, 1.6): continue
    ins = any(e.contains_point((x, y)) for e in _exc)
    if rng.random() < (.15 if ins else .8):
        TREES.append([round(x, 2), round(y, 2), round(float(hz(x, y)), 2), round(.35 + rng.random() * .35, 2), TYPES.index('tuft'), int(rng.integers(0, 3)), round(rng.random() * 6.28, 2)]); n_tu += 1
print('trees', len(tp), 'shrubs', n_sh, 'tufts', n_tu, 'R', R)

# ---------- labels (empties named LBL-...)
def lbl(t, p, dz=3):
    e = bpy.data.objects.new(f'LBL-{t}-{len(bpy.data.objects)}', None); e.location = (float(p[0]), float(p[1]), float(hz(p[0], p[1])) + dz)
    bpy.context.scene.collection.objects.link(e)
lbl('Acrópole · 570 m', loc(VX), 6)
lbl('Núcleo familiar reconstruído (1995)', loc([95, -8]), 7)
lbl('Muralha', line('M1')[int(len(line('M1')) * .45)], 4)
lbl('Bairros escavados', loc([-40, 70]), 4)
lbl('Arruamento principal (norte–sul)', loc([10, 60]), 3)
lbl('Setor sul', loc([40, -130]), 3)

# ---------- ground: DGT 2021 orthophoto inside its 512 m frame (4 px/m), stylised land cover around it, AO baked
TS = 3072; mpp = 2 * R / TS
jj, ii = np.mgrid[0:TS, 0:TS]; GX = (ii + .5) * mpp - R; GY = R - (jj + .5) * mpp
def noise(sig, seed): return gaussian_filter(np.random.default_rng(seed).normal(0, 1, (TS, TS)), sig, mode='wrap')
n1 = noise(40, 1); n1 /= n1.std(); n2 = noise(10, 2); n2 /= n2.std(); n3 = noise(2, 3); n3 /= n3.std()
def m2px(p): return [((x + R) / mpp, (R - y) / mpp) for x, y in p]
def mask_draw(fn):
    im = Image.new('L', (TS, TS), 0); fn(ImageDraw.Draw(im)); return np.asarray(im, float) / 255
inside = gaussian_filter(mask_draw(lambda d: d.polygon(m2px(SITE), fill=255)), 6)
forest = gaussian_filter(np.asarray(Image.fromarray((can * 255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR), float) / 255, 8)
def lerp(a, b, t): t = np.clip(t, 0, 1)[..., None]; return a * (1 - t) + b * t
C = lambda *c: np.array(c, float)
col = lerp(C(96, 118, 52), C(132, 146, 68), .5 + .22 * n1 + .12 * n2)
col = lerp(col, C(150, 150, 92), np.clip(inside * (.75 + .06 * n2), 0, 1))
col = lerp(col, C(72, 92, 44), forest * .75 * (1 - inside * .5))
# orthophoto (site point at pixel 1024,1024, 4 px/m, north up): its colours, slightly warmed, where it exists
ORT = np.asarray(Image.open(f'app/t3/{SID}-c.jpg').convert('RGB'), float)
ox = (GX + CX) * 4 + 1024; oy = 1024 - (GY + CY) * 4
okm = (ox >= 0) & (ox < 2047) & (oy >= 0) & (oy < 2047)
orc = np.stack([map_coordinates(ORT[..., k], [np.clip(oy, 0, 2047), np.clip(ox, 0, 2047)], order=1) for k in range(3)], -1)
orc = orc * np.array([1.08, 1.06, .98]) * 1.12 + 6
edge = np.clip(np.minimum.reduce([ox, 2047 - ox, oy, 2047 - oy]) / 60, 0, 1) * okm
col = lerp(col, orc, edge * .9)
col *= (1 + .04 * n3[..., None])
rimm = np.clip((np.hypot(GX, GY) - (R - 1.2)) / 1.2, 0, 1); col = lerp(col, C(84, 104, 46), rimm)
Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(f'{TMP}/ground_raw.jpg', quality=92)
gtex.image = bpy.data.images.load(f'{TMP}/ground_raw.jpg')
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'
ao = bpy.data.images.new('ao', 1024, 1024, float_buffer=False)
an = gmat.node_tree.nodes.new('ShaderNodeTexImage'); an.image = ao; gmat.node_tree.nodes.active = an
for o in sc.objects: o.select_set(False)
for o in sc.objects:
    if o.name.startswith('B-') or o.name.startswith('PROTO'): o.hide_render = True
terrain.select_set(True); bpy.context.view_layer.objects.active = terrain
sc.world = sc.world or bpy.data.worlds.new('w')
sc.render.bake.margin = 4
bpy.ops.object.bake(type='AO')
aopx = np.array(ao.pixels[:]).reshape(1024, 1024, 4)[::-1, :, 0]
aoi = Image.fromarray((np.clip(aopx, 0, 1) * 255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.5))
A = np.asarray(aoi, float)[..., None] / 255
G = np.asarray(Image.open(f'{TMP}/ground_raw.jpg'), float) * (.72 + .28 * A)
Image.fromarray(np.clip(G, 0, 255).astype(np.uint8)).save(f'{TMP}/ground.jpg', quality=88)
gmat.node_tree.nodes.remove(an); gtex.image = bpy.data.images.load(f'{TMP}/ground.jpg')
for o in sc.objects: o.hide_render = False

# ---------- export
SOURCES = {
 "sipa": "Direção-Geral do Património Cultural, Sereno, I. e Amaral, P. (1994). Citânia de Sanfins, SIPA n.º IPA.00005093: Monumento Nacional pelo Decreto n.º 35 817 (DG n.º 187, 20-08-1946); três linhas de muralhas, com espessura máxima de c. 3,5 m junto às portas, voltadas a poente; fosso escavado no afloramento a norte e a sul; c. de 160 construções circulares e quadrangulares; núcleos de 4-5 construções em pátio lajeado cercado por muro, com 200-300 m²; paredes de 40 a 60 cm; arruamento principal norte–sul e transversais; balneário no sopé, a sudoeste; reconstrução de um núcleo habitacional (1995).",
 "pa": "Portal do Arqueólogo (DGPC), Citânia de Sanfins: quatro linhas de muralha; cerca de 15 ha; arruamento central com c. 4 m, norte–sul, e transversais de 2 a 2,5 m; ocupação do séc. V a.C. ao séc. IV d.C.; trabalhos de 1944 a 2010.",
 "silva1980": "Silva, A. C. F. e Centeno, R. M. S. (1980). Escavações arqueológicas na Citânia de Sanfins (Paços de Ferreira) 1977-1978. Portugália, nova série, 1, pp. 57-78: acrópole no ponto mais elevado, a poente do marco geodésico (570 m); casa circular com 4,30 m de diâmetro interior e paredes de 0,50 m; 34 sepulturas medievais e capela de S. Romão.",
 "lemos2006": "Lemos, F. S. e Cruz, G. (2006). Forum, 39: a unidade reconstruída de Sanfins tem «pormenores discutíveis» e uma área inferior à média.",
 "wikien": "Wikipedia (en). Citânia de Sanfins (consultada em 2026-11): reconstrução de uma casa e réplica da estátua de guerreiro em 1995.",
 "lidar": "DGT (2025). LiDAR 2025, blocos 178484, 178485, 179484 e 179485: nuvens de pontos classificadas (LO-*-07-2025_v05, ≈ 7 pontos de solo por m²) e MDT/MDS de 50 cm. Terreno de 25 cm interpolado dos pontos de solo, sem exagero vertical; muros, casas, núcleo reconstruído e árvores pelo modelo de superfície (MDS − MDT).",
 "orto": "DGT (2021). Ortofotomapa de Portugal Continental 2021 (25 cm), serviço WMS Ortos2021-RGB: textura do chão e traçado da muralha e dos muros do setor sul.",
 "commons": "Wikimedia Commons, Category:Citânia de Sanfins: fotografias de Cssantos (2010, CC BY-SA 3.0), Lídia Maria Faria (2021, CC BY-SA 4.0), José Antonio Gil Martínez (2011, CC BY 2.0), Turismoenportugal (2013, CC BY-SA 3.0) e Henrique Matos (2008, CC BY 2.5).",
}
os.makedirs('app/dio', exist_ok=True)
for o in sc.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.abspath(f'app/dio/{SID}.glb'), export_format='GLB', export_apply=True, export_yup=True,
                          export_image_format='JPEG', export_jpeg_quality=86, export_materials='EXPORT', use_selection=False, export_extras=True,
                          export_draco_mesh_compression_enable=False)
json.dump({'cat': CAT, 'sources': SOURCES, 'R': R, 'ex': EX, 'h0': H0, 'cx': CX, 'cz': -CY, 'trees': TREES, 'types': TYPES,
           'pal': {k: [list(c) for c in v] for k, v in PAL.items()}}, open(f'app/dio/{SID}.json', 'w'))
print('ok', os.path.getsize(f'app/dio/{SID}.glb'))
