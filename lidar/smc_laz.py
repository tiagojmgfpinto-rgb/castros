# Castro de Santa Marta das Cortiças (Braga): products from the DGT LiDAR 2025 point clouds LO-177505, 177506, 178505 and 178506
# (LO-*-07-2025_v05.laz, ~150 MB each, too big for the repo: in the project files, /mnt/project-files/).
# Usage: /opt/bvenv/bin/python lidar/smc_laz.py [dir with the .laz]
# Box of 440 m (PT-TM06) holding the hilltop enclosure, the chapel and the monument. Outputs (lidar/, row 0 = north, 0.25 m):
#   smc_dtm25.npy  ground (class 2) TIN-interpolated
#   smc_dsm25.npy  highest return per cell (gaps filled from the TIN ground)
#   smc_box.json   box origin and cell size
import sys, json, numpy as np, laspy
from scipy.interpolate import LinearNDInterpolator
D = sys.argv[1] if len(sys.argv) > 1 else '/mnt/project-files'
XC, YC, HALF, CS = -21895.0, 205017.0, 220.0, .25
x0, y1 = XC - HALF, YC + HALF; N = int(2 * HALF / CS)
X = []; Y = []; Z = []; C = []
for b in ('177505', '177506', '178505', '178506'):
    with laspy.open(f'{D}/LO-{b}-07-2025_v05.laz') as f:
        h = f.header
        if h.maxs[0] < x0 - 2 or h.mins[0] > x0 + 2 * HALF + 2 or h.maxs[1] < y1 - 2 * HALF - 2 or h.mins[1] > y1 + 2: continue
        for p in f.chunk_iterator(5_000_000):
            x = np.asarray(p.x); y = np.asarray(p.y)
            m = (x >= x0 - 2) & (x < x0 + 2 * HALF + 2) & (y > y1 - 2 * HALF - 2) & (y <= y1 + 2)
            X.append(x[m]); Y.append(y[m]); Z.append(np.asarray(p.z)[m]); C.append(np.asarray(p.classification)[m])
    print(b, sum(len(a) for a in X))
x, y, z, c = map(np.concatenate, (X, Y, Z, C))
print('classes', {int(k): int(v) for k, v in zip(*np.unique(c, return_counts=True))})
col = ((x - x0) / CS).astype(int); row = ((y1 - y) / CS).astype(int)
ok = (col >= 0) & (col < N) & (row >= 0) & (row < N); idx = row * N + col
g = c == 2
gx, gy = (np.arange(N) + .5) * CS + x0, y1 - (np.arange(N) + .5) * CS
GX, GY = np.meshgrid(gx, gy)
dtm = LinearNDInterpolator(np.c_[x[g], y[g]], z[g])(GX, GY).astype(np.float32)
print('ground pts', g.sum(), 'per m2', round(g.sum() / (2 * HALF) ** 2, 1), 'nan', np.isnan(dtm).sum())
keep = ok & (c != 7) & (c != 18)          # drop noise
dsm = np.full(N * N, -1e9, np.float32); np.maximum.at(dsm, idx[keep], z[keep].astype(np.float32))
dsm = dsm.reshape(N, N); dsm = np.where(dsm < -1e8, dtm, np.maximum(dsm, dtm))
# buildings (class 6) mask, for the chapel and the monument
bld = np.zeros(N * N, bool); bld[idx[ok & (c == 6)]] = True
np.save('lidar/smc_dtm25.npy', dtm); np.save('lidar/smc_dsm25.npy', dsm.astype(np.float32)); np.save('lidar/smc_bld25.npy', bld.reshape(N, N))
json.dump({'x0': x0, 'y1': y1, 'cs': CS, 'n': N}, open('lidar/smc_box.json', 'w'))
print('ok', N)
