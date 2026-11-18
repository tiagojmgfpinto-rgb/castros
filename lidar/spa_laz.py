# Castro de São Paio (Labruge, Vila do Conde): terrain products on a 25 cm grid (PT-TM06, row 0 = north).
# The castro sits 40-60 m west of the line x = -50000 that splits the DGT LiDAR 2025 blocks 149480 and 150480. For the
# land side (x >= -50000) we have the point cloud LO-150480-07-2025_v05.laz (157 MB, in the project files); for the castro
# itself (block 149480) only the MDT and MDS rasters of 50 cm (MDT/MDS-50cm-149480-07-2025_v03.tif, sent by Tiago), which are
# resampled (bilinear) onto the 25 cm grid. The sea has no data in the rasters: set to -0.6 m (mean low water, approx.).
# Usage: /opt/bvenv/bin/python lidar/spa_laz.py [laz] [dir with the tif]
# Outputs (lidar/): spa_dtm25.npy, spa_dsm25.npy, spa_bld25.npy (class 6, LAZ side only), spa_cnt25.npy (ground points per
# cell, -1 where the 50 cm rasters were used), spa_box.json
import sys, json, glob, numpy as np, laspy, rasterio
from scipy.interpolate import LinearNDInterpolator
from rasterio.merge import merge
LAZ = sys.argv[1] if len(sys.argv) > 1 else '/mnt/project-files/LO-150480-07-2025_v05.laz'
TIF = sys.argv[2] if len(sys.argv) > 2 else 'lidar/raw'
XC, YC, HALF, CS = -50040.0, 179355.0, 115.0, .25
x0, y1 = XC - HALF, YC + HALF; N = int(2 * HALF / CS)
gx, gy = (np.arange(N) + .5) * CS + x0, y1 - (np.arange(N) + .5) * CS
GX, GY = np.meshgrid(gx, gy)
# ---- 50 cm rasters (both blocks), bilinear onto the 25 cm grid
def ras(kind):
    fs = [rasterio.open(f) for f in sorted(glob.glob(f'{TIF}/*{kind}-50cm-1[45][09]480-07-2025_v03.tif'))]
    a, tr = merge(fs, bounds=(x0 - 2, y1 - 2 * HALF - 2, x0 + 2 * HALF + 2, y1 + 2), res=.5, nodata=-999)
    a = a[0].astype(np.float32); a[a <= -998] = np.nan
    from scipy.ndimage import map_coordinates
    r = (tr.f - GY) / .5 - .5; c = (GX - tr.c) / .5 - .5
    return map_coordinates(a, [r, c], order=1, cval=np.nan, prefilter=False)
mdt = ras('MDT'); mds = ras('MDS')
print('raster nan (sea)', round(float(np.isnan(mdt).mean()), 3))
# ---- point cloud, land side
X = []; Y = []; Z = []; C = []
with laspy.open(LAZ) as f:
    for p in f.chunk_iterator(5_000_000):
        x = np.asarray(p.x); y = np.asarray(p.y)
        m = (x >= x0 - 2) & (x < x0 + 2 * HALF + 2) & (y > y1 - 2 * HALF - 2) & (y <= y1 + 2)
        X.append(x[m]); Y.append(y[m]); Z.append(np.asarray(p.z)[m]); C.append(np.asarray(p.classification)[m])
x, y, z, c = map(np.concatenate, (X, Y, Z, C))
print('points', len(x), 'classes', {int(k): int(v) for k, v in zip(*np.unique(c, return_counts=True))})
col = ((x - x0) / CS).astype(int); row = ((y1 - y) / CS).astype(int)
ok = (col >= 0) & (col < N) & (row >= 0) & (row < N); idx = row * N + col
g = c == 2
tin = LinearNDInterpolator(np.c_[x[g], y[g]], z[g])(GX, GY).astype(np.float32)
cnt = np.bincount(idx[ok & g], minlength=N * N).reshape(N, N).astype(np.int16)
keep = ok & (c != 7) & (c != 18)
dsm = np.full(N * N, -1e9, np.float32); np.maximum.at(dsm, idx[keep], z[keep].astype(np.float32)); dsm = dsm.reshape(N, N)
bld = np.zeros(N * N, bool); bld[idx[ok & (c == 6)]] = True; bld = bld.reshape(N, N)
land = GX >= -50000.0
print('LAZ ground pts per m2 (land side)', round(float(cnt[land].sum() / (land.sum() * CS * CS)), 2),
      'empty 1 m cells', round(float((cnt[land].reshape(-1) == 0).mean()), 3))
# 1 m cells with no ground point on the land side (DGT masks / water / buildings)
c1 = cnt[:, :].reshape(N // 4, 4, N // 4, 4).sum((1, 3)); l1 = land.reshape(N // 4, 4, N // 4, 4).all((1, 3))
print('land 1 m cells without ground points', round(float((c1[l1] == 0).mean()), 3))
# ---- merge: LAZ TIN on the land side, 50 cm MDT on the castro side; feather 1 m across the seam
w = np.clip((GX - (-50000.0)) / 1.0, 0, 1)
dtm = np.where(np.isnan(tin), mdt, tin * w + np.nan_to_num(mdt, nan=0) * (1 - w) if True else tin)
dtm = np.where(land, np.where(np.isnan(tin), mdt, tin), mdt)
seam = (np.abs(GX + 50000) < 3) & ~np.isnan(tin) & ~np.isnan(mdt)
print('seam check |TIN - MDT| median', round(float(np.median(np.abs(tin - mdt)[seam])), 3))
dsm = np.where(land & (dsm > -1e8), np.maximum(dsm, np.nan_to_num(dtm, nan=-9)), mds)
SEA = -0.6
dtm = np.where(np.isnan(dtm), SEA, dtm); dsm = np.where(np.isnan(dsm), dtm, np.maximum(dsm, dtm))
cnt = np.where(land, cnt, -1)
np.save('lidar/spa_dtm25.npy', dtm.astype(np.float32)); np.save('lidar/spa_dsm25.npy', dsm.astype(np.float32))
np.save('lidar/spa_bld25.npy', bld); np.save('lidar/spa_cnt25.npy', cnt)
json.dump({'x0': x0, 'y1': y1, 'cs': CS, 'n': N, 'xc': XC, 'yc': YC, 'seam_x': -50000.0, 'sea': SEA}, open('lidar/spa_box.json', 'w'))
print('ok', N)
