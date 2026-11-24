"""Árvores das maquetas segundo as regras do Tiago (prompt «metro a metro», secção 5):
- nenhuma árvore a menos de 5 m das estruturas arqueológicas, nem com a copa por cima delas;
- dentro das muralhas, só 10-15 % das árvores (densidade ≤ 15 % da da coroa de 40 m à volta do recinto);
- arbustos a pelo menos 2 m das estruturas; tojo e giesta verde-escuros, com flor amarela só em 12 % (perito, São Paio P2-11:
  as bolas amarelas saturadas eram um terço dos arbustos).
Lê app/dio/<id>.json (árvores) e as estruturas A-/AB- do GLB (app/dio/<id>.glb.png) e reescreve a lista `trees`.
Correr depois de refazer uma maqueta no Blender (o Blender volta a pôr todas as árvores do LiDAR).
Uso: /opt/bvenv/bin/python tools/arvores_regras.py <id> [...]   (precisa de node + tools/gltf/node_modules)
"""
import json, subprocess, sys, os, tempfile
import numpy as np
from scipy.spatial import cKDTree, ConvexHull
from matplotlib.path import Path

# muralhas que fecham o recinto habitado de cada sítio (o resto das muralhas fica com a floresta à volta)
RECINTO = {
    'guimaraes-citania-de-briteiros': ['M1', 'M2'],
    'guimaraes-castro-de-sabroso': ['M1', 'M2', 'M3', 'M4'],
    'guimaraes-castro-de-sao-miguel-o-anjo': ['M2'],
    'braga-castro-de-santa-marta-das-corticas': ['M1'],
    'pacos-de-ferreira-citania-de-sanfins': [],
}
# estruturas modernas ou sem forma no terreno: não contam para a distância
MODERNO = ('moderno', 'moderna', 'Infraestrutura', 'Equipamento', 'Capela', 'Monumento', 'Marco', 'Cruzeiro', 'Relevo',
           'Pedreira', 'Escavação', 'Igreja', 'Palácio', 'Ruína', 'Afloramento', 'Indeterminada')
COPA = {'oak': .83, 'cork': .86, 'euc': .42, 'euc2': .50, 'chest': .94, 'chest2': .75, 'oak2': 1.02, 'oak3': .52, 'cork2': .80}
DUMP = r"""
const {NodeIO}=require(process.argv[2]+'/@gltf-transform/core');const {ALL_EXTENSIONS}=require(process.argv[2]+'/@gltf-transform/extensions');
(async()=>{const d=await new NodeIO().registerExtensions(ALL_EXTENSIONS).read(process.argv[3]);const out={};
for(const n of d.getRoot().listNodes()){const nm=n.getName();if(!/^(A|AB)-/.test(nm)||!n.getMesh())continue;const sid=nm.replace(/^(A|AB)-/,'').replace(/\.\d+$/,'');
 const M=n.getWorldMatrix(),pts=out[sid]=out[sid]||[];
 for(const p of n.getMesh().listPrimitives()){const a=p.getAttribute('POSITION'),e=[0,0,0],N=a.getCount(),st=Math.max(1,Math.floor(N/3000));
  for(let i=0;i<N;i+=st){a.getElement(i,e);pts.push([M[0]*e[0]+M[4]*e[1]+M[8]*e[2]+M[12],M[2]*e[0]+M[6]*e[1]+M[10]*e[2]+M[14]])}}}
process.stdout.write(JSON.stringify(out))})()
"""

def structures(sid):
    tmp = tempfile.mkdtemp()
    subprocess.run([sys.executable, 'tools/unpng.py', f'app/dio/{sid}.glb.png', f'{tmp}/m.glb'], check=True, capture_output=True)
    open(f'{tmp}/d.cjs', 'w').write(DUMP)
    out = subprocess.run(['node', f'{tmp}/d.cjs', os.path.abspath('tools/gltf/node_modules'), f'{tmp}/m.glb'], check=True, capture_output=True, text=True).stdout
    return json.loads(out)

def run(sid):
    d = json.load(open(f'app/dio/{sid}.json'))
    cat = {c['id']: c for c in d['cat']}
    st = structures(sid)
    arch, rec = [], []
    for k, pts in st.items():
        c = cat.get(k) or cat.get(k.rstrip('R'))
        if not c or any(m in c['kind'] for m in MODERNO) and c['kind'] != 'Reconstrução moderna':
            continue
        arch += pts
        if k in RECINTO.get(sid, []):
            rec += pts
    A = np.array(arch)
    T = d['types']
    tr = d['trees']
    xz = np.array([[t[0], -t[1]] for t in tr])
    dist = cKDTree(A).query(xz)[0] if len(A) else np.full(len(tr), np.inf)
    kind = [T[t[4]] for t in tr]
    keep = np.ones(len(tr), bool)
    big = np.array([k in COPA for k in kind])
    copa = np.array([COPA.get(k, 0) / 2 * t[3] * ((t[7] if len(t) > 7 else 0) or 1) for k, t in zip(kind, tr)])
    near = big & (dist < np.maximum(5, copa))
    keep &= ~near
    shrub = np.array([k == 'shrub' for k in kind])
    keep &= ~(shrub & (dist < 2))
    thin = 0
    if rec:
        R = np.array(rec)
        h = ConvexHull(R)
        P = Path(R[h.vertices])
        inside = P.contains_points(xz)
        # coroa de 40 m à volta do recinto
        poly = R[h.vertices]
        c = poly.mean(0)
        ring = Path(c + (poly - c) * (1 + 40 / np.sqrt(h.volume / np.pi))).contains_points(xz) & ~inside
        ring_area = h.volume * ((1 + 40 / np.sqrt(h.volume / np.pi)) ** 2 - 1)
        dens_out = (big & ring).sum() / ring_area
        cap = int(round(.15 * dens_out * h.volume))
        idx = np.where(big & inside & keep)[0]
        if len(idx) > cap:
            # ficam as mais afastadas das estruturas (zonas por escavar), as outras saem
            order = idx[np.argsort(-dist[idx])]
            keep[order[cap:]] = False
            thin = len(idx) - cap
        print(f'{sid}: recinto {h.volume / 1e4:.2f} ha, densidade fora {dens_out * 1e4:.0f}/ha, no recinto ficam {min(cap, len(idx))} de {len(idx)}')
    print(f'{sid}: árvores {big.sum()} → {(big & keep).sum()} (perto das estruturas {near.sum()}, rareadas no recinto {thin}); '
          f'arbustos {shrub.sum()} → {(shrub & keep).sum()}')
    d['trees'] = [t for t, k in zip(tr, keep) if k]
    si = T.index('shrub') if 'shrub' in T else -1
    if si >= 0:
        d['pal']['shrub'] = [[110, 122, 54], [96, 110, 48], [78, 90, 42], [176, 158, 64]]
        j = 0
        for t in d['trees']:
            if t[4] == si:
                t[5] = 3 if j % 8 == 5 else j % 3
                j += 1
    json.dump(d, open(f'app/dio/{sid}.json', 'w'))

if __name__ == '__main__':
    for s in sys.argv[1:]:
        run(s)
