# Viewpoints of the comparison photographs of the Castro de São Paio, in the coordinates of the app viewer (metres,
# x = east, y = up, z = south, origin at the disc centre). Ground heights from the LiDAR model (lidar/spa_dtm25.npy).
# Positions are estimated from the photographs (structures and horizon in view), not measured: they are approximate.
import json, numpy as np
from scipy.ndimage import map_coordinates
B = json.load(open('lidar/spa_box.json')); D = np.load('lidar/spa_dtm25.npy')
CX, CY = -15.0, -12.0
def h(x, y):   # box-local metres -> ground height
    r = (B['n'] * B['cs'] / 2 - y) / B['cs'] - .5; c = (x + B['n'] * B['cs'] / 2) / B['cs'] - .5
    return float(map_coordinates(D, [[r], [c]], order=1)[0])
H0 = h(CX, CY)
def v(x, y, up): return [round(x - CX, 2), round(h(x, y) - H0 + up, 2), round(-(y - CY), 2)]
V = {
 # Tiago, 2025: the excavated area E2 with the logs, looking west to the sea
 'ph0': {'cam': v(-23.5, 4.8, 1.6), 'tgt': v(-45.0, 1.0, 0.0), 'fov': 62},
 # Tiago, 2025: the panel by E1 with the chapel behind, looking east
 'ph2': {'cam': v(-36.0, -35.5, 1.5), 'tgt': v(13.9, -25.8, 2.5), 'fov': 55},
}
print(json.dumps({'h0': H0, **V}))
json.dump(V, open('lidar/spa/views.json', 'w'), indent=1)
