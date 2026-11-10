# Citânia de Briteiros: trees with the species of the Minho hillside today (Tiago, 2026-10-28: mostly eucalyptus, then chestnut,
# oak and cork oak; no pines), as blend/dio_sab.py does. The LiDAR trees of app/dio/<id>.json keep their position and height; the species
# comes from height and crown width (canopy model MDS-MDT of lidar/mosaic.py, mean radius in 8 directions where the canopy stays above
# half the tree height). The prototypes are taken from Sabroso with tools/gltf/graft_protos.mjs. Run once after the model export.
# Use: /opt/bvenv/bin/python tools/brit_species.py   (needs lidar/mdt.npy and lidar/mds.npy)
import json, numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
SID = 'guimaraes-citania-de-briteiros'; P = f'app/dio/{SID}.json'
M = json.load(open(P)); S = json.load(open('app/dio/guimaraes-castro-de-sabroso.json'))
if 'pine' not in M['types']: raise SystemExit('already done')
X0L, Y0L = -15192.5388, 206428.3338; CX, CZ, EX = M['cx'], M['cz'], M['ex']   # as in blend/dio_brit.py
CH = gaussian_filter(np.load('lidar/mds.npy').astype(np.float32) - np.load('lidar/mdt.npy').astype(np.float32), 1.2)
def ch(x, y):   # local x east / y north -> canopy height (mosaic: 0.5 m, x from -16000, row 0 at y 207000)
    c = (np.asarray(x) + CX + X0L + 16000) / .5 - .5; r = (207000 - Y0L + (CZ - np.asarray(y))) / .5 - .5
    return map_coordinates(CH, [r, c], order=1, mode='nearest')
ang = np.linspace(0, 2 * np.pi, 8, endpoint=False); rad = np.arange(.5, 8.01, .5)
def crown_r(x, y, h):
    c = ch((x + np.cos(ang)[:, None] * rad[None]).ravel(), (y + np.sin(ang)[:, None] * rad[None]).ravel()).reshape(8, -1) > h * .5
    return float(np.mean([rad[np.argmin(r)] if not r.all() else rad[-1] for r in c]))
old, TY, PAL = M['types'], S['types'], S['pal']; rng = np.random.default_rng(7)
big = [i for i, t in enumerate(M['trees']) if old[t[4]] in ('oak', 'cork', 'pine')]
H = {i: M['trees'][i][3] / EX for i in big}; CR = {i: 2 * crown_r(M['trees'][i][0], M['trees'][i][1], H[i]) / max(H[i], 3) for i in big}
cr0 = float(np.median(list(CR.values())))
for i, t in enumerate(M['trees']):
    if i in CR:
        h_, rr, wf = H[i], rng.random(), float(np.clip(CR[i] / cr0, .7, 1.4))
        pe = (.8 if wf < 1.15 else .45) if h_ >= 12 else (.5 if h_ >= 8 else .15)   # same rule as blend/dio_sab.py
        if rr < pe: sp = 'euc'
        else: sp = str(rng.choice(['chest', 'oak', 'cork'], p=[.45, .35, .2] if wf > 1.15 else ([.25, .35, .4] if h_ < 9 else [.3, .5, .2])))
        if sp == 'euc': kind = 'euc2' if wf < .85 or rng.random() < .3 else 'euc'
        elif sp == 'chest': kind = str(rng.choice(['chest', 'chest2']))
        elif sp == 'cork': kind = str(rng.choice(['cork', 'cork2']))
        else: kind = 'oak2' if wf > 1.15 else ('oak3' if wf < .85 else str(rng.choice(['oak', 'oak2', 'oak3'], p=[.5, .25, .25])))
        t[4] = TY.index(kind); t[5] = int(rng.integers(0, len(PAL[kind]))); t[7:] = [round(wf * (.92 + .16 * rng.random()), 2)]
    else: t[4] = TY.index(old[t[4]])
M['types'], M['pal'] = TY, PAL
json.dump(M, open(P, 'w'), separators=(',', ':'))
from collections import Counter
print(Counter(TY[t[4]] for t in M['trees']))
