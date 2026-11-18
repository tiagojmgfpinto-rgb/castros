# Citânia de Sanfins: the excavated stone walls, read straight from the DGT LiDAR 2025 point cloud (lidar/sfn_laz.py).
# The low dry-stone walls of the houses, the yard walls and the restored rampart are not classified as ground, so the
# 25 cm surface model minus the ground model (MDS − MDT) draws them as thin lines 0.15–2 m high in the cleared, excavated area.
#   1. wall mask: 0.12 m < MDS − MDT < 2.2 m, more than 0.75 m from any tree crown (> 2.5 m), inside the excavated areas (EXC);
#   2. round houses: Hough transform for rings of 1.5–3.6 m radius, kept when ≥ 70 % of the ring (and ≥ 40 % of each quadrant) lies on a wall centre line (±0.4 m) and the floor is nearly empty, then refined by least squares
#      on the wall cells within ±0.5 m of the ring (centre and diameter to ~0.1 m); a house must not overlap a better one;
#   3. straight walls: the remaining wall cells are skeletonised and split into polylines (Douglas–Peucker, 0.3 m), dropped under 2 m;
#   4. height of each wall now = median of MDS − MDT on the wall cells along it that hold a return above 0.1 m.
# Output: lidar/sfn_walls.json {houses: [[x, y, diameter, height, cover]], lines: [{pts, h, len}]} in local metres from the site point
# (PT-TM06 -21224.03, 183783.55): x east, y north. Usage: /opt/bvenv/bin/python lidar/sfn_walls.py
import json, numpy as np
from scipy.ndimage import binary_dilation, label, map_coordinates, binary_closing
from skimage.transform import hough_circle, hough_circle_peaks
from skimage.morphology import skeletonize, remove_small_objects, disk
from skimage.measure import approximate_polygon
from matplotlib.path import Path as MPath

B = json.load(open('lidar/sfn_box.json')); CS = B['cs']
X0L, Y0L = -21224.03, 183783.55
d = np.load('lidar/sfn_dtm25.npy'); d = np.where(np.isnan(d), np.nanmean(d), d)
ch = np.nan_to_num(np.load('lidar/sfn_dsm25.npy') - d)
N = ch.shape[0]
def to_rc(x, y): return (B['y1'] - (Y0L + np.asarray(y))) / CS - .5, (X0L + np.asarray(x) - B['x0']) / CS - .5
def to_xy(r, c): return B['x0'] + (np.asarray(c) + .5) * CS - X0L, B['y1'] - (np.asarray(r) + .5) * CS - Y0L
# excavated and cleared areas (traced on the LiDAR wall mask): the acropolis with its houses and the south sector
EXC = [
 [(-100, 128), (-62, 145), (-15, 158), (72, 160), (84, 120), (118, 40), (118, -62), (10, -62), (-20, -40), (-45, 5), (-62, 18), (-88, 44), (-97, 62)],
 [(-12, -105), (65, -105), (65, -160), (-12, -160)],
]
rr, cc = np.mgrid[0:N, 0:N]
gx, gy = to_xy(rr, cc)
inside = np.zeros((N, N), bool)
for P in EXC: inside |= MPath(P).contains_points(np.c_[gx.ravel(), gy.ravel()]).reshape(N, N)
tree = binary_dilation(ch > 2.5, disk(3))
from scipy.ndimage import median_filter
from scipy.ndimage import maximum_filter
chm = maximum_filter(np.load("lidar/sfn_dsm25.npy"), 3) - d       # 0.75 m max: one return per 25 cm cell is rare, this closes the scan-line gaps
W = (median_filter(chm, 3) > .22) & (chm < 2.4) & ~tree & inside
W = binary_closing(W, disk(1)) & inside
W = remove_small_objects(W, max_size=10)
print('wall cells', int(W.sum()), 'area m2', W.sum() * CS * CS)
# ---- round houses, found on the wall centre lines (skeleton): rings of 1.5–3.6 m radius
ys, xs = np.nonzero(inside); r0, r1, c0, c1 = ys.min() - 20, ys.max() + 20, xs.min() - 20, xs.max() + 20
Ws = W[r0:r1, c0:c1]
SK = skeletonize(Ws)
radii = np.arange(6, 14.5, .5)            # px: 1.5 to 3.6 m
Hs = hough_circle(binary_dilation(SK, disk(1)), radii)
acc, cx_, cy_, rad_ = hough_circle_peaks(Hs, radii, min_xdistance=8, min_ydistance=8, threshold=.25, total_num_peaks=1500)
wy, wx = np.nonzero(SK)
from scipy.spatial import cKDTree
kd = cKDTree(np.c_[wx, wy])
ang = np.linspace(0, 2 * np.pi, 72, endpoint=False)
def cover(cx, cy, r):   # share of the ring on a wall centre line (±0.4 m), and the worst of its four quadrants
    px = cx + r * np.cos(ang); py = cy + r * np.sin(ang)
    hit = kd.query(np.c_[px, py])[0] <= 1.6
    return float(hit.mean()), float(hit.reshape(4, -1).mean(1).min())
def interior(cx, cy, r):   # wall centre-line cells on the floor (a house floor is empty), per m2
    ri = min(r - 3, .75 * r); return len(kd.query_ball_point((cx, cy), ri)) / max(np.pi * ri ** 2 * CS * CS, .5)
def refine(cx, cy, r):
    for _ in range(8):
        idx = kd.query_ball_point((cx, cy), r + 3); P = np.c_[wx[idx], wy[idx]].astype(float)
        dd = np.hypot(P[:, 0] - cx, P[:, 1] - cy); P = P[np.abs(dd - r) < 2.5]
        if len(P) < 15: break
        A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]; b = (P ** 2).sum(1)
        s_, *_ = np.linalg.lstsq(A, b, rcond=None); cx, cy = s_[0], s_[1]; r = float(np.sqrt(max(s_[2] + cx * cx + cy * cy, 1)))
    return cx, cy, r
cand = []
for a_, x, y, r in zip(acc, cx_, cy_, rad_):
    x2, y2, r2 = refine(float(x), float(y), float(r))
    if not (6 <= r2 <= 14.5): continue
    (cv, q4), it = cover(x2, y2, r2), interior(x2, y2, r2)
    if cv >= .7 and q4 >= .4 and it <= .6: cand.append((cv, x2, y2, r2))
cand.sort(reverse=True); houses = []
for cv, x, y, r in cand:
    if any(np.hypot(x - hx, y - hy) < (r + hr) - 2 for _, hx, hy, hr in houses): continue
    houses.append((cv, x, y, r))
print('houses', len(houses))
# ---- straight walls: drop ring cells, skeletonise
Wr = SK.copy()
for _, x, y, r in houses:
    yy, xx = np.ogrid[:Ws.shape[0], :Ws.shape[1]]; dd = np.hypot(xx - x, yy - y); Wr[np.abs(dd - r) < 2.2] = False
sk = remove_small_objects(Wr, max_size=6, connectivity=2)
# trace skeleton into polylines (split at junctions)
pts = set(zip(*np.nonzero(sk)))
def nb(p): return [(p[0] + a, p[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (p[0] + a, p[1] + b) in pts]
deg = {p: len(nb(p)) for p in pts}
seen = set(); lines = []
def walk(a, b):
    path = [a, b]; seen.add(frozenset((a, b)))
    while deg[path[-1]] == 2:
        nx = [q for q in nb(path[-1]) if frozenset((path[-1], q)) not in seen]
        if not nx: break
        seen.add(frozenset((path[-1], nx[0]))); path.append(nx[0])
    return path
for p in pts:
    if deg[p] != 2:
        for q in nb(p):
            if frozenset((p, q)) not in seen: lines.append(walk(p, q))
for p in pts:   # closed loops
    if deg[p] == 2 and all(frozenset((p, q)) not in seen for q in nb(p)):
        lines.append(walk(p, nb(p)[0]))
out = []
for L in lines:
    L = np.array(L, float)
    ln = np.sum(np.linalg.norm(np.diff(L, axis=0), axis=1)) * CS
    if ln < 2: continue
    S = approximate_polygon(L, 1.2)            # 0.3 m
    R_, C_ = S[:, 0] + r0, S[:, 1] + c0
    x, y = to_xy(R_, C_)
    hv = ch[(L[:, 0] + r0).astype(int), (L[:, 1] + c0).astype(int)]
    out.append({'pts': np.round(np.c_[x, y], 2).tolist(), 'h': round(float(np.median(hv[hv > .1])) if (hv > .1).any() else .3, 2), 'len': round(float(ln), 1)})
hs = []
for cv, x, y, r in houses:
    X, Y = to_xy(y + r0, x + c0)
    yy, xx = np.ogrid[:Ws.shape[0], :Ws.shape[1]]; dd = np.hypot(xx - x, yy - y); ring = (np.abs(dd - r) < 1.5) & Ws
    hv = ch[r0:r1, c0:c1][ring]; hv = hv[hv > .1]   # only the cells with a return on the wall (≈ half the 25 cm cells have none, and fall back to the ground)
    h = float(np.median(hv)) if len(hv) else .4
    hs.append([round(float(X), 2), round(float(Y), 2), round(2 * r * CS, 2), round(h, 2), round(cv, 2)])
json.dump({'houses': hs, 'lines': out, 'exc': EXC}, open('lidar/sfn_walls.json', 'w'))
dia = np.array([h[2] for h in hs]); print('diameter m: min %.2f median %.2f max %.2f' % (dia.min(), np.median(dia), dia.max()))
print('lines', len(out), 'total length m', round(sum(o['len'] for o in out)))
