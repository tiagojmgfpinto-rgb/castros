# Citânia de Sanfins (Paços de Ferreira): products from the DGT LiDAR 2025 point clouds LO-178484, 178485, 179484 and 179485
# (LO-*-07-2025_v05.laz, 140-210 MB each, too big for the repo: in the project files, /mnt/project-files/).
# Usage: /opt/bvenv/bin/python lidar/sfn_laz.py [dir with the .laz]
# Box of 680 m (PT-TM06) holding the whole walled area (≈ 440 × 530 m) and the summit of S. Romão. Outputs (lidar/, row 0 = north):
#   sfn_dtm25.npy  ground (class 2) TIN-interpolated, 0.25 m
#   sfn_dsm25.npy  highest return per cell (noise dropped; gaps filled from the TIN ground), 0.25 m
#   sfn_bld25.npy  cells with class 6 (building) points, 0.25 m
#   sfn_gcnt1.npy  ground points per 1 m cell (to find the zones the DGT left empty)
#   sfn_box.json   box origin and cell size
import sys, json, numpy as np, laspy
from scipy.interpolate import LinearNDInterpolator
D = sys.argv[1] if len(sys.argv) > 1 else '/mnt/project-files'
XC, YC, HALF, CS = -21224.0, 183819.0, 340.0, .25
x0, y1 = XC - HALF, YC + HALF; N = int(2 * HALF / CS)
X = []; Y = []; Z = []; C = []
for b in ('178484', '178485', '179484', '179485'):
    with laspy.open(f'{D}/LO-{b}-07-2025_v05.laz') as f:
        h = f.header
        if h.maxs[0] < x0 - 2 or h.mins[0] > x0 + 2 * HALF + 2 or h.maxs[1] < y1 - 2 * HALF - 2 or h.mins[1] > y1 + 2: continue
        for p in f.chunk_iterator(5_000_000):
            x = np.asarray(p.x); y = np.asarray(p.y)
            m = (x >= x0 - 2) & (x < x0 + 2 * HALF + 2) & (y > y1 - 2 * HALF - 2) & (y <= y1 + 2)
            X.append(x[m]); Y.append(y[m]); Z.append(np.asarray(p.z)[m]); C.append(np.asarray(p.classification)[m])
    print(b, sum(len(a) for a in X), flush=True)
x, y, z, c = map(np.concatenate, (X, Y, Z, C))
print('classes', {int(k): int(v) for k, v in zip(*np.unique(c, return_counts=True))})
col = ((x - x0) / CS).astype(int); row = ((y1 - y) / CS).astype(int)
ok = (col >= 0) & (col < N) & (row >= 0) & (row < N); idx = row * N + col
g = c == 2
n1 = N // 4; i1 = (row // 4) * n1 + col // 4
gc = np.bincount(i1[ok & g], minlength=n1 * n1).reshape(n1, n1).astype(np.uint16)
print('ground pts per m2: median', np.median(gc), 'empty 1 m cells', int((gc == 0).sum()), 'of', gc.size)
gx, gy = (np.arange(N) + .5) * CS + x0, y1 - (np.arange(N) + .5) * CS
GX, GY = np.meshgrid(gx, gy)
dtm = LinearNDInterpolator(np.c_[x[g], y[g]], z[g])(GX, GY).astype(np.float32)
print('ground pts', g.sum(), 'nan', np.isnan(dtm).sum(), flush=True)
keep = ok & (c != 7) & (c != 18)          # drop noise
dsm = np.full(N * N, -1e9, np.float32); np.maximum.at(dsm, idx[keep], z[keep].astype(np.float32))
dsm = dsm.reshape(N, N); dsm = np.where(dsm < -1e8, dtm, np.maximum(dsm, dtm))
bld = np.zeros(N * N, bool); bld[idx[ok & (c == 6)]] = True
np.save('lidar/sfn_dtm25.npy', dtm); np.save('lidar/sfn_dsm25.npy', dsm.astype(np.float32)); np.save('lidar/sfn_bld25.npy', bld.reshape(N, N))
np.save('lidar/sfn_gcnt1.npy', gc)
json.dump({'x0': x0, 'y1': y1, 'cs': CS, 'n': N}, open('lidar/sfn_box.json', 'w'))
print('ok', N)
