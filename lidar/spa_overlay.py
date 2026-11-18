# Castro de São Paio: control image of the structures of the model over the LiDAR hillshade (left) and the orthophoto
# (right), in the box-local frame of lidar/spa_box.json (230 m, 0.25 m cells). Usage: python lidar/spa_overlay.py <png>
import json, math, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
B = json.load(open('lidar/spa_box.json')); D = np.load('lidar/spa_dtm25.npy').astype(float); cs = B['cs']; n = B['n']
gy, gx = np.gradient(D, cs); az, alt = math.radians(315), math.radians(40)
sl = np.arctan(np.hypot(gx, gy)); asp = np.arctan2(-gx, gy)
hs = np.clip(np.sin(alt) * np.cos(sl) + np.cos(alt) * np.sin(sl) * np.cos(az - asp), 0, 1)
H = Image.fromarray((hs * 255).astype(np.uint8)).convert('RGB')
O19 = np.asarray(Image.open('lidar/spa/orto_z19.png').convert('RGB').resize((n, n)))   # z19 everywhere, z20 where it exists
O20 = np.asarray(Image.open('lidar/spa/orto_z20.png').convert('RGB').resize((n, n)))
O = Image.fromarray(np.where(O20.sum(2, keepdims=True) > 30, O20, O19))
LN = json.load(open('blend/spa_lines.json'))
px = lambda p: ((p[0] + n * cs / 2) / cs, (n * cs / 2 - p[1]) / cs)
E1 = [(-29.75, -31.7), (-20.1, -30.75), (-19.6, -34.2), (-29.75, -35.1)]
E2 = [(-34.2, 4.6), (-27.6, 4.75), (-26.7, 1.5), (-34.2, .25)]
C1 = [(-30.6 + 2.6 * math.cos(a), 26.6 + 2.6 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 33)]
def rect(c, L, W, az):   # chapel body from the LiDAR fit (azimuth of the ridge from north)
    a = math.radians(az); u = (math.sin(a), math.cos(a)); v = (u[1], -u[0])
    return [(c[0] + su * L / 2 * u[0] + sv * W / 2 * v[0], c[1] + su * L / 2 * u[1] + sv * W / 2 * v[1]) for su, sv in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
CH = rect((13.9, -25.8), 10.8, 9.1, 63)
def draw(im):
    d = ImageDraw.Draw(im)
    d.line([px(p) for p in LN['T1']['pts']], fill=(230, 40, 30), width=4)
    for poly, col in ((E1, (255, 200, 0)), (E2, (255, 200, 0)), (C1, (0, 220, 255)), (CH, (60, 255, 90))):
        q = [px(p) for p in poly]; d.line(q + q[:1], fill=col, width=3)
    d.line([px((-100, -105)), px((-80, -105))], fill=(255, 255, 255), width=5); d.text(px((-100, -101)), '20 m', fill=(255, 255, 255))
    return im
c = Image.new('RGB', (2 * n + 20, n), 'white'); c.paste(draw(H), (0, 0)); c.paste(draw(O), (n + 20, 0))
c.save(sys.argv[1]); print('written', sys.argv[1])
