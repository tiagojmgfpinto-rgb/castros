# Builds a castillos-style disc diorama of one castro in Blender (bpy) and exports a GLB for three.js.
# Usage: /opt/bvenv/bin/python blend/diorama.py <site-id>
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
P = importlib.import_module('brit_plan')
FIT = json.load(open('blend/brit_fit.json'))
rng = np.random.default_rng(11)

# ---------- panel px and orthophoto px -> local metres (x east, z south) -> Blender (x, y=-z)
mean = np.array(FIT['mean']); tx, tz, th, kk = FIT['x']; PXM = FIT['pxm']
def plan2m(p):
    q = (np.asarray(p, float) - mean) / PXM * kk; c, s = math.cos(th), math.sin(th)
    return np.stack([q[..., 0] * c - q[..., 1] * s, q[..., 0] * s + q[..., 1] * c], -1) + [tx, tz]
R1m = plan2m(P.R1)
CX, CZ = (R1m.min(0) + R1m.max(0)) / 2 + [8, 22]
BATHL = np.array([-148.0, 120.0])                  # Balneário Sul: Wikiloc point, confirmed as a terraced cut in the LiDAR ground model
R = max(float(np.max(np.hypot(R1m[:, 0] - CX, R1m[:, 1] - CZ))) + 26, float(np.hypot(*(BATHL - [CX, CZ]))) + 20)
def loc(p):  m = plan2m(p); return np.stack([m[..., 0] - CX, -(m[..., 1] - CZ)], -1)
def oloc(p): p = np.asarray(p, float); return np.stack([(p[..., 0] - 1024) / 4 - CX, -((p[..., 1] - 1024) / 4 - CZ)], -1)
def mloc(p): p = np.asarray(p, float); return np.stack([p[..., 0] - CX, -(p[..., 1] - CZ)], -1)
# ---------- terrain heights: DGT LiDAR 2025 ground model (MDT, 50 cm), lightly smoothed
from scipy.ndimage import map_coordinates
MDT = gaussian_filter(np.load('lidar/mdt.npy').astype(np.float32), .8); MDS = np.load('lidar/mds.npy').astype(np.float32)
X0L, Y0L = -15192.5388, 206428.3338                     # site point in PT-TM06
def _rc(x, y):  # Blender xy -> MDT row/col
    lx = np.asarray(x) + CX; lz = CZ - np.asarray(y)
    return (207000 - (Y0L - lz)) / .5 - .5, (X0L + lx + 16000) / .5 - .5
def hraw(x, y):
    r, c = _rc(x, y); return map_coordinates(MDT, [np.atleast_1d(r).ravel(), np.atleast_1d(c).ravel()], order=1, mode='nearest').reshape(np.shape(r))
def chm(x, y):
    r, c = _rc(x, y); a = [np.atleast_1d(r).ravel(), np.atleast_1d(c).ravel()]
    return (map_coordinates(MDS, a, order=1, mode='nearest') - map_coordinates(MDT, a, order=1, mode='nearest')).reshape(np.shape(r))
H0 = float(hraw(0, 0)); EX = 1.15
# the Balneário Sul sits in a cut in the slope: carve the ground to its floor level inside the footprint (soft edge 1.2 m)
_bc = np.array([BATHL[0] - CX, -(BATHL[1] - CZ)]); _bu = np.array([-.55, -.83]) / math.hypot(.55, .83); _bv = np.array([-_bu[1], _bu[0]])
_bfl = min(float(hraw(*(_bc + _bu * u + _bv * v))) for u in np.linspace(-5, 3, 9) for v in np.linspace(-3, 1.5, 7)) - .3
_hraw0 = hraw
def hraw(x, y):
    h = _hraw0(x, y); X_ = np.asarray(x, float) - _bc[0]; Y_ = np.asarray(y, float) - _bc[1]
    u = X_ * _bu[0] + Y_ * _bu[1]; v = X_ * _bv[0] + Y_ * _bv[1]
    du = np.maximum(np.maximum(-5.2 - u, u - 3.6), 0); dv = np.maximum(np.maximum(-3.3 - v, v - 2.2), 0); d = np.hypot(du, dv)
    t = np.clip(d / 1.2, 0, 1); return np.where(d < 1.2, np.minimum(h, _bfl * (1 - t) + h * t), h)
# house platforms: every house stands on a levelled terrace (level = ground at its centre), blended out over 1.8 m
from scipy.spatial import cKDTree as _KP
_hl = []
for (lx, lz, r, *_r) in json.load(open('blend/p15_houses.json')): _hl.append((mloc(np.array([lx, lz])), min(3.8, max(1.8, r))))
for (lx, lz, r, *_r) in json.load(open('lidar/houses.json')): _hl.append((mloc(np.array([lx, lz])), r))
for (x_, y_, r_) in P.ORTHO_HOUSES: _hl.append((oloc([x_, y_]), max(2.3, r_ / 4)))
for (x_, y_, r_) in P.RECON_HOUSES: _hl.append((oloc([x_, y_]), r_ / 4))
_hc = np.array([h[0] for h in _hl]); _hr = np.array([h[1] for h in _hl]); _hlev = np.array([float(hraw(*c)) for c in _hc]); _hk = _KP(_hc)
_hraw1 = hraw
def hraw(x, y):
    h = _hraw1(x, y); X_ = np.asarray(x, float); Y_ = np.asarray(y, float); sh = np.shape(h)
    d, i = _hk.query(np.c_[np.ravel(X_ * np.ones(sh)), np.ravel(Y_ * np.ones(sh))])
    e = d - (_hr[i] + .7); t = np.clip(e / 1.8, 0, 1); t = t * t * (3 - 2 * t)
    out = np.ravel(h * np.ones(sh)); out = np.where(e < 1.8, _hlev[i] * (1 - t) + out * t, out)
    return out.reshape(sh) if sh else float(out[0])
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
NR, NA = 200, 600
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
# fine ground patch (0.25 m) over the Balneário Sul cut, so the excavation reads at the right width
_us = np.arange(-9, 7.01, .25); _vs = np.arange(-7, 6.01, .25); PV = []; PF_ = []; PUV = []
for j, v in enumerate(_vs):
    for i, u in enumerate(_us):
        q = _bc + _bu * u + _bv * v; PV.append((q[0], q[1], float(hz(*q)) + .06)); PUV.append(tuple(uv_of(q[0], q[1])))
nu = len(_us)
for j in range(len(_vs) - 1):
    for i in range(nu - 1): k = j * nu + i; PF_.append((k, k + 1, k + nu + 1, k + nu))
patch = new_obj('terrain_bath', mesh_from('terrain_bath', PV, PF_, PUV), gmat)
for p_ in patch.data.polygons: p_.use_smooth = True

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
def sweep(pts, w, h, jitter=.25, sink=.6, closed=False, top_taper=.85, step=.8):
    p = dense(pts, step, closed=closed); n = len(p)
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
# ---------- clip helper: keep the part of a line that lies on the disc
def clip(L, r=None):
    r = r or R - 3; L = np.asarray(L, float); out = []; cur = []
    for q in dense(L, 2):
        if math.hypot(*q) < r: cur.append(q)
        elif len(cur) > 1: out.append(np.array(cur)); cur = []
        else: cur = []
    if len(cur) > 1: out.append(np.array(cur))
    return out
_st = np.asarray(Image.open('blend/stone.jpg').convert('RGB'), float); _g = np.random.default_rng(12); _hh, _ww = _st.shape[:2]
_moss = gaussian_filter(_g.normal(0, 1, (_hh, _ww)), 9); _moss = np.clip((_moss - .35) * 2.2, 0, 1)[..., None]
_lich = (gaussian_filter(_g.random((_hh, _ww)), 1.2) > .62)[..., None]
_ru = _st * .82 * (1 - _moss * .55) + np.array([78, 92, 52]) * _moss * .55
_ru = np.where(_lich, _ru * .6 + np.array([214, 210, 190]) * .4, _ru)
Image.fromarray(np.clip(_ru, 0, 255).astype(np.uint8)).save('blend/ruin.jpg', quality=88)
ruin_m, _ = img_mat('ruin', 'blend/ruin.jpg', .95)
CAT = []
def put(sid, name, mat, geo, mode, ev):
    if mode == 'A' and mat is stone_m: mat = ruin_m
    A = Acc()
    for g in geo: A.add(g)
    o = A.obj(f'{mode}-{sid}', mat)
    if o: o['sid'] = sid; o['mode'] = mode; o['ev'] = ev
    return o
def item(**k): CAT.append(k)
th_m, _ = img_mat('thatch', 'blend/thatch.jpg', 1)
cyl = lambda c, rad, n=28: [(c[0] + math.cos(a) * rad, c[1] + math.sin(a) * rad) for a in np.linspace(0, 2 * np.pi, n + 1)[:-1]]
def roof(c, rad, wall_h, sid, ev='hip', rise=1.15, over=.6):
    gz = float(hz(c[0], c[1])) + wall_h; rr2 = rad + over; hr = rad * rise
    rv = [(c[0], c[1], gz + hr)] + [(c[0] + math.cos(k / 24 * 2 * np.pi) * rr2, c[1] + math.sin(k / 24 * 2 * np.pi) * rr2, gz - .3) for k in range(24)]
    return (rv, [(0, 1 + k, 1 + (k + 1) % 24) for k in range(24)], [(.5, .5)] + [(k / 24 * 3, 1.5) for k in range(24)])
from scipy.spatial import cKDTree as _KD
_ro = json.load(open('osm/mask_sites.json'))[SID]['rl']
_rp = [(mloc(np.array(r_[1:], float).reshape(-1, 2)), max(5, r_[0])) for r_ in _ro if r_[0] >= 4]
_rd = np.vstack([dense(p_, 1.0) for p_, w_ in _rp]) if _rp else np.zeros((1, 2)) + 1e6
_rw = np.concatenate([np.full(len(dense(p_, 1.0)), w_) for p_, w_ in _rp]) if _rp else np.ones(1)
_rkd = _KD(_rd)
def offroad(segs, pad=1.5):
    out = []
    for sg in segs:
        d_, i_ = _rkd.query(sg); ok = d_ > _rw[i_] * .45 + pad; cur = []
        for q, k in zip(sg, ok):
            if k: cur.append(q)
            else:
                if len(cur) > 1: out.append(np.array(cur))
                cur = []
        if len(cur) > 1: out.append(np.array(cur))
    return out
# ramparts (Cardoso 1938: three rings of walls, about 2 m thick; a fourth wall to the north)
RAMP = [('M1', P.R1 + [P.R1[0]], 'Primeira muralha', 'conf', 2.0, 1.6, 3.5,
         'Traçado do painel do sítio, coincidente com a muralha registada no OpenStreetMap (erro médio do alinhamento ≈ 8 m). Define a elipse de cerca de 250 × 150 m que envolve o núcleo habitado (Cardoso 1938).', ['painel', 'osm', 'cardoso1938']),
        ('M2', P.R2 + [P.R2[0]], 'Segunda muralha', 'conf', 2.0, 1.4, 3.2,
         'Traçado do painel; o troço poente coincide com a muralha registada no OpenStreetMap.', ['painel', 'osm', 'cardoso1938']),
        ('M3', P.R3, 'Terceira muralha (troço poente e norte)', 'doc', 2.0, 1.0, 3.0,
         'Traçado esquemático do painel, aproximado: a posição exata no terreno não foi verificada.', ['painel', 'cardoso1938']),
        ('M3E', P.R3E, 'Terceira muralha (troço nascente)', 'doc', 2.0, 1.0, 3.0,
         'Traçado esquemático do painel, aproximado.', ['painel', 'cardoso1938'])]
for sid, L, name, ev, w, h, hb, note, src in RAMP:
    segs = offroad(clip(loc(L)))
    if not segs: continue
    put(sid, name, stone_m, [sweep(sg, w, h, .3, step=2.2) for sg in segs], 'A', ev)
    put(sid, name, stone_m, [sweep(sg, w, hb, .1, top_taper=.92, step=2.2) for sg in segs], 'B', 'hip')
    item(id=sid, name=name, kind='Muralha', phase='—', ev=ev, evB='hip', dims=f'espessura ≈ {w:g} m (Cardoso 1938) · altura representada {h:g} m · reconstituição {hb:g} m',
         note=note + ' A altura original não está publicada: o valor da reconstituição é hipotético.', src=src)
# gates: openings marked with two stone jambs
for i, (n, x, y) in enumerate(P.GATES):
    c = loc([x, y])[0] if np.ndim(loc([x, y])) > 1 else loc([x, y])
    if math.hypot(*c) > R - 4: continue
    item(id=f'G{i + 1}', name=n, kind='Porta', phase='—', ev='doc', evB='doc', dims='—', note='Posição assinalada no painel do sítio (n.º 6); não modelada como estrutura, apenas identificada.', src=['painel'])
# main paved streets (panel n.º 7): flat stone strips 3 m wide
pave_m = col_mat('paving', (176, 168, 152), .9)
def road_strip(pts, w=6.0):
    p = dense(pts, 1.0); d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9; nr = np.stack([-d[:, 1], d[:, 0]], 1)
    V = []; F = []; UV = []; n = len(p); prof = [-w / 2 - .9, -w / 2, w / 2, w / 2 + .9]; pv = [0, .06, .94, 1]
    s_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
    for i in range(n):
        zs = [float(hz(*(p[i] + nr[i] * o + d[i] * l))) for o in np.linspace(-w / 2 - 1, w / 2 + 1, 5) for l in (-1, 0, 1)]
        zt = max(zs) + .15
        for j, o in enumerate(prof):
            q = p[i] + nr[i] * o; V.append((q[0], q[1], zt if j in (1, 2) else float(hz(*q)) - .4)); UV.append((s_[i] / 12, pv[j]))
    for i in range(n - 1):
        for j in range(3): a_ = i * 4 + j; F.append((a_, a_ + 1, a_ + 5, a_ + 4))
    return V, F, UV
def strip(pts, w=3.0, lift=.12):
    p = dense(pts, 1.0); d = np.gradient(p, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9; nr = np.stack([-d[:, 1], d[:, 0]], 1)
    V = []; F = []
    for i in range(len(p)):
        for sg in (-1, 1):
            x_, y_ = p[i, 0] + nr[i, 0] * w / 2 * sg, p[i, 1] + nr[i, 1] * w / 2 * sg; V.append((x_, y_, float(hz(x_, y_)) + lift))
    for i in range(len(p) - 1): a = i * 2; F.append((a, a + 1, a + 3, a + 2))
    return V, F, [(0, 0)] * len(V)
_avoid = [oloc([x_, y_]) for x_, y_, r_ in P.RECON_HOUSES] + [oloc([P.CHAPEL[0], P.CHAPEL[1]])]
def away(segs, rr=6.5):
    out = []
    for sg in segs:
        cur = []
        for q in sg:
            if min(math.hypot(*(q - a_)) for a_ in _avoid) > rr: cur.append(q)
            else:
                if len(cur) > 1: out.append(np.array(cur))
                cur = []
        if len(cur) > 1: out.append(np.array(cur))
    return out
for i, L in enumerate(P.WAYS):
    sid = f'S{i + 1}'
    put(sid, 'Rua principal', pave_m, [strip(sg) for sg in away(offroad(clip(loc(L))))], 'AB', 'doc')
    item(id=sid, name='Rua principal lajeada', kind='Arruamento', phase='—', ev='doc', evB='doc', dims='largura representada ≈ 3 m',
         note='Traçado das ruas principais do painel (n.º 7), esquemático. Uma delas é acompanhada pela conduta de água, em pedra, de 320 m que abastecia o Balneário Sul (Cruz & Antunes 2010-11).', src=['painel', 'cruz2011'])
# round houses measured on the orthophoto (Cardoso 1938: internal diameter about 5 m, walls 40–50 cm)
hpos = []
# round houses from the general survey plan (Unidade de Arqueologia da U. Minho, "Levantamento geral, sectores de intervenção"),
# georeferenced on the two rebuilt houses and the chapel (residual < 1 m)
for i, (lx, lz, r, sc_, px_, py_) in enumerate(json.load(open('blend/p15_houses.json'))):
    c = mloc(np.array([lx, lz])); rad = float(np.clip(r, 1.8, 3.8))
    if math.hypot(*c) > R - 3 or min(math.hypot(*(c - oloc([x_, y_]))) for x_, y_, r_ in P.RECON_HOUSES) < 5: continue
    sid = f'P{i + 1:03d}'; hpos.append((c[0], c[1], rad))
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .45, .6 + rng.random() * .35, .1, .9, closed=True)], 'A', 'conf')
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .45, 2.1, .02, .9, closed=True, top_taper=1)], 'B', 'hip')
    ro = put(sid + 'R', 'Cobertura', th_m, [roof(c, rad, 2.1, sid)], 'B', 'hip')
    if ro:
        for p_ in ro.data.polygons: p_.use_smooth = True
    item(id=sid, name=f'Casa circular (planta) {i + 1}', kind='Habitação', phase='—', ev='conf', evB='hip', roof='hip', dims=f'diâmetro ≈ {2 * rad:.1f} m (medido na planta)',
         note='Casa circular desenhada no levantamento geral da Citânia (Unidade de Arqueologia da Universidade do Minho), georreferenciado pelas duas casas reconstruídas e pela capela (erro < 1 m). Cardoso (1938): casas redondas com cerca de 5 m de diâmetro interior, cobertura cónica de colmo. Altura de reconstituição e cobertura hipotéticas.', src=['plan', 'cardoso1938'])
nph = len([h for h in hpos])
for i, (x, y, r) in enumerate(P.ORTHO_HOUSES):
    c = oloc([x, y]); rad = max(2.3, r / 4)
    if any(math.hypot(c[0] - q[0], c[1] - q[1]) < max(rad, q[2]) * 1.3 for q in hpos): continue
    hpos.append((c[0], c[1], rad)); sid = f'H{i + 1:02d}'
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .45, .6 + rng.random() * .35, .1, .9, closed=True)], 'A', 'conf')
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .45, 2.1, .02, .9, closed=True, top_taper=1)], 'B', 'hip')
    ro = put(sid + 'R', 'Cobertura', th_m, [roof(c, rad, 2.1, sid)], 'B', 'hip')
    if ro:
        for p_ in ro.data.polygons: p_.use_smooth = True
    item(id=sid, name=f'Casa circular {i + 1}', kind='Habitação', phase='—', ev='conf', evB='hip', roof='hip', dims=f'diâmetro ≈ {2 * rad:.1f} m (medido na ortofoto)',
         note='Muro circular visível na ortofoto de 2021. Cardoso (1938): casas redondas com cerca de 5 m de diâmetro interior, paredes de 40–50 cm, coluna central de madeira e cobertura cónica de colmo (ou telha, na fase romanizada). A altura das paredes e a posição das portas não estão medidas.',
         src=['dgt', 'cardoso1938'])
LH = json.load(open('lidar/houses.json')); nlh = 0
for (lx, lz, r, cov, h) in LH:
    c = mloc(np.array([lx, lz])); 
    if math.hypot(*c) > R - 4 or any(math.hypot(c[0] - q[0], c[1] - q[1]) < max(r, q[2]) * 1.2 for q in hpos): continue
    if min(math.hypot(*(c - oloc([x_, y_]))) for x_, y_, r_ in P.RECON_HOUSES) < 9: continue
    nlh += 1; sid = f'L{nlh:02d}'; rad = float(r); hpos.append((c[0], c[1], rad))
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .45, max(.4, min(1.4, float(h))), .05, .3, closed=True)], 'A', 'conf')
    put(sid, 'Casa', stone_m, [sweep(cyl(c, rad), .45, 2.1, .02, .9, closed=True, top_taper=1)], 'B', 'hip')
    ro = put(sid + 'R', 'Cobertura', th_m, [roof(c, rad, 2.1, sid)], 'B', 'hip')
    if ro:
        for p_ in ro.data.polygons: p_.use_smooth = True
    item(id=sid, name=f'Casa circular (LiDAR) {nlh}', kind='Habitação', phase='—', ev='conf', evB='hip', roof='hip', dims=f'diâmetro ≈ {2 * rad:.1f} m · altura do muro medida ≈ {float(h):.1f} m',
         note=f'Círculo ajustado a um muro medido no LiDAR da DGT (2025, 50 cm), com {int(cov)}° do anel visíveis. Cardoso (1938): casas redondas com cerca de 5 m de diâmetro interior. Altura de reconstituição e cobertura hipotéticas.', src=['lidar', 'cardoso1938'])
print('lidar houses', nlh)
# the two houses rebuilt by Martins Sarmento (19th c.): standing, in both modes
for i, (x, y, r) in enumerate(P.RECON_HOUSES):
    c = oloc([x, y]); rad = r / 4; sid = f'RH{i + 1}'; hpos.append((c[0], c[1], rad))
    # proportions from a photograph of the two houses: closed dry-stone drum (~2.5 m), thick low straw cone with a rounded eave,
    # rectangular doorway with granite jambs and lintel set flush in the wall, dark green wooden door
    WH = 2.5; ang0 = math.radians([-70, 200][i]); dx, dy = math.cos(ang0), math.sin(ang0); tx_, ty_ = -dy, dx
    ring = cyl(c, rad, 48)
    g = [sweep(ring, .55, WH, .0, .3, closed=True, top_taper=1)]
    door = (c[0] + dx * (rad + .29), c[1] + dy * (rad + .29)); gz_ = float(hz(*door))
    def box(u0, u1, z0, z1, t0=0, t1=.08):
        V = [(door[0] + tx_ * u + dx * t, door[1] + ty_ * u + dy * t, gz_ + z) for z in (z0, z1) for u, t in [(u0, t0), (u1, t0), (u1, t1), (u0, t1)]]
        return V, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], [(0, 0)] * 8
    frame = [box(-.66, -.46, -.1, 1.72), box(.46, .66, -.1, 1.72), box(-.76, .76, 1.72, 1.98)]
    put(sid, 'Casa reconstruída', stone_m, g + frame, 'AB', 'conf')
    put(sid, 'Porta', col_mat(f'door{i}', (38, 66, 50), .7), [box(-.46, .46, 0, 1.72, .0, .05)], 'AB', 'conf')
    # thatch: apex, upper slope, rounded eave (two rings), underside back to the wall top
    gz = float(hz(c[0], c[1])) + WH; N_ = 32
    rings = [(rad + .55, gz + .2), (rad + .62, gz - .15), (rad + .4, gz - .42), (rad - .1, gz - .2)]
    RV = [(c[0], c[1], gz + rad * .62)]
    for rr_, zz_ in rings:
        RV += [(c[0] + math.cos(k / N_ * 2 * np.pi) * rr_, c[1] + math.sin(k / N_ * 2 * np.pi) * rr_, zz_) for k in range(N_)]
    RF = [(0, 1 + k, 1 + (k + 1) % N_) for k in range(N_)]
    for j in range(len(rings) - 1):
        o0, o1 = 1 + j * N_, 1 + (j + 1) * N_
        RF += [(o0 + k, o1 + k, o1 + (k + 1) % N_, o0 + (k + 1) % N_) for k in range(N_)]
    ro = put(sid + 'R', 'Cobertura', th_m, [(RV, RF, [(0, 0)] + [(k / N_ * 4, j * .3) for j in range(len(rings)) for k in range(N_)])], 'AB', 'conf')
    if ro:
        for p_ in ro.data.polygons: p_.use_smooth = True
    item(id=sid, name=f'Casa reconstruída por Martins Sarmento ({i + 1})', kind='Reconstrução (séc. XIX)', phase='séc. XIX', ev='conf', evB='conf', dims=f'diâmetro ≈ {2 * rad:.1f} m (medido na ortofoto)',
         note='Uma das duas casas circulares reconstruídas por Martins Sarmento, junto à «Casa da Espiral» e à plataforma da capela de São Romão (Cruz & Antunes 2010-11). Visível na ortofoto com a cobertura cónica. Proporções (parede ≈ 2,6 m, cobertura baixa de colmo com beiral, porta com ombreiras e lintel de granito) tiradas de fotografia atual.', src=['cruz2011', 'dgt'])
# Casa do Conselho (panel n.º 8): large round building
cc = loc([P.COUNCIL[0], P.COUNCIL[1]]); crad = 5.5; hpos.append((cc[0], cc[1], crad))
put('CC', 'Casa do Conselho', stone_m, [sweep(cyl(cc, crad, 40), .7, .9, .1, .3, closed=True), sweep(cyl(cc, crad - .9, 40), .6, .45, .05, .2, closed=True)], 'A', 'doc')
put('CC', 'Casa do Conselho', stone_m, [sweep(cyl(cc, crad, 40), .7, 2.4, .02, .3, closed=True, top_taper=1), sweep(cyl(cc, crad - .9, 40), .6, .45, .05, .2, closed=True)], 'B', 'hip')
item(id='CC', name='«Casa do Conselho»', kind='Edifício comunitário', phase='—', ev='doc', evB='hip', dims='diâmetro representado ≈ 11 m, com banco corrido interior',
     note='Edifício circular de grandes dimensões assinalado no painel (n.º 8). A posição vem do painel (aproximada); o diâmetro e o banco interior são uma representação, não uma medição.', src=['painel'])
rect = lambda c, L_, W_, ca, sa: [(c[0] + ca * u - sa * v, c[1] + sa * u + ca * v) for u, v in [(-L_ / 2, -W_ / 2), (L_ / 2, -W_ / 2), (L_ / 2, W_ / 2), (-L_ / 2, W_ / 2)]]
def block(c, L_, W_, rot, h, lift_roof=.6):
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot)); q = rect(c, L_, W_, ca, sa); g = min(float(hz(x_, y_)) for x_, y_ in q)
    V = [(x_, y_, g - .5) for x_, y_ in q] + [(x_, y_, g + h) for x_, y_ in q]
    m1 = ((q[0][0] + q[3][0]) / 2, (q[0][1] + q[3][1]) / 2); m2 = ((q[1][0] + q[2][0]) / 2, (q[1][1] + q[2][1]) / 2)
    V += [(m1[0], m1[1], g + h + lift_roof), (m2[0], m2[1], g + h + lift_roof)]
    F = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]; FR = [(4, 5, 9, 8), (6, 7, 8, 9), (5, 6, 9), (7, 4, 8)]
    return (V, F, [(0, 0)] * len(V)), (V, FR, [(0, 0)] * len(V))
wall_w = col_mat('render', (226, 222, 212), .9); roof_m = col_mat('modernroof', (150, 146, 138), .8)
W_, Rf = [], []
for (x_, y_, L_, Wd, rot, h) in P.RECEPTION:
    a_, b_ = block(oloc([x_, y_]), L_ / 4, Wd / 4, rot, h); W_.append(a_); Rf.append(b_)
put('CR', 'Centro de receção', wall_w, W_, 'A', 'conf'); put('CRR', 'Cobertura', roof_m, Rf, 'A', 'conf')
bc = oloc([P.RECEPTION[0][0], P.RECEPTION[0][1]])
item(id='CR', name='Centro de receção', kind='Edifício moderno', phase='atual', ev='conf', evB='conf', dims='≈ 17 × 12 m mais um corpo anexo (medido na ortofoto)',
     note='Edifício de apoio aos visitantes junto à entrada do sítio, onde se compram os bilhetes. Posição e planta medidas na ortofoto de 2021, junto ao ponto «Você está aqui» do painel; alturas aproximadas. Aparece só no estado atual.', src=['dgt', 'painel'])
# Balneário Sul: position from the Wikiloc point "Balneário Sul e Pedra Formosa", confirmed by a rectangular cut in the LiDAR ground model.
# Form after current photographs: a paved corridor (atrium/antechamber) between walls of large granite blocks, a narrower paved
# compartment on its left, the Pedra Formosa closing the corridor (gabled slab, low arched opening, carved arcs and triskele),
# the rocky mound of the oven chamber behind it, and a modern steel water channel along the left side.
from PIL import ImageDraw as _ID
_t = Image.new('RGB', (512, 448), (118, 114, 106)); _d = _ID.Draw(_t)
_n = np.random.default_rng(3).normal(0, 9, (448, 512, 1)); _t = Image.fromarray(np.clip(np.asarray(_t, float) + _n, 0, 255).astype(np.uint8)); _d = _ID.Draw(_t)
for k, (rx, ry) in enumerate([(200, 150), (165, 118), (130, 86)]):
    _d.arc([256 - rx, 448 - 40 - ry * 2, 256 + rx, 448 - 40], 180, 360, fill=(70, 66, 60), width=7)
_d.arc([256 - 220, 120, 256 + 220, 300], 200, 340, fill=(70, 66, 60), width=6)
for cx_, cy_ in [(66, 300), (446, 300)]:
    for t_ in np.linspace(0, 12, 60): pass
    _d.arc([cx_ - 22, cy_ - 22, cx_ + 22, cy_ + 22], 0, 300, fill=(70, 66, 60), width=5); _d.arc([cx_ - 10, cy_ - 10, cx_ + 10, cy_ + 10], 0, 300, fill=(70, 66, 60), width=4)
for k in range(3):   # triskele near the top
    a0 = k * 2.094; _d.arc([256 - 30 + 18 * math.cos(a0), 70 - 30 + 18 * math.sin(a0), 256 + 30 + 18 * math.cos(a0), 70 + 30 + 18 * math.sin(a0)], math.degrees(a0) + 90, math.degrees(a0) + 260, fill=(66, 62, 56), width=6)
_d.ellipse([256 - 40, 30, 256 + 40, 110], outline=(66, 62, 56), width=5)
_t.save('blend/pedraformosa.jpg', quality=90)
pf_m, _ = img_mat('pedraformosa', 'blend/pedraformosa.jpg', .9)
bcen = mloc(BATHL); ux, uy = -.55, -.83; nn_ = math.hypot(ux, uy); ux, uy = ux / nn_, uy / nn_; vx, vy = -uy, ux
P_ = lambda u, v: (bcen[0] + ux * u + vx * v, bcen[1] + uy * u + vy * v)
gfl = (_bfl - H0) * EX     # floor level of the cut
def blk(u0, u1, v0, v1, z0, z1, rot=0):
    q = [P_(u0, v0), P_(u1, v0), P_(u1, v1), P_(u0, v1)]
    V = [(x_, y_, gfl + z) for z in (z0, z1) for x_, y_ in q]
    return V, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], [(0, 0), (1, 0), (1, 1), (0, 1)] * 2
walls_ = []
for k, u0 in enumerate(np.arange(-4.0, 2.0, 1.2)):           # right side of the corridor: large blocks
    walls_.append(blk(u0, u0 + 1.15, .95, 1.5, -.1, .95 + .15 * ((k * 7) % 3) / 2))
for k, u0 in enumerate(np.arange(-4.0, 2.0, 1.2)):           # left side, shared with the side compartment
    walls_.append(blk(u0, u0 + 1.15, -1.45, -.95, -.1, .85 + .1 * ((k * 5) % 3) / 2))
for k, u0 in enumerate(np.arange(-4.0, -.4, 1.2)):           # outer wall of the side compartment
    walls_.append(blk(u0, u0 + 1.15, -2.9, -2.45, -.1, .7))
walls_ += [blk(.4, .95, -2.9, -.95, -.1, .9), blk(.5, 1.3, .95, 1.9, -.1, 1.25), blk(.5, 1.3, -1.9, -.95, -.1, 1.25)]   # inner screen blocks before the stone
put('BS', 'Balneário Sul', stone_m, walls_, 'AB', 'doc')
floor_ = [blk(-4.3, 1.6, -.95, .95, -.05, .1), blk(-4.3, .4, -2.45, -1.45, -.05, .1)]
put('BS', 'Lajeado do balneário', pave_m, floor_, 'AB', 'conf'); hpos.append((bcen[0], bcen[1], 9.0))
# the Pedra Formosa: gabled outline with the arched opening, extruded 0.3 m
out2 = [(-1.15, 0), (-.24, 0)] + [(.24 * math.cos(t), .5 * math.sin(t) if False else .24 * math.sin(t) + .0) for t in np.linspace(math.pi, 0, 12)][1:-1] + [(.24, 0), (1.15, 0), (1.15, 1.2), (0, 1.95), (-1.15, 1.2)]
V = []; F = []; UV = []
for du in (1.6, 1.9):
    for (x2, z2) in out2:
        x_, y_ = P_(du, x2); V.append((x_, y_, gfl + z2)); UV.append(((x2 + 1.15) / 2.3, z2 / 1.95))
n2 = len(out2); F.append(tuple(range(n2))[::-1]); F.append(tuple(range(n2, 2 * n2)))
for k in range(n2): F.append((k, (k + 1) % n2, n2 + (k + 1) % n2, n2 + k))
put('PF', 'Pedra Formosa', pf_m, [(V, F, UV)], 'AB', 'conf')
# rocky mound of the oven chamber behind the stone
bmb = bmesh.new()
for k in range(6):
    tmp = bmesh.new(); bmesh.ops.create_icosphere(tmp, subdivisions=2, radius=1); cu = 2.9 + rng.random() * 1.2; cv = (rng.random() - .5) * 2.4
    scl = np.array([.55 + rng.random() * .4, .5 + rng.random() * .4, .4 + rng.random() * .3]); c_ = P_(cu, cv)
    for vv in tmp.verts:
        q = np.array(vv.co) * scl; vv.co = (c_[0] + q[0], c_[1] + q[1], gfl + .7 + q[2])
    m_ = bpy.data.meshes.new('t'); tmp.to_mesh(m_); tmp.free(); bmb.from_mesh(m_); bpy.data.meshes.remove(m_)
me3 = bpy.data.meshes.new('ovenmound'); bmb.to_mesh(me3); bmb.free(); ov = new_obj('AB-BSO', me3, col_mat('mossgranite', (110, 112, 96), .95)); ov['sid'] = 'BS'; ov['mode'] = 'AB'; ov['ev'] = 'hip'
# modern steel water channel along the left side, running uphill
ch_ = [P_(u, -3.6) for u in (-6.5, 0, 3.5, 6.5)]
cg = []
for a_, b_ in zip(ch_[:-1], ch_[1:]):
    for off in (-.18, .18):
        cg.append(sweep([np.array(a_) + [vx * off, vy * off], np.array(b_) + [vx * off, vy * off]], .06, .3, 0, -.05, top_taper=1))
    cg.append(strip(np.array([a_, b_]), w=.36, lift=.06))
put('BSC', 'Calha moderna', col_mat('steel', (176, 182, 186), .35), cg, 'A', 'conf')
item(id='BS', name='Balneário Sul', kind='Balneário', phase='—', ev='doc', evB='doc', dims='corredor lajeado ≈ 6 × 1,9 m, com compartimento lateral ≈ 4,7 × 1 m',
     note='Balneário castrejo junto à estrada, posto a descoberto em 1930 na abertura da EN 309 e restaurado nesse ano. Localização: ponto «Balneário Sul e Pedra Formosa» (Wikiloc), confirmado por um corte retangular na encosta no modelo do terreno LiDAR. A forma (corredor lajeado entre muros de grandes blocos, compartimento lateral e pedra formosa ao fundo) segue fotografias atuais; as medidas são aproximadas. A câmara de forno, atrás da pedra, está representada apenas como o monte de pedras visível hoje. A água chegava por uma conduta em pedra de 320 m vinda de uma mina na encosta nascente.', src=['lidar', 'cardoso1935', 'cruz2011'])
item(id='PF', name='Pedra formosa do Balneário Sul', kind='Balneário', phase='—', ev='conf', evB='conf', dims='≈ 2,3 m de largura × 1,95 m de altura (estimado por fotografia)',
     note='Pedra formosa conservada no local, entre a antecâmara e a câmara (Cruz & Antunes 2010-11): laje de remate em empena, com a pequena abertura em arco na base e decoração gravada de arcos concêntricos, espirais e um trisquel. A decoração está representada de forma simplificada. A Pedra Formosa mais conhecida, recolhida há séculos, está no Museu de Guimarães; há quem a atribua ao Balneário Este.', src=['cruz2011', 'cardoso1935'])
item(id='BSC', name='Calha de água (moderna)', kind='Infraestrutura moderna', phase='atual', ev='conf', evB='conf', dims='—', note='Calha metálica de escoamento junto ao balneário, visível nas fotografias atuais. Aparece só no estado atual.', src=[])
# Balneário nascente (panel n.º 9)
be = loc([P.BATH[0], P.BATH[1]])
if math.hypot(*be) < R - 4:
    put('BE', 'Balneário nascente', stone_m, [sweep(rect(be, 7, 4, 1, 0), .7, .9, .05, .3, closed=True)], 'A', 'doc')
    item(id='BE', name='Balneário nascente', kind='Balneário', phase='—', ev='doc', evB='doc', dims='representação esquemática',
         note='Assinalado no painel (n.º 9); escavado por Cruz & Antunes, que o consideram o possível local original da Pedra Formosa, como já propunha Cardoso (1935). Forma e dimensões não modeladas com rigor.', src=['painel', 'cardoso1935'])
# Capela de São Romão, after a photograph of its façade: square body of granite ashlar, moulded cornice, stone pyramid roof
# with an iron cross, green double door with a lattice top, an inscribed stone above it; a lower lean-to annex with a tiled roof on the left
def ashlar(path):
    g_ = np.random.default_rng(4); W_, H_ = 512, 512; img = np.zeros((H_, W_, 3)); y = 0
    while y < H_:
        rh = int(g_.integers(34, 56)); x = -int(g_.integers(0, 60))
        while x < W_:
            bw = int(g_.integers(60, 130)); t = g_.random(); c_ = np.array([222, 212, 192]) * (.9 + .14 * t) + np.array([18, 6, -6]) * (g_.random() < .3)
            img[y:y + rh, max(0, x):x + bw] = c_ + g_.normal(0, 7, (min(rh, H_ - y), min(x + bw, W_) - max(0, x), 3)); x += bw
            img[y:y + rh, max(0, x - 3):max(0, x)] = (110, 104, 96)
        img[min(H_ - 1, y + rh - 3):y + rh] = (110, 104, 96); y += rh
    Image.fromarray(np.clip(gaussian_filter(img, (.6, .6, 0)), 0, 255).astype(np.uint8)).save(path, quality=88)
ashlar('blend/ashlar.jpg'); ash_m, _ = img_mat('ashlar', 'blend/ashlar.jpg', .85)
chx, chy, chs, chr_ = P.CHAPEL; ch = oloc([chx, chy]); side = chs / 4
# façade towards the rebuilt houses and the path (south-east), annex on the left of the façade
fd = np.array([1.0, -1.0]) / math.sqrt(2); lt = np.array([fd[1], -fd[0]])            # façade normal, left vector (seen from outside)
Q = lambda u, v: (ch[0] + fd[0] * u + lt[0] * v, ch[1] + fd[1] * u + lt[1] * v)
g0 = min(float(hz(*Q(u, v))) for u in (-side / 2, side / 2) for v in (-side / 2, side / 2)); wallH = 3.4; pyrH = 3.9; h2 = side / 2
def boxq(u0, u1, v0, v1, z0, z1, uvs=3.0):
    q = [Q(u0, v0), Q(u1, v0), Q(u1, v1), Q(u0, v1)]; V = [(x_, y_, g0 + z) for z in (z0, z1) for x_, y_ in q]
    F = [(0, 1, 2, 3)[::-1], (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    L = [abs(u1 - u0), abs(v1 - v0)]
    UV = [(0, z0 / uvs), (L[0] / uvs, z0 / uvs), (L[0] / uvs + L[1] / uvs, z0 / uvs), (0, z0 / uvs)] + [(0, z1 / uvs), (L[0] / uvs, z1 / uvs), (L[0] / uvs + L[1] / uvs, z1 / uvs), (0, z1 / uvs)]
    return V, F, UV
parts = [boxq(-h2, h2, -h2, h2, -.4, wallH), boxq(-h2 - .25, h2 + .25, -h2 - .25, h2 + .25, wallH - .05, wallH + .3),   # body and cornice
         boxq(-h2 - .2, h2 + .2, -h2 - .2, h2 + .2, -.4, .25)]                                                           # plinth step
cq = [Q(-h2 - .15, -h2 - .15), Q(h2 + .15, -h2 - .15), Q(h2 + .15, h2 + .15), Q(-h2 - .15, h2 + .15)]
PV = [(x_, y_, g0 + wallH + .3) for x_, y_ in cq] + [(ch[0], ch[1], g0 + wallH + .3 + pyrH)]
parts.append((PV, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)], [(0, 0), (side / 2, 0), (side, 0), (side * 1.5, 0), (side / 4, pyrH / 2)]))
# annex: lower body on the left side, mono-pitch tiled roof
parts.append(boxq(-h2 + .3, h2 - .6, h2, h2 + 2.6, -.4, 2.3))
put('CH', 'Capela de São Romão', ash_m, parts, 'A', 'conf')
tile_m = col_mat('tiles', (168, 92, 64), .8)
aq = [Q(-h2 + .1, h2), Q(h2 - .4, h2), Q(h2 - .4, h2 + 2.85), Q(-h2 + .1, h2 + 2.85)]
RV2 = [(aq[0][0], aq[0][1], g0 + 2.75), (aq[1][0], aq[1][1], g0 + 2.75), (aq[2][0], aq[2][1], g0 + 2.2), (aq[3][0], aq[3][1], g0 + 2.2)]
put('CH', 'Telhado do anexo', tile_m, [(RV2, [(0, 1, 2, 3), (3, 2, 1, 0)], [(0, 0)] * 4)], 'A', 'conf')
door_m = col_mat('chapeldoor', (28, 112, 62), .6); dark_m = col_mat('iron', (36, 34, 32), .5)
fu = h2 + .02
put('CH', 'Porta da capela', door_m, [boxq(fu - .02, fu + .04, -.65, .65, .25, 2.45)], 'A', 'conf')
put('CH', 'Grades e cruz', dark_m, [boxq(fu + .04, fu + .06, -.6 + k * .3, -.57 + k * .3, 1.75, 2.4) for k in range(5)] + [boxq(fu + .04, fu + .06, -.62, .62, 2.05, 2.08), boxq(fu + .04, fu + .06, -.03, .03, .3, 2.4),
     boxq(-.05, .05, -.05, .05, wallH + .3 + pyrH - .1, wallH + .3 + pyrH + 1.0), boxq(-.05, .05, -.38, .38, wallH + .3 + pyrH + .55, wallH + .3 + pyrH + .65)], 'A', 'conf')
put('CH', 'Lintel e pedra inscrita', ash_m, [boxq(fu - .02, fu + .08, -.8, .8, 2.45, 2.7), boxq(fu - .02, fu + .08, -.85, -.65, .25, 2.45), boxq(fu - .02, fu + .08, .65, .85, .25, 2.45),
     boxq(fu - .02, fu + .1, -.6, .6, 2.8, 3.15)], 'A', 'conf')
item(id='CH', name='Capela de São Romão', kind='Edifício moderno', phase='época moderna', ev='conf', evB='conf', dims=f'corpo ≈ {side:.1f} × {side:.1f} m (ortofoto); alturas aproximadas',
     note='Capela no topo do monte: corpo quadrado em cantaria de granito com cornija, telhado em pirâmide de pedra rematado por uma cruz de ferro, porta verde de duas folhas com grade na parte superior e pedra inscrita por cima; anexo mais baixo com telhado de telha. Forma segundo fotografia atual; a orientação da fachada (para as casas reconstruídas) é aproximada. É posterior ao povoado: aparece só no estado atual.', src=['dgt', 'cruz2011'])
# walls measured by LiDAR in the clearings (surface model minus ground model): stone walls 0.2–3 m high
from matplotlib.path import Path as MPath
_r2 = MPath(loc(P.R2)); excl = [oloc([P.CHAPEL[0], P.CHAPEL[1]]), oloc([P.RECEPTION[0][0], P.RECEPTION[0][1]])] + [oloc([x, y]) for x, y, r in P.RECON_HOUSES]
PW = [mloc(np.array(w_, float)) for w_ in json.load(open('blend/p15_walls.json'))]
PW = [w_ for w_ in PW if len(w_) > 1]
PWs = []
for w_ in PW:
    for sg in offroad([dense(w_, .5)], pad=.8):
        if len(sg) > 2 and math.hypot(*sg.mean(0)) < R - 3 and min(np.hypot(*(sg.mean(0) - q[:2])) - q[2] for q in hpos) > .3: PWs.append(sg)
from skimage.measure import approximate_polygon as _ap
def approx_line(sg): return _ap(np.asarray(sg), .25)
pa = Acc(); pb = Acc()
for sg in PWs:
    sg2 = approx_line(sg); pa.add(sweep(sg2, .5, .75, .0, .25, step=1.8)); pb.add(sweep(sg2, .5, 1.8, .0, .25, step=1.8))
o_ = pa.obj('A-QW', stone_m); o_['sid'] = 'QW'; o_['mode'] = 'A'; o_['ev'] = 'conf'
o_ = pb.obj('B-QW', stone_m); o_['sid'] = 'QW'; o_['mode'] = 'B'; o_['ev'] = 'hip'
item(id='QW', name='Muros dos quarteirões', kind='Muro', phase='—', ev='conf', evB='hip', dims=f'{len(PWs)} troços, ≈ {sum(np.sum(np.hypot(*np.diff(w_, axis=0).T)) for w_ in PWs):.0f} m',
     note='Muros das unidades familiares, quarteirões e ruas, vetorizados do levantamento geral da Citânia (Unidade de Arqueologia da Universidade do Minho). A vetorização automática da planta pode ter falhas e troços fragmentados. Altura atual representada ≈ 0,75 m; altura de reconstituição hipotética.', src=['plan'])
from scipy.spatial import cKDTree as _K2
_pwk = _K2(np.vstack(PWs)) if PWs else None
nw = 0; WL = json.load(open('lidar/walls.json'))
for wl in WL:
    pts = mloc(np.array(wl['p'], float))
    m_ = pts.mean(0)
    if math.hypot(*m_) > R - 4 or not _r2.contains_point(m_) or min(math.hypot(*(m_ - e)) for e in excl) < 9: continue
    if _pwk is not None and np.median(_pwk.query(dense(pts, .5))[0]) < 2.5: continue
    if any(abs(np.hypot(*(pts - [q[0], q[1]]).T).mean() - q[2]) < .6 for q in hpos if math.hypot(m_[0] - q[0], m_[1] - q[1]) < q[2] + 2): continue
    nw += 1; sid = f'W{nw:03d}'; h = float(wl['h'])
    put(sid, 'Muro', stone_m, [sweep(pts, .55, h, .0, .25, step=1.2)], 'A', 'conf'); put(sid, 'Muro', stone_m, [sweep(pts, .55, max(h, 1.8), .0, .25, step=1.2)], 'B', 'hip')
    item(id=sid, name='Muro', kind='Muro', phase='—', ev='conf', evB='hip', dims=f'comprimento ≈ {wl["len"]:.0f} m · altura medida ≈ {h:.1f} m · largura ≈ 0,55 m',
         note='Muro medido no LiDAR da DGT (2025, 50 cm): diferença entre o modelo de superfície e o modelo do terreno, numa zona sem árvores. Altura de reconstituição hipotética.', src=['lidar'])
print('houses', len(P.ORTHO_HOUSES), 'lidar walls', nw)
# road (modern), from OpenStreetMap: asphalt ribbon in the current state
def road_tex(path, centre):
    TW, TH_ = 512, 256                       # x: 12 m along the road, y: across (top = v 1)
    g_ = np.random.default_rng(9); base = 62 + g_.normal(0, 7, (TH_, TW)) + gaussian_filter(g_.normal(0, 12, (TH_, TW)), 3)
    img = np.stack([base, base, base * 1.03], -1)
    v = (1 - (np.arange(TH_) + .5) / TH_)[:, None] * np.ones((1, TW)); u = (np.arange(TW)[None, :] + .5) / TW * 12 * np.ones((TH_, 1))
    sh = (v < .06) | (v > .94); img[sh] = np.array([132, 120, 98]) + g_.normal(0, 10, (sh.sum(), 1))       # gravel shoulder
    wh = np.array([236, 234, 226]); vw = 1 / 6.6                                                       # road ≈ 5.9 m wide between v .06 and .94
    def band(v0, v1, m=None):
        k = (v > v0) & (v < v1) & (np.ones_like(v, bool) if m is None else m); img[k] = wh * (.92 + .08 * g_.random((k.sum(), 1)))
    band(.075, .075 + .12 * vw); band(.925 - .12 * vw, .925)                                            # 12 cm edge lines
    if centre: band(.5 - .06 * vw, .5 + .06 * vw, (u % 12) < 4)                                        # 4 m dash, 8 m gap
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path, quality=88)
road_tex('blend/road_main.jpg', True); road_tex('blend/road_access.jpg', False)
road_m, _ = img_mat('asphalt', 'blend/road_main.jpg', .75); road2_m, _ = img_mat('asphalt_access', 'blend/road_access.jpg', .75)
o = json.load(open('osm/mask_sites.json'))[SID]
RG = []; RG2 = []
for rl in o['rl']:
    w_ = rl[0]; pts = mloc(np.array(rl[1:], float).reshape(-1, 2))
    acc_ = w_ < 5 and np.hypot(*(pts - oloc([P.RECEPTION[0][0], P.RECEPTION[0][1]])).T).min() < 15
    if w_ < 5 and not (w_ >= 4 and acc_): continue
    for sg in clip(pts, R - 1.5):
        (RG2 if w_ < 8 else RG).append(road_strip(sg, w=max(w_, 5) * .9 if w_ < 8 else 6.6))
if RG or RG2:
    if RG: put('RD', 'Estrada', road_m, RG, 'A', 'conf')
    if RG2: put('RD', 'Acesso ao centro de receção', road2_m, RG2, 'A', 'conf')
    item(id='RD', name='Estrada (atual)', kind='Infraestrutura moderna', phase='séc. XX', ev='conf', evB='conf', dims='—', note='Estrada de acesso (EN 309), aberta em 1930; foi na sua construção que apareceu a Pedra Formosa (Cardoso 1935). Traçado do OpenStreetMap.', src=['osm', 'cardoso1935'])
from matplotlib.path import Path as _MP
from pyproj import Transformer as _Tr
_tf = _Tr.from_crs(4326, 3763, always_xy=True)
PARKS = [[(41.5279081, -8.314109)]]
import osmium as _os
class _PH(_os.SimpleHandler):
    def __init__(s_): super().__init__(); s_.o = []
    def way(s_, w):
        if dict(w.tags).get('amenity') == 'parking':
            try: L_ = [(n.location.lat, n.location.lon) for n in w.nodes]
            except Exception: return
            if 41.52 < L_[0][0] < 41.534 and -8.322 < L_[0][1] < -8.308: s_.o.append(L_)
_ph = _PH(); _ph.apply_file('osm/braga.pbf', locations=True)
park_m, _ = img_mat('parking', 'blend/road_access.jpg', .8); npk = 0
for L_ in _ph.o:
    xy = np.array([_tf.transform(lo, la) for la, lo in L_]); lx = xy[:, 0] - X0L; lz = Y0L - xy[:, 1]; poly = mloc(np.c_[lx, lz])
    if np.min(np.hypot(*poly.T)) > R - 3: continue
    mp_ = _MP(poly); x0, y0 = poly.min(0); x1, y1 = poly.max(0); V = []; F = []; UV = []; idx = {}
    xs_ = np.arange(x0, x1 + 1, 1.0); ys_ = np.arange(y0, y1 + 1, 1.0)
    for j, y_ in enumerate(ys_):
        for i, x_ in enumerate(xs_):
            idx[(i, j)] = len(V); V.append((x_, y_, 0)); UV.append((x_ / 12, .5))
    zz_ = []
    for (i, j), k in idx.items():
        x_, y_, _z = V[k]
        if math.hypot(x_, y_) < R - 2: zz_.append(float(hz(x_, y_)))
    for j in range(len(ys_) - 1):
        for i in range(len(xs_) - 1):
            c_ = (xs_[i] + .5, ys_[j] + .5)
            if mp_.contains_point(c_) and math.hypot(*c_) < R - 2: F.append((idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))
    if not F: continue
    used = sorted({k for f in F for k in f}); V = [(V[k][0], V[k][1], float(hz(V[k][0], V[k][1])) + .2) if k in used else V[k] for k in range(len(V))]
    npk += 1; put('PK', 'Parque de estacionamento', park_m, [(V, F, UV)], 'A', 'conf')
if npk: item(id='PK', name='Parque de estacionamento', kind='Infraestrutura moderna', phase='atual', ev='conf', evB='conf', dims='—', note='Parque de estacionamento de apoio aos visitantes, segundo o OpenStreetMap. Aparece só no estado atual.', src=['osm'])
print('parks', npk)
# no outcrops are mapped for Briteiros: decorative boulders only outside the first wall
rock_m = col_mat('granite', (122, 116, 104), .95)
from matplotlib.path import Path as MPath
_encl0 = MPath(loc(P.R1)); _encl2 = MPath(loc(P.R2))
bm2 = bmesh.new(); nb = 0
for _ in range(5000):
    x, y = (rng.random(2) * 2 - 1) * R
    if nb >= 35 or math.hypot(x, y) > R - 4 or _encl2.contains_point((x, y)): continue
    for kk2 in range(int(rng.integers(1, 4))):
        tmp = bmesh.new(); bmesh.ops.create_icosphere(tmp, subdivisions=2, radius=1)
        sc = np.array([.6 + rng.random() * 1.6, .5 + rng.random() * 1.3, .45 + rng.random() * .9]); ox, oy = (rng.random(2) - .5) * 3; ang = rng.random() * np.pi
        for vv in tmp.verts:
            q = np.array(vv.co) * sc * (1 + rng.normal(0, .08)); ca, sa = math.cos(ang), math.sin(ang)
            vv.co = (x + ox + q[0] * ca - q[1] * sa, y + oy + q[0] * sa + q[1] * ca, 0); vv.co.z = float(hz(vv.co.x, vv.co.y)) + q[2] - .25
        m_ = bpy.data.meshes.new('t'); tmp.to_mesh(m_); tmp.free(); bm2.from_mesh(m_); bpy.data.meshes.remove(m_)
    nb += 1
me2 = bpy.data.meshes.new('boulders'); bm2.to_mesh(me2); bm2.free(); new_obj('boulders', me2, col_mat('granite2', (132, 128, 118), .95))
# ---------- trees from the LiDAR canopy height model: local maxima above 4 m, real heights
from scipy.ndimage import maximum_filter as _mf
rS, cS = _rc(np.array([-R, R]), np.array([R, -R])); r0_, r1_ = int(rS.min()), int(rS.max()); c0_, c1_ = int(cS.min()), int(cS.max())
CH = gaussian_filter(MDS[r0_:r1_, c0_:c1_] - MDT[r0_:r1_, c0_:c1_], 1.2)
pk = (CH == _mf(CH, 7)) & (CH > 3)
ys, xs = np.nonzero(pk)
tp = []; TH = {}
for yy_, xx_ in zip(ys, xs):
    lx = (c0_ + xx_ + .5) * .5 - 16000 - X0L; lz = Y0L - (207000 - (r0_ + yy_ + .5) * .5)
    x, y = lx - CX, -(lz - CZ)
    if math.hypot(x, y) < R - 2.5: tp.append((x, y)); TH[(x, y)] = float(CH[yy_, xx_])
a = np.asarray(crop.resize((512, 512))).astype(float); r_, g_, b_ = a[..., 0], a[..., 1], a[..., 2]
can = gaussian_filter(((a.mean(-1) < 92) & (g_ >= r_ - 4) & (b_ < g_ + 10)).astype(float), 1.2)
wallpts = np.vstack([dense(loc(L)) for L in [P.R1, P.R2]] + [np.array([[h[0], h[1]] for h in hpos])] + ([np.vstack([r['V'] for r in []])] if False else []))
from scipy.spatial import cKDTree
kd = cKDTree(wallpts)
from matplotlib.path import Path as MPath
_encl = MPath(loc(P.R1))
roadpts = np.vstack([np.array(g[0])[:, :2] for g in RG]) if RG else np.zeros((1, 2)) + 1e6; kr = cKDTree(roadpts)
_r2t = MPath(loc(P.R2))
tp = [p for p in tp if kr.query(p)[0] > 4 and math.hypot(p[0] - bcen[0], p[1] - bcen[1]) > 15 and (not _r2t.contains_point(p) or (kd.query(p)[0] > 4 and rng.random() < (.2 if _encl.contains_point(p) else .5)))]   # real LiDAR trees, thinned inside the walls so the ruins stay readable
if len(tp) > 2600: tp = [tp[i] for i in sorted(rng.choice(len(tp), 2600, replace=False))]
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
PROTO = {
 'oak': [('trunk', OAK_L), ('leaf', OAK_C)],
 'cork': [('bark', COR_T), ('trunk', COR_L), ('leaf', COR_C)],
 'pine': [('trunk', cone(0, 0, -.03, .02, .6, 6)), ('leaf', blobs([(0, 0, .74, .26, .3), (.17, .06, .64, .19, .22), (-.16, -.07, .62, .19, .22), (.03, -.18, .58, .17, .2), (-.04, .16, .56, .16, .2), (0, 0, .9, .16, .16)]))],
 'shrub': [('leaf', blobs([(0, 0, .3, .42, .55), (.28, .1, .25, .3, .42), (-.25, -.12, .24, .28, .4)]))],
 'tuft': [('leaf', blades(7))],
}
PAL = {'oak': [(96, 128, 54), (112, 140, 60), (84, 116, 48)], 'cork': [(70, 88, 52), (80, 96, 56), (62, 80, 48)], 'pine': [(70, 100, 56), (80, 110, 60), (62, 92, 52)],
       'shrub': [(128, 138, 62), (112, 128, 56), (196, 170, 60)], 'tuft': [(120, 132, 62), (138, 144, 70), (104, 120, 56)]}
bark_m = col_mat('corkbark', (160, 78, 44), .9); trunk = col_mat('trunk', (88, 74, 60), .9)
for nm, parts in PROTO.items():
    for part, geo in parts:
        A = Acc(); A.add(geo); o = A.obj(f'PROTO-{nm}-{part}-{len(bpy.data.objects)}', {'trunk': trunk, 'bark': bark_m}.get(part, leaf[1])); o.location = (0, 0, 0)
TYPES = list(PROTO)
TREES = []
for (x, y) in tp:
    g = float(hz(x, y)); h_ = TH[(x, y)]; rr = rng.random(); kind = 'pine' if (h_ > 15 and rr < .35) else ('cork' if (h_ < 13 and rr < .45) else 'oak')
    TREES.append([round(x, 2), round(y, 2), round(g, 2), round(min(22, h_ * EX), 1), TYPES.index(kind), int(rng.integers(0, 3)), round(rng.random() * 6.28, 2)])
# undergrowth: gorse/broom at the forest edges and on the slopes, grass tufts everywhere but the path and the structures
canm = lambda x, y: can[min(511, max(0, int((R - y) / (2 * R) * 512))), min(511, max(0, int((x + R) / (2 * R) * 512)))]
pathpts = np.vstack([dense(loc(L), 1.5) for L in P.WAYS] + [roadpts]); kp = cKDTree(pathpts)
def free(x, y, dw, dp=2.5): return math.hypot(x, y) < R - 2 and kd.query((x, y))[0] > dw and kp.query((x, y))[0] > dp
n_sh = 0
for _ in range(9000):
    x, y = (rng.random(2) * 2 - 1) * R; c = canm(x, y)
    if n_sh > 650 or not free(x, y, 6) or _encl.contains_point((x, y)): continue
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

# ---------- labels
for t, x, y in P.LABELS:
    c = loc([x, y])
    if math.hypot(*c) > R - 4: continue
    e = bpy.data.objects.new(f'LBL-{t}-{len(bpy.data.objects)}', None); e.location = (c[0], c[1], float(hz(c[0], c[1])) + 3); bpy.context.scene.collection.objects.link(e)
for t, c, dz in [('Capela de São Romão', ch, 9), ('Casas reconstruídas', oloc([728, 696]), 6), ('Centro de receção', bc, 7), ('Balneário Sul', bcen, 5)]:
    e = bpy.data.objects.new(f'LBL-{t}-{len(bpy.data.objects)}', None); e.location = (c[0], c[1], float(hz(c[0], c[1])) + dz); bpy.context.scene.collection.objects.link(e)

# ---------- stylised ground (the orthophoto only guides land cover): grass, dry grass in the enclosure, trodden earth, path
TS = 2560; mpp = 2 * R / TS
jj, ii = np.mgrid[0:TS, 0:TS]; GX = (ii + .5) * mpp - R; GY = R - (jj + .5) * mpp
def noise(sig, seed):
    return gaussian_filter(np.random.default_rng(seed).normal(0, 1, (TS, TS)), sig, mode='wrap')
n1 = noise(40, 1); n1 /= n1.std(); n2 = noise(10, 2); n2 /= n2.std(); n3 = noise(2, 3); n3 /= n3.std()
from PIL import ImageDraw
def m2px(p): return [((x + R) / mpp, (R - y) / mpp) for x, y in p]
def mask_draw(fn):
    im = Image.new('L', (TS, TS), 0); fn(ImageDraw.Draw(im)); return np.asarray(im, float) / 255
encl = loc(P.R1)
inside = gaussian_filter(mask_draw(lambda d: d.polygon(m2px(encl), fill=255)), 6)
def near(d):
    for L in [P.R1 + [P.R1[0]], P.R2 + [P.R2[0]]]: d.line(m2px(loc(L)), fill=255, width=int(6 / mpp))
    for (x, y, rad) in hpos:
        X, Y = (x + R) / mpp, (R - y) / mpp; q = (rad + 1.6) / mpp; d.ellipse([X - q, Y - q, X + q, Y + q], fill=255)
dirt = gaussian_filter(mask_draw(near), 5)
def _paths(d):
    for L in P.WAYS: d.line(m2px(dense(loc(L), 2)), fill=255, width=int(3.4 / mpp), joint='curve')
path = gaussian_filter(mask_draw(_paths), 2.2)
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
zz2 = hz(GX[::2, ::2], GY[::2, ::2]); gy2, gx2 = np.gradient(zz2, mpp * 2)
nx, ny, nz = -gx2, gy2, np.ones_like(gx2); nn = np.sqrt(nx * nx + ny * ny + 1); L_ = np.array([-.55, .45, .7]); L_ /= np.linalg.norm(L_)
shade = (nx * L_[0] + ny * L_[1] + nz * L_[2]) / nn; shade = np.asarray(Image.fromarray(shade.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
col *= np.clip(.8 + .3 * (shade - shade.mean()) / (shade.std() + 1e-6) * .5 + .2, .62, 1.2)[..., None]
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

_SEC = np.load('blend/p15_sectors.npy')
import cv2 as _cv
_M15, _ = _cv.estimateAffinePartial2D(np.array([(428, 463), (408, 488), (349, 469)], float), np.array([(-70.25, -88.5), (-77.75, -75.5), (-103.0, -81.0)], float))
_Mi = _cv.invertAffineTransform(_M15)
_inner = {5, 6, 7, 8, 11, 12}
for c in CAT:
    obs = [o for o in bpy.data.objects if o.type == 'MESH' and o.get('sid') == c['id']]
    if not obs: continue
    vs = np.array([v.co[:] for o in obs for v in o.data.vertices])[:, :2].mean(0)
    lx, lz = vs[0] + CX, CZ - vs[1]; px_, py_ = _Mi @ [lx, lz, 1]
    if 0 <= int(py_) < _SEC.shape[0] and 0 <= int(px_) < _SEC.shape[1] and c['kind'] not in ('Muralha',) and c['id'] not in ('QW', 'RD', 'PK', 'W'):
        k = int(_SEC[int(py_), int(px_)]); c['sector'] = f'S{k}' + ('' if k in _inner else ' (aprox.)')
        c['phase'] = (c['phase'] + ' · ' if c.get('phase') and c['phase'] != '—' else '') + 'setor ' + c['sector']
# ---------- export
os.makedirs('app/dio', exist_ok=True)
for o in sc.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.abspath(f'app/dio/{SID}.glb'), export_format='GLB', export_apply=True, export_yup=True,
                          export_image_format='JPEG', export_jpeg_quality=80, export_materials='EXPORT', use_selection=False, export_extras=True,
                          export_draco_mesh_compression_enable=False)
json.dump({'cat': CAT, 'sources': P.SOURCES, 'R': R, 'ex': EX, 'h0': H0, 'cx': CX, 'cz': CZ, 'trees': TREES, 'types': TYPES, 'pal': {k: [list(c) for c in v] for k, v in PAL.items()}}, open(f'app/dio/{SID}.json', 'w'))
print('ok', os.path.getsize(f'app/dio/{SID}.glb'))
