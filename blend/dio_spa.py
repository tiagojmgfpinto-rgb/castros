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
def hz(x, y): return (np.maximum(hraw(x, y), SEA - 1.2) - H0) * EX
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
NR, NA = 330, 900
rr = np.linspace(0, R, NR + 1)[1:]; aa = np.linspace(0, 2 * np.pi, NA, endpoint=False)
X = np.concatenate([[0], (rr[:, None] * np.cos(aa)[None]).ravel()]); Y = np.concatenate([[0], (rr[:, None] * np.sin(aa)[None]).ravel()])
Z = hz(X, Y); V = np.stack([X, Y, Z], 1); F = []
for a in range(NA): F.append((0, 1 + a, 1 + (a + 1) % NA))
for r in range(NR - 1):
    o0, o1 = 1 + r * NA, 1 + (r + 1) * NA
    for a in range(NA): b = (a + 1) % NA; F.append((o0 + a, o1 + a, o1 + b, o0 + b))
gmat, gtex = img_mat('ground', 'blend/spa/ground_raw.jpg')
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
Image.fromarray(np.clip(st[::-1] + rng.normal(0, 6, st.shape), 0, 255).astype(np.uint8)).resize((64, 256)).save('blend/spa/strata.jpg', quality=90)
smat, _ = img_mat('earth', 'blend/spa/strata.jpg')
skirt = new_obj('skirt', mesh_from('skirt', SV, SF, SUV), smat)# ---------- sea: a flat water surface at the level of the LiDAR returns over the water, clipped to the disc
water_m = bpy.data.materials.new('water'); water_m.use_nodes = True
_wb = water_m.node_tree.nodes['Principled BSDF']; _wb.inputs['Base Color'].default_value = (.12, .32, .40, 1); _wb.inputs['Roughness'].default_value = .25
_wb.inputs['Alpha'].default_value = .82; water_m.blend_method = 'BLEND' if hasattr(water_m, 'blend_method') else None
NWA = 360; wa = np.linspace(0, 2 * np.pi, NWA, endpoint=False); wz = (SEA - H0) * EX
WV = [(0, 0, wz)] + [(math.cos(a) * (R - .02), math.sin(a) * (R - .02), wz) for a in wa]
WF = [(0, 1 + k, 1 + (k + 1) % NWA) for k in range(NWA)]
WVs = [(math.cos(a) * (R - .03), math.sin(a) * (R - .03), z) for z in (wz, wz - 1.6) for a in wa]   # side band: inside the earth skirt on land, visible over the sea
WFs = [(k, (k + 1) % NWA, NWA + (k + 1) % NWA, NWA + k) for k in range(NWA)]
sea_o = new_obj('sea', mesh_from('sea', WV + WVs, WF + [tuple(i + len(WV) for i in f) for f in WFs]), water_m)
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
Image.fromarray(np.clip(_st * [.74, .72, .64] + [6, 6, 2], 0, 255).astype(np.uint8)).save('blend/spa/rubble.jpg', quality=88)
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
put('T1', 'Talude e muralha nascente', rub_m, [rampart(T1, 2.6, .05, .08, taper=.5)], 'A', 'conf')
put('T1', 'Talude e muralha nascente', stone_m, [rampart(T1, 2.5, 1.6, .1, taper=.92)], 'B', 'hip')
item(id='T1', name='Talude coroado por muralha, a nascente', kind='Muralha', phase='Idade do Ferro', ev='conf', evB='hip',
     dims=f'comprimento ≈ {LN["T1"]["len"]:.0f} m · talude com ≈ {T1_DROP:.1f} m de desnível (LiDAR) · crista ≈ {max(T1_RISE, 0):.1f} m acima do interior · reconstituição: muro com 2,5 m de largura e 1,6 m acima da crista (hipotético)',
     note=f'«Talude coroado por uma muralha de pedra, da qual apenas resta o seu alicerce», bem demarcado sobretudo na vertente Este (Almeida et al. 2012). No LiDAR de 2025 é o rebordo nascente do povoado: uma crista ligeiramente elevada sobre o interior e um talude de cerca de {T1_DROP:.1f} m para os campos. Traçado no modelo do terreno e ajustado à crista. Largura e altura da muralha não publicadas: valores da reconstituição hipotéticos.',
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
for sid, poly, nm, note, src in [
    ('E1', E1, 'Ruínas de Habitação (área escavada protegida)',
     'Área escavada coberta por gravilha, com bordo de pedra e troncos e painel interpretativo. Segundo o painel, a construção circular era o compartimento de uma habitação associada a um pátio e a um lajeado, com lareira central e piso de argila decorado com círculos; pertence ao nível mais recente do povoado (séculos II–I a.C.). Contorno medido na ortofotografia; as paredes estão tapadas e não se veem.',
     ['pan', 'hmdb', 'alm', 'orto']),
    ('E2', E2, 'Conjunto habitacional à volta de um pátio (área escavada protegida)',
     'Área escavada coberta por gravilha, rodeada por um muro de pedra, junto ao passadiço. O painel descreve um conjunto de três ou quatro compartimentos à volta de um pequeno pátio, talvez fechado por um muro de pedra ou de madeira, do nível mais recente; no interior apareceram uma fíbula, uma mó manual redonda e uma lareira central decorada. Contorno medido na ortofotografia; as paredes estão tapadas e não se veem.',
     ['pan', 'alm', 'orto'])]:
    put(sid, nm, gravel_m, [pad(poly)], 'A', 'conf')
    put(sid + 'W', 'Bordo da área escavada', stone_m, [poly_walls(poly, .4, .35)], 'A', 'conf')
    sd = sorted(sides(poly))
    item(id=sid, name=nm, kind='Área escavada', phase='atual', ev='conf', evB='conf', dims=f'≈ {np.mean(sd[2:]):.1f} × {np.mean(sd[:2]):.1f} m ({area(poly):.0f} m², medido na ortofotografia)', note=note, src=src)
    item(id=sid + 'W', name='Bordo da área escavada', kind='Muro moderno', phase='atual', ev='conf', evB='conf', dims='≈ 0,35 m de altura (aproximado)', note='Bordo de proteção da área escavada (pedra e troncos), posto na valorização do sítio.', src=['pan', 'orto'])
# reconstitution of the houses under the two areas: round stone houses with conical thatch (hypothetical diameters and positions)
th_m, _ = img_mat('thatch', 'blend/thatch.jpg', 1)
HD = 2 * (C1_RO - C1_W)          # 4.2 m: inner diameter of the round structure C1, the only one measurable on the site today
def house(sid, c, rad, label_):
    put(sid, label_, stone_m, [sweep(cyl(c, rad + .25), .5, 2.1, .02, .3, closed=True, top_taper=1)], 'B', 'hip')
    gz = float(hz(c[0], c[1])) + 2.1; rr2 = rad + .85; hr = rad * 1.15
    rv = [(c[0], c[1], gz + hr)] + [(c[0] + math.cos(k / 24 * 2 * np.pi) * rr2, c[1] + math.sin(k / 24 * 2 * np.pi) * rr2, gz - .3) for k in range(24)]
    ro = put(sid + 'R', 'Cobertura', th_m, [(rv, [(0, 1 + k, 1 + (k + 1) % 24) for k in range(24)], [(.5, .5)] + [(k / 24 * 3, 1.5) for k in range(24)])], 'B', 'hip')
    if ro:
        for p in ro.data.polygons: p.use_smooth = True
HN = 'O diâmetro das casas de São Paio não está publicado: a reconstituição usa {d:.1f} m de diâmetro interior, o da estrutura circular C1 medida na ortofotografia, e paredes de 2,1 m. A cobertura cónica de colmo segue o livro do Centro Interpretativo («telhados de forma cónica», de colmo, sem telha) e o desenho do painel, ambos reconstituições. Posição dentro da área escavada e portas: hipotéticas.'.format(d=HD)
e1c = E1.mean(0); house('H1', e1c, HD / 2, 'Casa circular (reconstituição)')
item(id='H1', name='Casa circular das «Ruínas de Habitação»', kind='Habitação', phase='Idade do Ferro, fase recente', ev='doc', evB='hip', roof='hip',
     dims=f'diâmetro interior {HD:.1f} m (hipotético)', note='Construção circular em pedra do nível mais recente (meados do séc. II a.C. a meados do séc. I a.C.), com lareira central e piso decorado com círculos estampilhados (painel; Almeida et al. 2012). ' + HN, src=['pan', 'alm', 'hmdb'])
_ax = E2[1] - E2[0]; _ax /= np.linalg.norm(_ax); e2c = E2.mean(0); _off = (HD / 2 + .5)
house('H2', e2c - _ax * _off, HD / 2, 'Compartimento circular (reconstituição)'); house('H3', e2c + _ax * _off, HD / 2, 'Compartimento circular (reconstituição)')
for sid in ('H2', 'H3'):
    item(id=sid, name='Compartimento circular do conjunto habitacional', kind='Habitação', phase='Idade do Ferro, fase recente', ev='doc', evB='hip', roof='hip',
         dims=f'diâmetro interior {HD:.1f} m (hipotético)', note='O painel mostra dois compartimentos circulares lado a lado, ligados a um pátio; o conjunto teria três ou quatro construções. ' + HN, src=['pan', 'alm'])
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
# ---------- buildings: footprints from the LiDAR (MDS − MDT > 2.2 m, flat or gabled roofs), roofs at the measured MDS height
# (smoothed surface on a 0.5 m grid), walls down to the lowest ground. Only in the current state, except the chapel (kept in both).
nd = _dsm - _dtm
gy_, gx_ = np.gradient(_dsm, LB['cs']); gyy, _ = np.gradient(gy_, LB['cs']); _, gxx = np.gradient(gx_, LB['cs'])
cand = (nd > 2.2) & (uniform_filter(np.abs(gxx) + np.abs(gyy), 5) < 2.5)
cand = binary_closing(binary_opening(cand, iterations=2), iterations=2)
labB, nB_ = label(cand)
_ci = np.arange(LB['n']); _GXl = LB['x0'] + (_ci + .5) * LB['cs'] - X0L; _GYl = LB['y1'] - (_ci + .5) * LB['cs'] - Y0L
BLDS = {  # component centroid (local box metres) -> id, name, roof colour, wall colour, kept in the reconstitution
 (13.9, -25.8): ('CH', 'Capela de São Paio', 'tile', 'granite', True),
 (-22.2, 47.1): ('B1', 'Edifício a norte do castro', 'grey', 'lime', False),
 (32.5, 66.0): ('B2', 'Anexo agrícola', 'grey', 'lime', False),
}
lime_m = col_mat('lime', (238, 234, 224), .85); tile_m = col_mat('tile', (176, 86, 52), .8); grey_m = col_mat('roofgrey', (150, 150, 146), .85)
gran_m = col_mat('granite_grey', (146, 145, 139), .9)   # the chapel is grey granite (photographs, 2025)
BLDM = np.zeros_like(cand); BLD_PTS = []; BINFO = {}; CHFIT = {}
for i in range(1, nB_ + 1):
    rr_, cc_ = np.nonzero(labB == i)
    if len(rr_) * LB['cs'] ** 2 < 12: continue
    cx_, cy_ = _GXl[cc_].mean(), _GYl[rr_].mean()
    key = next((k for k in BLDS if math.hypot(k[0] - cx_, k[1] - cy_) < 3), None)
    if key is None: continue
    bid, nm, rc_, wc_, keep = BLDS[key]
    m = labB == i; BLDM |= m
    # 0.5 m roof grid: vertices at cell corners, height = median MDS of the cell (3x3 median), walls along the outline
    r0, r1, c0, c1 = rr_.min() - 2, rr_.max() + 3, cc_.min() - 2, cc_.max() + 3
    sub = m[r0:r1, c0:c1]; ds = median_filter(_dsm[r0:r1, c0:c1], 3)
    h2 = (sub.shape[0] // 2) * 2, (sub.shape[1] // 2) * 2
    M2 = sub[:h2[0], :h2[1]].reshape(h2[0] // 2, 2, h2[1] // 2, 2).mean((1, 3)) > .5
    D2 = ds[:h2[0], :h2[1]].reshape(h2[0] // 2, 2, h2[1] // 2, 2).mean((1, 3))
    base = float(_dtm[r0:r1, c0:c1][sub].min()) - .3
    ny_, nx_ = M2.shape
    cx0 = _GXl[c0] - LB['cs'] / 2; cy0 = _GYl[r0] + LB['cs'] / 2        # top-left corner of the sub grid (local)
    cxw = lambda j: cx0 + j * .5 - CX; cyw = lambda i_: cy0 - i_ * .5 - CY
    # corner heights: mean of the roof cells touching the corner
    CZ = np.full((ny_ + 1, nx_ + 1), np.nan)
    for a in range(ny_ + 1):
        for b in range(nx_ + 1):
            v = [D2[a2, b2] for a2 in (a - 1, a) for b2 in (b - 1, b) if 0 <= a2 < ny_ and 0 <= b2 < nx_ and M2[a2, b2]]
            if v: CZ[a, b] = np.mean(v)
    V = []; F = []; vid = {}
    def vtx(a, b, z):
        k = (a, b, round(z, 3))
        if k not in vid: vid[k] = len(V); V.append((cxw(b), cyw(a), (z - H0) * EX))
        return vid[k]
    for a in range(ny_):
        for b in range(nx_):
            if not M2[a, b]: continue
            F.append((vtx(a + 1, b, CZ[a + 1, b]), vtx(a + 1, b + 1, CZ[a + 1, b + 1]), vtx(a, b + 1, CZ[a, b + 1]), vtx(a, b, CZ[a, b])))
    WV = []; WF = []
    for a in range(ny_):
        for b in range(nx_):
            if not M2[a, b]: continue
            for (dn, e0, e1) in (((-1, 0), (a, b), (a, b + 1)), ((1, 0), (a + 1, b + 1), (a + 1, b)), ((0, -1), (a + 1, b), (a, b)), ((0, 1), (a, b + 1), (a + 1, b + 1))):
                na, nb = a + dn[0], b + dn[1]
                if 0 <= na < ny_ and 0 <= nb < nx_ and M2[na, nb]: continue
                z0, z1 = CZ[e0], CZ[e1]; o = len(WV)
                WV += [(cxw(e0[1]), cyw(e0[0]), (base - H0) * EX), (cxw(e1[1]), cyw(e1[0]), (base - H0) * EX), (cxw(e1[1]), cyw(e1[0]), (z1 - H0) * EX), (cxw(e0[1]), cyw(e0[0]), (z0 - H0) * EX)]
                WF.append((o, o + 1, o + 2, o + 3))
    roof_mat = {'tile': tile_m, 'grey': grey_m}[rc_]; wall_mat = {'granite': gran_m, 'lime': lime_m}[wc_]
    mode = 'AB' if keep else 'A'
    if bid == 'CH':   # gabled nave fitted to the LiDAR: minimum rectangle of the roof cells, ridge along the long axis
        import cv2
        P_ = np.c_[_GXl[cc_], _GYl[rr_]].astype(np.float32); (rcx, rcy), (rw, rh_), ra = cv2.minAreaRect(P_)
        ax_ = np.array([math.cos(math.radians(ra)), math.sin(math.radians(ra))])
        if rh_ > rw: ax_ = np.array([-ax_[1], ax_[0]]); rw, rh_ = rh_, rw
        u_ = (P_ - [rcx, rcy]) @ ax_; v_ = (P_ - [rcx, rcy]) @ np.array([-ax_[1], ax_[0]]); zt_ = _dsm[rr_, cc_]
        eave = float(np.median(zt_[np.abs(np.abs(v_) - rh_ / 2) < .6])); ridge = float(np.percentile(zt_[np.abs(v_) < .8], 90))
        ang_ = math.atan2(ax_[1], ax_[0]); c_ = np.array([rcx - CX, rcy - CY]); g0 = (base - H0) * EX
        ze, zr = (eave - H0) * EX, (ridge - H0) * EX
        geo_w = [boxv(c_[0], c_[1], ang_, rw - .3, rh_ - .3, g0, ze)]
        put(bid + 'w', nm + ' (paredes)', wall_mat, geo_w + [gable_wall(c_[0], c_[1], ang_, rw - .3, rh_ - .3, ze, zr - ze)], mode, 'conf')
        put(bid, nm, roof_mat, [gable(c_[0], c_[1], ang_, rw - .3, rh_ - .3, ze, zr - ze, .25)], mode, 'conf')
        # stone cross on the apex of the west (main) facade, as in the 2025 photographs
        ends = [c_ + ax_ * rw / 2, c_ - ax_ * rw / 2]; we = min(ends, key=lambda e: e[0])
        put(bid + 'x', 'Cruz da fachada', gran_m, [boxv(we[0], we[1], ang_, .18, .18, zr, zr + 1.0), boxv(we[0], we[1], ang_, .18, .7, zr + .55, zr + .73)], mode, 'conf')
        CHFIT = dict(L=float(rw), W=float(rh_), eave=eave - float(_dtm[m].min()), ridge=ridge - float(_dtm[m].min()), az=(90 - math.degrees(ang_)) % 180)
    else:
        put(bid, nm, roof_mat, [(V, F, [(0, 0)] * len(V))], mode, 'conf')
        put(bid + 'w', nm + ' (paredes)', wall_mat, [(WV, WF, [((k % 4 in (1, 2)) * 1.0, (k % 4 > 1) * 1.0) for k in range(len(WV))])], mode, 'conf')
    top = float(np.percentile(_dsm[m], 97)); fl = float(_dtm[m].min())
    BINFO[bid] = dict(area=float(m.sum() * LB['cs'] ** 2), top=top, base=fl, c=(cx_, cy_))
    pts = np.c_[_GXl[cc_] - CX, _GYl[rr_] - CY]; BLD_PTS.append(pts[::7])
BLD_PTS = np.vstack(BLD_PTS) if BLD_PTS else np.zeros((0, 2))
print('buildings', {k: (round(v['area']), round(v['top'] - v['base'], 1)) for k, v in BINFO.items()})
ch = BINFO.get('CH', dict(area=0, top=0, base=0))
item(id='CH', name='Capela de São Paio', kind='Edifício moderno', phase='séc. XVII (?), remodelada em 1885 (?) e nos anos 70 do séc. XX', ev='conf', evB='conf',
     dims=(f'corpo ≈ {CHFIT["L"]:.1f} × {CHFIT["W"]:.1f} m · beirado ≈ {CHFIT["eave"]:.1f} m e cumeeira ≈ {CHFIT["ridge"]:.1f} m acima do solo · eixo a {CHFIT["az"]:.0f}° do norte (LiDAR)' if CHFIT else 'LiDAR'),
     note='No extremo sul do castro. Apesar do aspeto recente, incorpora elementos provavelmente do século XVII; no interior há a data de 1885, talvez de obras; nos anos 70 do século XX foi largamente remodelada e só restou a fachada principal. O altar-mor é um rochedo tirado da penedia (Almeida et al. 2012). Forma e alturas do LiDAR (MDS), com cobertura e paredes simplificadas.', src=['alm', 'lidar', 'tese'])
for bid, nm in (('B1', 'Edifício a norte do castro'), ('B2', 'Anexo agrícola')):
    if bid in BINFO:
        item(id=bid, name=nm, kind='Edifício moderno', phase='atual', ev='conf', evB='conf', dims=f'planta ≈ {BINFO[bid]["area"]:.0f} m² · altura ≈ {BINFO[bid]["top"] - BINFO[bid]["base"]:.1f} m (LiDAR)',
             note='Edifício atual, fora do castro; forma e altura do LiDAR (MDS).', src=['lidar', 'orto'])
item(id='CI', name='Centro Interpretativo do Castro de São Paio', kind='Edifício moderno', phase='2012', ev='conf', evB='conf', dims='cobertura ao nível do terreno do lado do castro (o LiDAR classifica-a como solo)',
     note='Aberto no fim de 2012, no mesmo edifício de um café-restaurante; mostra o espólio do castro e painéis de arqueologia, geologia e biologia. O edifício está encaixado na encosta: do lado do castro a cobertura fica à cota do terreno, por isso aparece no relevo e na textura do solo.', src=['alm', 'muni', 'tese'])
# ---------- orthophoto (aligned on the LiDAR, lidar/spa_orto.py) on the box grid: z20 where captured, z19 elsewhere
_o19 = np.asarray(Image.open('lidar/spa/orto_z19.png').convert('RGB'), float)
_o20 = np.asarray(Image.open('lidar/spa/orto_z20.png').convert('RGB'), float)
_v20 = (_o20.sum(2) > 30)[..., None]
ORT = np.where(_v20, _o20, _o19)
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
wallpts = np.vstack([dense(line('T1'))] + [dense(np.vstack([p, p[:1]]), .8) for p in STRUCT_POLYS] + [BLD_PTS])
from scipy.spatial import cKDTree
kd = cKDTree(wallpts)
from matplotlib.path import Path as MPath
_encl = MPath(ENC)
_upper = _encl
ntp0 = len(tp)
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
pathpts = np.argwhere(PAVED_G)[:, ::-1].astype(float); pathpts = np.stack([pathpts[:, 0] * .5 - R, R - pathpts[:, 1] * .5], 1) if len(pathpts) else np.zeros((1, 2)) + 1e6; kp = cKDTree(pathpts)
def free(x, y, dw, dp=2.5): return math.hypot(x, y) < R - 2 and kd.query((x, y))[0] > dw and kp.query((x, y))[0] > dp and float(hraw(x, y)) > 1.2 and not ROCKY(x, y)
n_sh = 0
# shrubs where the LiDAR sees low vegetation: local maxima of the canopy model between 0.7 and 2.8 m (gorse, broom, brambles)
_low = gaussian_filter(np.where((CHM > .7) & (CHM < 2.8), CHM, 0), 2)[r0_:r1_, c0_:c1_]
_lp = (_low == _mf(_low, 17)) & (_low > .5)
for yy_, xx_ in zip(*np.nonzero(_lp)):
    lx = LB['x0'] + (c0_ + xx_ + .5) * LB['cs'] - X0L; ly = LB['y1'] - (r0_ + yy_ + .5) * LB['cs'] - Y0L; x, y = lx - CX, ly - CY
    if n_sh > 260 or not free(x, y, 3) or (_encl.contains_point((x, y)) and rng.random() > .25): continue
    hs_ = float(CHM[r0_ + yy_, c0_ + xx_])
    TREES.append([round(x, 2), round(y, 2), round(float(hz(x, y)), 2), round(max(1.0, hs_), 2), TYPES.index('shrub'), int(rng.integers(0, 3)), round(rng.random() * 6.28, 2)]); n_sh += 1
n_tu = 0
for _ in range(20000):
    x, y = (rng.random(2) * 2 - 1) * R
    if n_tu > 700 or not free(x, y, 1.6, 1.8): continue
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

# ---------- ground texture from the orthophoto (real colours, read 1:1 on the LiDAR), cleaned and toned towards the castillos look:
# beach umbrellas and people smoothed away, a light hillshade from the 25 cm ground model, and ambient occlusion baked below.
TS = 3072; mpp = 2 * R / TS
jj, ii = np.mgrid[0:TS, 0:TS]; GX = (ii + .5) * mpp - R; GY = R - (jj + .5) * mpp
step = 3; col = orto_at(GX[::step, ::step], GY[::step, ::step])                  # 0.2 m samples of a 0.25 m image
col = np.stack([np.asarray(Image.fromarray(col[..., k].astype(np.float32)).resize((TS, TS), Image.BICUBIC)) for k in range(3)], -1)
hh = hraw(GX[::4, ::4], GY[::4, ::4]); hh = np.asarray(Image.fromarray(hh.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
mx = col.max(2); mn = col.min(2); sat = (mx - mn) / (mx + 1)
beach = gaussian_filter(((mx > 165) & (sat < .3) & (hh < 7.5) & (hh > SEA + .1)).astype(float), 6) > .5
smooth = np.stack([median_filter(col[::4, ::4, k], 9) for k in range(3)], -1)
smooth = np.stack([np.asarray(Image.fromarray(smooth[..., k].astype(np.float32)).resize((TS, TS), Image.BILINEAR)) for k in range(3)], -1)
outlier = np.abs(col - smooth).sum(2) > 70
col = np.where((beach & outlier)[..., None] | (beach[..., None] & (rng.random((TS, TS, 1)) < 0)), smooth, col)
col = np.where(beach[..., None], col * .4 + smooth * .6, col)
under = hh < SEA + .05
col = np.where(under[..., None], col * .55 + np.array([40, 70, 72]) * .45, col)                      # sea floor under the water
# tone: a little more saturation in the greens, lift the shadows, fine grain
g = col.mean(2, keepdims=True); col = g + (col - g) * 1.12
col = 255 * (np.clip(col, 0, 255) / 255) ** .92
zz2 = hz(GX[::4, ::4], GY[::4, ::4]); gy2, gx2 = np.gradient(zz2, mpp * 4)
nx, ny = -gx2, gy2; nn = np.sqrt(nx * nx + ny * ny + 1); L_ = np.array([-.55, .45, .7]); L_ /= np.linalg.norm(L_)
shade = (nx * L_[0] + ny * L_[1] + L_[2]) / nn; shade = np.asarray(Image.fromarray(shade.astype(np.float32)).resize((TS, TS), Image.BILINEAR))
col *= np.clip(1 + .25 * (shade - np.median(shade)), .78, 1.15)[..., None]
n3 = gaussian_filter(np.random.default_rng(3).normal(0, 1, (TS, TS)), 1.2); n3 /= n3.std()
col *= (1 + .035 * n3[..., None])
rim = np.clip((np.hypot(GX, GY) - (R - 1.0)) / 1.0, 0, 1)[..., None]; col = col * (1 - rim * .25)
Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save('blend/spa/ground_raw.jpg', quality=92)
gtex.image = bpy.data.images.load(os.path.abspath('blend/spa/ground_raw.jpg'))
# ---------- ambient occlusion baked into the ground texture (Cycles)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.device = 'CPU'
ao = bpy.data.images.new('ao', 1024, 1024, float_buffer=False)
an = gmat.node_tree.nodes.new('ShaderNodeTexImage'); an.image = ao; gmat.node_tree.nodes.active = an
for o in sc.objects: o.select_set(False)
for o in sc.objects:
    if o.name.startswith('B-') or o.name == 'sea': o.hide_render = True
terrain.select_set(True); bpy.context.view_layer.objects.active = terrain
sc.world = sc.world or bpy.data.worlds.new('w')
sc.render.bake.margin = 4
bpy.ops.object.bake(type='AO')
aopx = np.array(ao.pixels[:]).reshape(1024, 1024, 4)[::-1, :, 0]
aoi = Image.fromarray((np.clip(aopx, 0, 1) * 255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.5))
A = np.asarray(aoi, float)[..., None] / 255
G = np.asarray(Image.open('blend/spa/ground_raw.jpg'), float) * (.72 + .28 * A)
Image.fromarray(np.clip(G, 0, 255).astype(np.uint8)).save('blend/spa/ground.jpg', quality=88)
gmat.node_tree.nodes.remove(an); gtex.image = bpy.data.images.load(os.path.abspath('blend/spa/ground.jpg'))
for o in sc.objects: o.hide_render = False

# ---------- export
SOURCES = {
 "alm": "Almeida, P. B. de; Araújo, M. A.; Abrunhosa, M. J.; Teixeira, J.; Cruz, V. (2012). O Castro de S. Paio (Labruge, Vila do Conde). Vila do Conde: Câmara Municipal (livro do Centro Interpretativo; arqueologia por P. Brochado de Almeida, pp. 15-26). ISBN 978-972-9453-95-3. Cópia no Repositório Aberto da U. Porto: https://hdl.handle.net/10216/22268",
 "pa": "DGPC — Portal do Arqueólogo, sítio «São Paio» (CNS 3560): povoado fortificado da Idade do Ferro; escavações de C. A. Brochado de Almeida e P. J. L. Costa Pinto (1993-1996), sondagem (2004) e levantamento (2005). https://arqueologia.patrimoniocultural.pt/index.php?sid=sitios&subsid=49316",
 "pan": "Painéis interpretativos da Câmara Municipal de Vila do Conde no sítio («Ruínas de Habitação / Family House» e outros), fotografados por T. Pinto em 2025.",
 "hmdb": "The Historical Marker Database — «Ruínas de Habitação / Family House» (n.º 233697), «Os penedos amoladoiros» (233600), «Gravuras da área de S. Paio» (233448), com as coordenadas dos painéis (2023). https://www.hmdb.org/m.asp?m=233697",
 "muni": "Município de Vila do Conde (Visit Vila do Conde) — Castro de São Paio; Rota do Castro de São Paio. https://www.visitviladoconde.pt/fazer/patrimonio/patrimonio-arqueologico/geo_artigo/castro-de-sao-paio-43",
 "tese": "Pinto, T. — Castros do Noroeste de Portugal (tese de doutoramento, Univ. de Santiago de Compostela); visitas em 2022 e 2025: casas circulares, vestígios de fosso e muralha, capela na acrópole, passadiço com painéis, Centro Interpretativo de 2012.",
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
