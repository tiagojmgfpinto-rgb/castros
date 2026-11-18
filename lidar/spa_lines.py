# Castro de São Paio: the east talude (rampart bank) traced on the LiDAR ground model.
# Hand seed on the crest (from height profiles across the bank), then a tracker walks along the scarp in 2 m steps: at each step
# it looks across (±7 m) for the steepest drop to the outside, puts the crest at the highest point within 6 m inside that drop and
# stops where the drop falls under 1.5 m. Local metres from the box centre (lidar/spa_box.json: xc, yc), x east, y north.
# Usage: /opt/bvenv/bin/python lidar/spa_lines.py  -> blend/spa_lines.json
import json, numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter, gaussian_filter1d
B = json.load(open('lidar/spa_box.json')); dtm = gaussian_filter(np.load('lidar/spa_dtm25.npy'), 1.2)
def h(x, y):
    r = (B['y1'] - (B['yc'] + np.asarray(y))) / B['cs'] - .5; c = (B['xc'] + np.asarray(x) - B['x0']) / B['cs'] - .5
    return map_coordinates(dtm, [np.atleast_1d(r).ravel(), np.atleast_1d(c).ravel()], order=1).reshape(np.shape(r))
def walk(p, d, maxn=80):
    pts = []; drops = []; scarp = []
    for _ in range(maxn):
        n = np.array([d[1], -d[0]])              # right-hand normal (outside when walking north-west)
        o = np.arange(-7, 7.01, .25); pr = h(p[0] + n[0] * o, p[1] + n[1] * o)
        g = np.gradient(pr, .25); k = int(np.argmin(g))       # steepest descent towards outside
        top = o[k]; ins = (o >= top - 6) & (o <= top); kc = int(np.argmax(np.where(ins, pr, -1e9)))
        drop = float(pr[kc] - h(p[0] + n[0] * (o[k] + 4), p[1] + n[1] * (o[k] + 4)))
        if drop < 1.5: break
        c = p + n * o[kc]; pts.append(c); drops.append(drop); scarp.append(p + n * top)
        if len(pts) >= 3:
            v = pts[-1] - pts[-3]; v /= np.linalg.norm(v); d = .6 * d + .4 * v; d /= np.linalg.norm(d)
        p = c + d * 2.0
    return pts, drops, scarp
d0 = np.array([55, -75.]); d0 /= np.linalg.norm(d0); seed = np.array([-11.1, 34.2]) + np.array([.806, .591]) * 4
# walking south-east the outside is on the left
def walk_left(p, d, maxn=80):
    pts = []; drops = []; sc = []
    for _ in range(maxn):
        n = np.array([-d[1], d[0]])
        o = np.arange(-7, 7.01, .25); pr = h(p[0] + n[0] * o, p[1] + n[1] * o)
        g = np.gradient(pr, .25); k = int(np.argmin(g)); top = o[k]
        ins = (o >= top - 6) & (o <= top); kc = int(np.argmax(np.where(ins, pr, -1e9)))
        drop = float(pr[kc] - h(p[0] + n[0] * (o[k] + 4), p[1] + n[1] * (o[k] + 4)))
        if drop < 1.5: break
        c = p + n * o[kc]; pts.append(c); drops.append(drop); sc.append(p + n * top)
        if len(pts) >= 3:
            v = pts[-1] - pts[-3]; v /= np.linalg.norm(v); d = .6 * d + .4 * v; d /= np.linalg.norm(d)
        p = c + d * 2.0
    return pts, drops, sc
fw, dfw, sfw = walk_left(seed, d0)
bw, dbw, sbw = walk(seed, -d0)
P = np.array(bw[::-1] + fw); D = np.array(dbw[::-1] + dfw); S = np.array(sbw[::-1] + sfw)
P = np.stack([gaussian_filter1d(P[:, 0], 1.2, mode='nearest'), gaussian_filter1d(P[:, 1], 1.2, mode='nearest')], 1)
L = float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
crest = h(P[:, 0], P[:, 1])
print('T1 points', len(P), 'length', round(L, 1), 'drop median', round(float(np.median(D)), 2), 'min/max', round(float(D.min()), 2), round(float(D.max()), 2))
print('start', P[0].round(1), 'end', P[-1].round(1), 'crest z', round(float(crest.min()), 1), round(float(crest.max()), 1))
json.dump({'T1': {'pts': P.round(2).tolist(), 'drop': D.round(2).tolist(), 'scarp': S.round(2).tolist(), 'len': L, 'closed': False,
                  'drop_median': float(np.median(D))}}, open('blend/spa_lines.json', 'w'))
