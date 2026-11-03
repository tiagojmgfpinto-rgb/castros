# Castro Máximo: fills the hole that the DGT left in the LiDAR 2025 over the prison (no points within ≈ 190 m of it, in the
# point cloud and in the MDT/MDS, where the 50 cm grid is only a radial interpolation). The hole covers the east slope of the
# summit, the end of Rua do Castro Máximo and the houses down to Av. Artur Soares.
# Fill: coarse relief of the AWS Terrain Tiles (terrarium z15, mostly SRTM 30 m of 2000), corrected by a harmonic (Laplace)
# surface so that it meets the LiDAR along the whole edge of the hole, then smoothed. Approximate: listed in the gaps.
# Usage: /opt/bvenv/bin/python lidar/cmx_fill.py  (after lidar/cmx_laz.py) -> lidar/cmx_dtmf25.npy, lidar/cmx_void25.npy
import json, math, os, urllib.request, numpy as np
from PIL import Image
from pyproj import Transformer
from scipy.ndimage import gaussian_filter, map_coordinates, zoom, binary_dilation
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve
B = json.load(open('lidar/cmx_box.json')); N = B['n']; CS = B['cs']
dtm = np.load('lidar/cmx_dtm25.npy'); cnt = np.load('lidar/cmx_cnt25.npy')
void = gaussian_filter((cnt > 0).astype(np.float32), 8) < .02          # no point within ≈ 2 m
void = binary_dilation(void, iterations=8) | np.isnan(dtm)              # drop the 2 m fringe of the TIN
print('void cells', void.sum(), 'area %.2f ha' % (void.sum() * CS * CS / 1e4))
# terrarium z15 tiles
Z = 15; T = Transformer.from_crs(3763, 4326, always_xy=True); D = '/tmp/terrarium15'; os.makedirs(D, exist_ok=True)
lon0, lat1 = T.transform(B['x0'], B['y1']); lon1, lat0 = T.transform(B['x0'] + N * CS, B['y1'] - N * CS)
tx = lambda lon: (lon + 180) / 360 * 2 ** Z; ty = lambda lat: (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * 2 ** Z
X0t, X1t, Y0t, Y1t = int(tx(lon0)), int(tx(lon1)), int(ty(lat1)), int(ty(lat0))
M = np.zeros(((Y1t - Y0t + 1) * 256, (X1t - X0t + 1) * 256))
for i, x in enumerate(range(X0t, X1t + 1)):
    for j, y in enumerate(range(Y0t, Y1t + 1)):
        f = f'{D}/{x}_{y}.png'
        if not os.path.exists(f): urllib.request.urlretrieve(f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png', f)
        a = np.asarray(Image.open(f).convert('RGB'), float); M[j * 256:(j + 1) * 256, i * 256:(i + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
# 1 m working grid
K = 4; n = N // K
gx = B['x0'] + (np.arange(n) + .5) * K * CS; gy = B['y1'] - (np.arange(n) + .5) * K * CS
GX, GY = np.meshgrid(gx, gy); lon, lat = T.transform(GX, GY)
terr = map_coordinates(M, [(ty(lat) - Y0t) * 256 - .5, (tx(lon) - X0t) * 256 - .5], order=1)
d1 = np.nanmean(np.where(void, np.nan, dtm).reshape(n, K, n, K), axis=(1, 3))
v1 = void.reshape(n, K, n, K).mean(axis=(1, 3)) > .25
v1 |= np.isnan(d1)
res = np.where(v1, 0, d1 - terr)
print('terrain tiles − LiDAR outside the hole: mean %.1f m, sd %.1f m' % (np.mean(-res[~v1]), np.std(res[~v1])))
# Laplace on the hole cells, Dirichlet = LiDAR residual at the edge
idx = -np.ones((n, n), int); ys, xs = np.nonzero(v1); idx[ys, xs] = np.arange(len(ys))
A = lil_matrix((len(ys), len(ys))); b = np.zeros(len(ys))
for k, (y, x) in enumerate(zip(ys, xs)):
    nb = [(y + dy, x + dx) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= y + dy < n and 0 <= x + dx < n]
    A[k, k] = len(nb)
    for (yy, xx) in nb:
        if v1[yy, xx]: A[k, idx[yy, xx]] = -1
        else: b[k] += res[yy, xx]
res[ys, xs] = spsolve(A.tocsr(), b)
fill1 = gaussian_filter(terr + res, 3)
fill = zoom(fill1, K, order=1)[:N, :N]
w = np.clip(gaussian_filter(void.astype(np.float32), 8) * 1.6, 0, 1)    # feather 2 m into the LiDAR
out = np.where(void, fill, dtm); out = w * fill + (1 - w) * np.where(np.isnan(out), fill, out)
np.save('lidar/cmx_dtmf25.npy', out.astype(np.float32)); np.save('lidar/cmx_void25.npy', void)
print('filled: hole %.1f–%.1f m' % (out[void].min(), out[void].max()))
