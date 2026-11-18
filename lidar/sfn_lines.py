# Citânia de Sanfins: snaps the wall lines traced by eye (blend/sfn_trace.py) onto the standing walls of the LiDAR 2025.
# Each vertex (densified every 2 m) moves along the normal, within ±4 m, to the highest point of MDS − MDT (0.75 m max filter,
# trees > 2.5 m masked); where no wall stands out (< 0.2 m) the traced position is kept. The offsets are smoothed along the line.
# Width = run around the top above half its height (0.75 m max filter widens it by up to 0.5 m). Prints the mean shift, the share of the line on a visible wall and its median height; writes blend/sfn_lines.json.
import json, sys, numpy as np
from scipy.ndimage import map_coordinates, maximum_filter, gaussian_filter1d
sys.path.insert(0, 'blend'); from sfn_trace import LINES
B = json.load(open('lidar/sfn_box.json')); X0L, Y0L = -21224.03, 183783.55
d = np.load('lidar/sfn_dtm25.npy'); d = np.where(np.isnan(d), np.nanmean(d), d)
ch = maximum_filter(np.load('lidar/sfn_dsm25.npy'), 3) - d; ch[ch > 2.5] = 0
def h(x, y):
    c = (X0L + np.asarray(x) - B['x0']) / B['cs'] - .5; r = (B['y1'] - (Y0L + np.asarray(y))) / B['cs'] - .5
    return map_coordinates(ch, [r, c], order=1)
def dense(p, step):
    p = np.asarray(p, float); out = [p[0]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step))); out += [a + (b - a) * t for t in np.linspace(0, 1, n + 1)[1:]]
    return np.array(out)
res = {}
for nm, pts in LINES.items():
    p = dense(pts, 2); t = np.gradient(p, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True); nr = np.stack([t[:, 1], -t[:, 0]], 1)
    o = np.arange(-4, 4.01, .25); Q = p[:, None] + nr[:, None] * o[None, :, None]
    z = h(Q[..., 0], Q[..., 1]); k = np.argmax(z, 1); zm = z.max(1); vis = zm > .2
    off = np.where(vis, o[k], 0.); off = gaussian_filter1d(off, 1.5, mode='nearest')
    q = p + nr * off[:, None]
    hh = float(np.median(zm[vis])) if vis.any() else 0.
    # width of the standing wall: contiguous run around the top where MDS − MDT stays above half the top height
    wd = []
    for i in np.nonzero(vis)[0]:
        a = b = k[i]; thr = zm[i] / 2
        while a > 0 and z[i, a - 1] > thr: a -= 1
        while b < len(o) - 1 and z[i, b + 1] > thr: b += 1
        wd.append((b - a + 1) * .25)
    wmed = float(np.median(wd)) if wd else 0.
    res[nm] = {'pts': np.round(q, 2).tolist(), 'h': round(hh, 2), 'vis': round(float(vis.mean()), 2), 'w': round(wmed, 2), 'shift': round(float(np.mean(np.abs(off))), 2),
               'len': round(float(np.sum(np.linalg.norm(np.diff(q, axis=0), axis=1))), 1)}
    print(nm, res[nm]['len'], 'm; visible wall on %.0f %%' % (100 * vis.mean()), 'median height %.2f m' % hh, 'width %.2f m' % wmed, 'mean shift %.2f m' % res[nm]['shift'])
json.dump(res, open('blend/sfn_lines.json', 'w'))
