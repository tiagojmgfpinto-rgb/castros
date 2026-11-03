# Castro Máximo: OpenStreetMap features around the site, read from osm/braga.pbf -> blend/cmx_osm.json
# (local metres from the site point PT-TM06 (-24590.1, 210181.1): x east, y north). Usage: /opt/bvenv/bin/python lidar/cmx_osm.py
import json, osmium
from pyproj import Transformer
T = Transformer.from_crs(4326, 3763, always_xy=True)
X0, Y0, CX, CY, R = -24590.1, 210181.1, -120.0, 120.0, 280.0
KEEP = ('highway', 'building', 'leisure', 'landuse', 'natural', 'amenity', 'barrier', 'historic', 'man_made')
class H(osmium.SimpleHandler):
    def __init__(s): super().__init__(); s.ways = []; s.nodes = []
    def way(s, w):
        tg = {k: v for k, v in w.tags}
        if not any(k in tg for k in KEEP): return
        try: p = [T.transform(n.lon, n.lat) for n in w.nodes]
        except Exception: return
        p = [(round(x - X0, 1), round(y - Y0, 1)) for x, y in p]
        if min((x - CX) ** 2 + (y - CY) ** 2 for x, y in p) > R * R: return
        s.ways.append({'id': w.id, 'tags': tg, 'pts': p})
    def node(s, n):
        tg = {k: v for k, v in n.tags}
        if not any(k in tg for k in KEEP): return
        x, y = T.transform(n.location.lon, n.location.lat); x -= X0; y -= Y0
        if (x - CX) ** 2 + (y - CY) ** 2 < R * R: s.nodes.append({'id': n.id, 'tags': tg, 'pts': [(round(x, 1), round(y, 1))]})
h = H(); h.apply_file('osm/braga.pbf', locations=True)
json.dump({'ways': h.ways, 'nodes': h.nodes}, open('blend/cmx_osm.json', 'w'), ensure_ascii=False)
print(len(h.ways), 'ways', len(h.nodes), 'nodes')
