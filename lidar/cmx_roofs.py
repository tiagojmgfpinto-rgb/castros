# Castro Máximo: houses inside the LiDAR hole (prison mask), where the DGT has no points and OpenStreetMap has no buildings.
# Tile roofs (orange-red) are picked out of the orthophoto Tiago sent (blend/cmx_orto.png, Google, ≈ 0.93 m/px), placed with a
# similarity fitted on the stadium pitch and the GD Bairro da Misericórdia pitch (OpenStreetMap): scale 1.07 px/m, north up.
# Each roof -> minimum-area rectangle; heights are not known (2 floors assumed). -> blend/cmx_roofs.json (local metres)
import json, numpy as np, cv2
from PIL import Image
from scipy.ndimage import map_coordinates, binary_opening, binary_closing, label
O = np.asarray(Image.open('blend/cmx_orto.png').convert('RGB'), float)
S, OX, OY = 1.07, 305.0, 212.0                       # ortho px = OX + (x + 160)·S, OY − (y − 232)·S
B = json.load(open('lidar/cmx_box.json')); X0, Y0 = -24590.1, 210181.1; V = np.load('lidar/cmx_void25.npy')
g = np.arange(-280, 120, .5); GX, GY = np.meshgrid(g, np.arange(240, -160, -.5))
o = np.stack([map_coordinates(O[..., k], [OY - (GY - 232) * S, OX + (GX + 160) * S], order=1) for k in range(3)], -1)
r, gg, b = o[..., 0], o[..., 1], o[..., 2]
roof = (r > gg + 28) & (r > b + 45) & (r > 120)
inv = map_coordinates(V.astype(float), [(B['y1'] - (Y0 + GY)) / .25, (X0 + GX - B['x0']) / .25], order=0) > .5
m = binary_closing(binary_opening(roof & inv, iterations=1), iterations=2)
L, n = label(m); out = []
for k in range(1, n + 1):
    ys, xs = np.nonzero(L == k)
    if len(ys) * .25 < 25: continue
    pts = np.stack([GX[ys, xs], GY[ys, xs]], 1).astype(np.float32)
    (cx, cy), (w, h), a = cv2.minAreaRect(pts)
    if w * h > 400 or min(w, h) < 4: continue
    out.append({'c': [round(float(cx), 1), round(float(cy), 1)], 'w': round(float(w), 1), 'h': round(float(h), 1), 'a': round(float(a), 1), 'area': round(len(ys) * .25)})
json.dump(out, open('blend/cmx_roofs.json', 'w'))
print(len(out), 'roofs', [(o_['c'], o_['w'], o_['h']) for o_ in out])
