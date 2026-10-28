# Castro de Sabroso: products from the DGT LiDAR 2025 point cloud LO-182505-07-2025_v05.laz (128 MB, too big for the repo:
# it is in the project files, /mnt/project-files/). Usage: /opt/bvenv/bin/python lidar/sab_laz.py [path.laz]
# Box of 360 m around the disc centre (PT-TM06). Outputs (lidar/, row 0 = north, 0.25 m):
#   sab_dtm25.npy  ground (class 2) TIN-interpolated
#   sab_dsm25.npy  highest return per cell (gaps filled from the TIN ground)
#   sab_box.json   box origin and cell size
import sys, json, numpy as np, laspy
from scipy.spatial import Delaunay
from scipy.interpolate import LinearNDInterpolator
LAZ = sys.argv[1] if len(sys.argv) > 1 else '/mnt/project-files/LO-182505-07-2025_v05.laz'
XC, YC, HALF, CS = -17372.0, 204705.0, 180.0, .25
x0, y1 = XC - HALF, YC + HALF; N = int(2 * HALF / CS)
las = laspy.read(LAZ)
x = np.asarray(las.x); y = np.asarray(las.y); z = np.asarray(las.z); c = np.asarray(las.classification)
m = (x >= x0 - 2) & (x < x0 + 2 * HALF + 2) & (y > y1 - 2 * HALF - 2) & (y <= y1 + 2)
x, y, z, c = x[m], y[m], z[m], c[m]
col = ((x - x0) / CS).astype(int); row = ((y1 - y) / CS).astype(int)
ok = (col >= 0) & (col < N) & (row >= 0) & (row < N); idx = row * N + col
g = c == 2
gx, gy = (np.arange(N) + .5) * CS + x0, y1 - (np.arange(N) + .5) * CS
GX, GY = np.meshgrid(gx, gy)
dtm = LinearNDInterpolator(np.c_[x[g], y[g]], z[g])(GX, GY).astype(np.float32)
print('ground pts', g.sum(), 'nan', np.isnan(dtm).sum())
dsm = np.full(N * N, -1e9, np.float32); np.maximum.at(dsm, idx[ok], z[ok].astype(np.float32))
dsm = dsm.reshape(N, N); dsm = np.where(dsm < -1e8, dtm, np.maximum(dsm, dtm))
np.save('lidar/sab_dtm25.npy', dtm); np.save('lidar/sab_dsm25.npy', dsm.astype(np.float32))
json.dump({'x0': x0, 'y1': y1, 'cs': CS, 'n': N}, open('lidar/sab_box.json', 'w'))
print('ok', N)
