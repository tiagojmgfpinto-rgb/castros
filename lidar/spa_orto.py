# Castro de São Paio: Google satellite tiles (z19 0.224 m/px, z20 0.112 m/px) captured in 2026-11 as screenshots of a
# canvas mosaic (lidar/spa/orto/z<z>_<x>_<y>.jpg = canvas crop at offset x,y, 1024x768 canvas px shown as 800x600),
# stitched and resampled onto the PT-TM06 grid of the site (0.25 m), then shifted onto the LiDAR by cross-correlating
# edges with the MDS. Usage: /opt/bvenv/bin/python lidar/spa_orto.py  -> lidar/spa/orto_z19.png, orto_z20.png, orto.json
import json, glob, re, numpy as np
from PIL import Image
from pyproj import Transformer
from scipy.ndimage import map_coordinates, gaussian_filter, sobel
B = json.load(open('lidar/spa_box.json'))
MOS = {19: (41.28175, -8.7303, 180), 20: (41.2817, -8.7306, 64)}   # centre lat, lon and half size (m) of each mosaic
K = 800 / 1024
inv = Transformer.from_crs(3763, 4326, always_xy=True)
out = {}
for z, (lat, lon, half) in MOS.items():
    n = 2 ** z; tx = (lon + 180) / 360 * n
    ty = (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) / 2 * n
    mpp = 40075016.686 * np.cos(np.radians(lat)) / n / 256; hp = half / mpp / 256
    x0t, y0t = tx - hp, ty - hp; S = round(2 * hp * 256)
    M = np.zeros((int(S * K) + 2, int(S * K) + 2, 3), np.uint8)
    for f in glob.glob(f'lidar/spa/orto/z{z}_*.jpg'):
        ox, oy = map(int, re.findall(r'_(\d+)', f)[-2:])
        a = np.asarray(Image.open(f).convert('RGB')); r0, c0 = round(oy * K), round(ox * K)
        M[r0:r0 + a.shape[0], c0:c0 + a.shape[1]] = a
    N = B['n']; xs = B['x0'] + (np.arange(N) + .5) * B['cs']; ys = B['y1'] - (np.arange(N) + .5) * B['cs']
    X, Y = np.meshgrid(xs, ys); lo, la = inv.transform(X, Y)
    px = ((lo + 180) / 360 * n - x0t) * 256 * K
    py = ((1 - np.log(np.tan(np.radians(la)) + 1 / np.cos(np.radians(la))) / np.pi) / 2 * n - y0t) * 256 * K
    out[z] = (M, px, py)
# shift onto the LiDAR: edges of the z19 image vs edges of the 25 cm MDS (buildings, walls, boardwalk, rocks)
dsm = np.load('lidar/spa_dsm25.npy'); dtm = np.load('lidar/spa_dtm25.npy')
def edges(a): a = gaussian_filter(a, 2); e = np.hypot(sobel(a, 0), sobel(a, 1)); return (e - e.mean()) / e.std()
EL = edges(np.clip(dsm - dtm, 0, 6) + .4 * dtm)
best = {}
for z, (M, px, py) in out.items():
    g = M.astype(float).mean(2); sc = []
    # resample once, then shift the 0.25 m grid
    I = map_coordinates(g, [py.ravel(), px.ravel()], order=1, cval=np.nan).reshape(py.shape)
    EI = edges(np.nan_to_num(I, nan=np.nanmean(I)))
    c = B['n'] // 2; h = int(90 / B['cs'])
    W = slice(c - h, c + h)
    for dx in range(-28, 29):      # cells (0.25 m)
        for dy in range(-28, 29):
            a = EI[c - h - dy:c + h - dy, c - h + dx:c + h + dx]   # image shifted by (dx east, dy north)... sample
            sc.append((float((a * EL[W, W]).mean()), dx, dy))
    s, dx, dy = max(sc); best[z] = (dx, dy, s)
    print('z', z, 'best shift (cells E,N)', dx, dy, 'score', round(s, 3))
    # apply: image pixel at grid (r, c) comes from (r - dy, c + dx)... build the aligned RGB
    rgb = np.stack([map_coordinates(M[..., k].astype(float), [py.ravel(), px.ravel()], order=1).reshape(py.shape) for k in range(3)], -1)
    rgb = np.roll(np.roll(rgb, dy, 0), -dx, 1)
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(f'lidar/spa/orto_z{z}.png')
json.dump({str(z): {'shift_e_m': -best[z][0] * B['cs'], 'shift_n_m': best[z][1] * B['cs'], 'score': best[z][2]} for z in best}, open('lidar/spa/orto.json', 'w'), indent=1)
