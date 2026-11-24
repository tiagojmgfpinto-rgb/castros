"""Estradas pavimentadas do OpenStreetMap à volta de um sítio, em metros do referencial da maqueta (x = este, z = sul, a partir do
centro do disco), para o tools/gltf/estradas.mjs as pôr com textura de asfalto no estado atual.
Só entram as vias com piso pavimentado: highway primary…residential/unclassified/service sem surface não pavimentado
(em Portugal estas vias são asfaltadas ou em cubo); caminhos, trilhos e veredas ficam como estão (pintados no chão).
Uso: /opt/bvenv/bin/python tools/estradas_osm.py <id> [ficheiro .osm.json do Overpass]   → tools/gltf/estradas/<id>.json
"""
import json, sys, math
from pyproj import Transformer

LARG = {'primary': 7.5, 'secondary': 7.0, 'tertiary': 6.0, 'unclassified': 5.0, 'residential': 5.0, 'service': 3.5}
NAOPAV = {'unpaved', 'ground', 'dirt', 'gravel', 'fine_gravel', 'grass', 'sand', 'earth', 'compacted', 'mud', 'pebblestone'}
T = Transformer.from_crs('EPSG:4326', 'EPSG:3763', always_xy=True)

def run(sid, overpass=None):
    site = next(s for s in json.load(open('data.json'))['sites'] if s['id'] == sid)
    la, lo = site['coords'][:2]
    meta = json.load(open(f'app/dio/{sid}.json'))
    R, cx, cz = meta['R'], meta['cx'], meta['cz']
    x0, y0 = T.transform(lo, la)
    ways = []
    if overpass:
        J = json.load(open(overpass))
        nodes = {e['id']: (e['lat'], e['lon']) for e in J['elements'] if e['type'] == 'node'}
        for e in J['elements']:
            if e['type'] == 'way' and 'highway' in e.get('tags', {}):
                ways.append((e['id'], e['tags'], [nodes[n] for n in e['nodes'] if n in nodes]))
    else:
        import osmium
        r = 0.006
        class H(osmium.SimpleHandler):
            def way(self, w):
                if 'highway' not in w.tags: return
                try: pts = [(n.lat, n.lon) for n in w.nodes]
                except Exception: return
                if any(abs(a - la) < r and abs(b - lo) < r * 1.35 for a, b in pts):
                    ways.append((w.id, dict(w.tags), pts))
        H().apply_file('osm/braga.pbf', locations=True)
    out = []
    for wid, tags, pts in ways:
        h = tags.get('highway')
        if h not in LARG or tags.get('surface') in NAOPAV or tags.get('tracktype'):
            continue
        if h == 'service' and tags.get('service') in ('parking_aisle', 'driveway'):
            continue
        P = []
        for a, b in pts:
            x, y = T.transform(b, a)
            P.append([round(x - x0 - cx, 2), round(-(y - y0) - cz, 2)])   # x este, z sul, a partir do centro do disco
        if not any(math.hypot(*p) < R for p in P):
            continue
        w = float(tags['width']) if tags.get('width', '').replace('.', '', 1).isdigit() else LARG[h]
        out.append({'osm': wid, 'highway': h, 'nome': tags.get('name', ''), 'surface': tags.get('surface', ''), 'largura': w, 'pts': P})
    json.dump({'fonte': 'OpenStreetMap (contribuidores), ODbL; extrato de 2026', 'vias': out},
              open(f'tools/gltf/estradas/{sid}.json', 'w'), ensure_ascii=False, indent=0)
    print(sid, len(out), 'vias:', ', '.join(f"{o['highway']} {o['nome'] or o['osm']}" for o in out))

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
