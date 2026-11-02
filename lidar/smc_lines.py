# Castro de Santa Marta das Cortiças: snaps the lines traced by eye (blend/smc_trace.py) onto the LiDAR scarps.
# Each vertex (densified every 3 m) moves along the outward normal, within ±7 m, to the steepest point of the 25 cm
# ground model (lidar/smc_dtm25.npy, with the boulders removed (grey opening 6 m) and smoothed 0.5 m); the line is then smoothed. Prints the mean shift and the
# height drop across each line; writes blend/smc_lines.json (local metres, x east, y north).
import json, sys, numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter, gaussian_filter1d
sys.path.insert(0, 'blend'); from smc_trace import LINES
from scipy.ndimage import grey_opening
d = gaussian_filter(grey_opening(np.load('lidar/smc_dtm25.npy'), size=(25, 25)), 2); B = json.load(open('lidar/smc_box.json'))   # granite boulders (< 6 m) removed first
X0L, Y0L = -21894.7, 205017.0
def h(x, y):
    c = (X0L + np.asarray(x) - B['x0']) / B['cs'] - .5; r = (B['y1'] - (Y0L + np.asarray(y))) / B['cs'] - .5
    return map_coordinates(d, [r, c], order=1)
def dense(p, step, closed):
    p = np.asarray(p, float); out = [p[0]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step))); out += [a + (b - a) * t for t in np.linspace(0, 1, n + 1)[1:]]
    out = np.array(out); return out[:-1] if closed else out
res = {}
for nm, pts in LINES.items():
    closed = pts[0] == pts[-1]; p = dense(pts, 3, closed); n = len(p)
    t = np.gradient(p, axis=0) if not closed else (np.roll(p, -1, 0) - np.roll(p, 1, 0)); t /= np.linalg.norm(t, axis=1, keepdims=True)
    nr = np.stack([t[:, 1], -t[:, 0]], 1)
    # outward = downhill
    if np.mean(h(*(p + nr * 4).T) - h(*(p - nr * 4).T)) > 0: nr = -nr
    o = np.arange(-7, 7.01, .25); Q = p[:, None] + nr[:, None] * o[None, :, None]
    z = h(Q[..., 0], Q[..., 1]); s = -np.gradient(z, .25, axis=1)
    k = np.argmax(s, 1); off = gaussian_filter1d(o[k].astype(float), 2, mode='wrap' if closed else 'nearest')
    q = p + nr * (off[:, None] - 1.5)          # wall on the crest, 1.5 m inside the steepest point
    drop = h(*(q - nr * 1).T) - h(*(q + nr * 7).T)
    res[nm] = {'pts': np.round(q, 2).tolist(), 'closed': closed, 'drop': float(np.median(drop)), 'shift': float(np.mean(np.abs(off))),
               'len': float(np.sum(np.linalg.norm(np.diff(np.vstack([q, q[:1]]) if closed else q, axis=0), axis=1)))}
    print(nm, 'n', n, 'mean shift %.1f m' % res[nm]['shift'], 'median drop %.1f m' % res[nm]['drop'], 'max slope median %.0f°' % np.degrees(np.arctan(np.median(s.max(1)))), 'length %.0f m' % res[nm]['len'])
    if closed:
        A = abs(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1])) / 2; print('   area %.2f ha' % (A / 1e4)); res[nm]['area_ha'] = A / 1e4
json.dump(res, open('blend/smc_lines.json', 'w'))
