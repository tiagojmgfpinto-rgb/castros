# Castro de Sabroso: georeferences the 1930 plan (blend/sab_plan.py, plan px) on the LiDAR ground model (lidar/sab_dtm25.npy).
# The rampart of the upper enclosure is clear in the 25 cm ground model (clearing, no trees): its crest line was traced by eye
# (TRACE, local metres x east / z south of the site point) and the plan walls W_WEST + W_EAST_INNER are fitted to it with a
# similarity transform (shift, rotation, scale), least squares on point-to-curve distance. Writes blend/sab_fit.json.
# Result (2026-10): rms 0.9 m; upper enclosure 0.73 ha (published 0.7 ha). The previous fit, on the 1929 protection-zone markers,
# put the plan about 20 m too far north.
import json, math, sys, numpy as np
from scipy.optimize import minimize
sys.path.insert(0, 'blend'); import sab_plan as P
TRACE = np.array([(-58, 30), (-54, 18), (-50, 8), (-44, -3), (-36, -11), (-26, -17), (-14, -21), (0, -22), (10, -16), (18, -6), (24, 4), (29, 14), (33, 24), (37, 32)], float)
old = json.load(open('blend/sab_fit.json')); mean = np.array(old['mean']); K = old['K']; x0 = old.get('old_x', old['x'])
def tr(p, x):
    tx, tz, th, k = x; q = (np.asarray(p, float) - mean) * K * k; c, s = math.cos(th), math.sin(th)
    return np.stack([q[..., 0] * c - q[..., 1] * s, q[..., 0] * s + q[..., 1] * c], -1) + [tx, tz]
PL = np.array(P.W_WEST[::-1] + P.W_EAST_INNER, float)
def d2curve(q, C):
    a = C[:-1]; b = C[1:]; ab = b - a; t = np.clip(((q[:, None] - a) * ab).sum(-1) / (ab * ab).sum(-1), 0, 1)
    return np.sqrt(((q[:, None] - (a + t[..., None] * ab)) ** 2).sum(-1)).min(1)
f = lambda x: (d2curve(TRACE, tr(PL, x)) ** 2).mean()
best = None
for th in np.radians(np.arange(-40, 41, 5)) + x0[2]:
    for k in (.9, 1, 1.1):
        r = minimize(f, [x0[0], x0[1] + 20, th, k], method='Nelder-Mead', options={'maxiter': 5000, 'xatol': 1e-4, 'fatol': 1e-6})
        if best is None or r.fun < best.fun: best = r
x = best.x; up = tr(P.W_WEST[::-1] + P.W_EAST_INNER, x)
area = abs(np.sum(up[:, 0] * np.roll(up[:, 1], -1) - np.roll(up[:, 0], -1) * up[:, 1])) / 2 / 1e4
print('rms', round(math.sqrt(best.fun), 2), 'm; upper enclosure', round(area, 3), 'ha; x', x)
json.dump({'mean': mean.tolist(), 'K': K, 'x': [float(v) for v in x], 'old_x': list(x0), 'rms': math.sqrt(best.fun), 'method': 'lidar rampart trace'}, open('blend/sab_fit.json', 'w'))
