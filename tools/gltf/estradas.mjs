import { execSync } from 'child_process';
// Estradas pavimentadas no estado atual, com a textura de asfalto de Briteiros (blend/road_access.jpg: 12 m ao longo da via,
// a largura de um lado ao outro), sem refazer o Blender: as vias vêm de tools/gltf/estradas/<id>.json (tools/estradas_osm.py,
// OpenStreetMap) e assentam no terreno da maqueta (0,12 m acima do triângulo do terreno em cada vértice).
// Junta a peça A-RD ao GLB e a entrada «Estrada (atual)» ao catálogo app/dio/<id>.json; reescreve o .glb.png e o .drc.glb.png.
// Pedido do Tiago (24 nov. 2026): «colocar a textura de estrada nos sítios em que há estrada».
// Uso: node tools/gltf/estradas.mjs <id>
import fs from 'fs';
import { execFileSync } from 'child_process';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { prune } from '@gltf-transform/functions';

const id = process.argv[2], F = `app/dio/${id}`, tmp = `/tmp/_estradas_${id}`;
const V = JSON.parse(fs.readFileSync(`tools/gltf/estradas/${id}.json`, 'utf8')).vias;
const meta = JSON.parse(fs.readFileSync(`${F}.json`, 'utf8'));
execFileSync('python3', ['tools/unpng.py', `${F}.glb.png`, `${tmp}.glb`]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(`${tmp}.glb`), root = doc.getRoot();
// sem duplicar: tira uma A-RD anterior feita por este script
for (const n of root.listNodes()) if (n.getName() === 'A-RD' && n.getExtras().estradas) n.dispose();

// triângulos do terreno em coordenadas do mundo, numa grelha de 2 m
const tris = [], G = new Map(), C = 2, key = (i, j) => i * 100000 + j;
for (const n of root.listNodes()) {
  if (n.getName() !== 'terrain' || !n.getMesh()) continue;
  const M = n.getWorldMatrix();
  for (const p of n.getMesh().listPrimitives()) {
    const a = p.getAttribute('POSITION'), I = p.getIndices(), e = [0, 0, 0], W = [];
    for (let i = 0; i < a.getCount(); i++) { a.getElement(i, e); W.push([0, 1, 2].map(j => M[j] * e[0] + M[4 + j] * e[1] + M[8 + j] * e[2] + M[12 + j])); }
    const nt = I ? I.getCount() / 3 : a.getCount() / 3;
    for (let t = 0; t < nt; t++) {
      const v = [0, 1, 2].map(k => W[I ? I.getScalar(t * 3 + k) : t * 3 + k]); const ti = tris.push(v) - 1;
      const x0 = Math.floor(Math.min(...v.map(q => q[0])) / C), x1 = Math.floor(Math.max(...v.map(q => q[0])) / C);
      const z0 = Math.floor(Math.min(...v.map(q => q[2])) / C), z1 = Math.floor(Math.max(...v.map(q => q[2])) / C);
      for (let i = x0; i <= x1; i++) for (let j = z0; j <= z1; j++) { const k = key(i, j); if (!G.has(k)) G.set(k, []); G.get(k).push(ti); }
    }
  }
}
const hAt = (x, z) => {
  for (const ti of G.get(key(Math.floor(x / C), Math.floor(z / C))) || []) {
    const [a, b, c] = tris[ti], d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2]);
    if (Math.abs(d) < 1e-9) continue;
    const l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d, l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d, l3 = 1 - l1 - l2;
    if (l1 >= -1e-6 && l2 >= -1e-6 && l3 >= -1e-6) return l1 * a[1] + l2 * b[1] + l3 * c[1];
  }
  return null;
};

// faixas: pontos de 1,5 em 1,5 m; só os troços dentro do disco (com terreno)
const P = [], N = [], UV = [], IX = [];
let comp = 0;
for (const v of V) {
  const d = [];
  for (let i = 1; i < v.pts.length; i++) {
    const [ax, az] = v.pts[i - 1], [bx, bz] = v.pts[i], L = Math.hypot(bx - ax, bz - az), n = Math.max(1, Math.ceil(L / 1.5));
    for (let k = i === 1 ? 0 : 1; k <= n; k++) d.push([ax + (bx - ax) * k / n, az + (bz - az) * k / n]);
  }
  const hw = v.largura / 2; let run = null, s = 0;
  const flush = () => { run = null; };
  for (let i = 0; i < d.length; i++) {
    const p = d[i], q = d[Math.min(i + 1, d.length - 1)], o = d[Math.max(i - 1, 0)];
    let tx = q[0] - o[0], tz = q[1] - o[1]; const tl = Math.hypot(tx, tz) || 1; tx /= tl; tz /= tl;
    const L = [p[0] - tz * hw, p[1] + tx * hw], Rr = [p[0] + tz * hw, p[1] - tx * hw];
    const hl = hAt(...L), hr = hAt(...Rr), hc = hAt(...p);
    if (i > 0) s += Math.hypot(p[0] - d[i - 1][0], p[1] - d[i - 1][1]);
    if (hl === null || hr === null || hc === null || Math.hypot(...L) > meta.R - .5 || Math.hypot(...Rr) > meta.R - .5) { flush(); continue; }
    const base = P.length / 3;
    P.push(L[0], Math.max(hl, hc - .3) + .12, L[1], Rr[0], Math.max(hr, hc - .3) + .12, Rr[1]);
    N.push(0, 1, 0, 0, 1, 0); UV.push(s / 12, 1, s / 12, 0);
    if (run !== null) { IX.push(run, base, run + 1, run + 1, base, base + 1); comp += Math.hypot(p[0] - d[i - 1][0], p[1] - d[i - 1][1]); }   // normal para cima
    run = base;
  }
}
if (!IX.length) { console.log(id, 'sem estradas dentro do disco'); process.exit(0); }
const buf = root.listBuffers()[0];
const acc = (arr, type, T) => doc.createAccessor().setArray(new T(arr)).setType(type).setBuffer(buf);
const img = fs.readFileSync('blend/road_access.jpg');
const tex = doc.createTexture('asfalto').setImage(img).setMimeType('image/jpeg');
const mat = doc.createMaterial('asfalto').setBaseColorTexture(tex).setRoughnessFactor(.8).setMetallicFactor(0);
const prim = doc.createPrimitive().setMaterial(mat).setIndices(acc(IX, 'SCALAR', Uint32Array))
  .setAttribute('POSITION', acc(P, 'VEC3', Float32Array)).setAttribute('NORMAL', acc(N, 'VEC3', Float32Array)).setAttribute('TEXCOORD_0', acc(UV, 'VEC2', Float32Array));
const node = doc.createNode('A-RD').setMesh(doc.createMesh('A-RD').addPrimitive(prim)).setExtras({ sid: 'RD', mode: 'A', ev: 'conf', estradas: true });
root.getDefaultScene().addChild(node);
await doc.transform(prune({ keepLeaves: true, keepAttributes: true, keepExtras: true }));
await io.write(`${tmp}.glb`, doc);
execFileSync('python3', ['mkpng.py', `${tmp}.glb`, `${F}.glb.png`], { stdio: 'inherit' });
execFileSync('node', ['tools/gltf/draco.mjs', `${tmp}.glb`, `${tmp}.d.glb`], { stdio: 'inherit' });
execFileSync('python3', ['mkpng.py', `${tmp}.d.glb`, `${F}.drc.glb.png`], { stdio: 'inherit' });
fs.rmSync(`${tmp}.glb`); fs.rmSync(`${tmp}.d.glb`);
// catálogo
const larg = [...new Set(V.map(v => v.largura))].sort((a, b) => a - b).map(x => String(x).replace('.', ',')).join(' a ');
const nomes = V.map(v => v.nome).filter(Boolean);
const item = { id: 'RD', name: 'Estrada (atual)', kind: 'Infraestrutura moderna', phase: 'atual', ev: 'conf', evB: 'conf',
  dims: `largura ≈ ${larg} m · ${Math.round(comp)} m dentro da maqueta`,
  note: `Estradas pavimentadas do OpenStreetMap${nomes.length ? ' (' + [...new Set(nomes)].join(', ') + ')' : ''}, assentes no terreno do LiDAR com textura de asfalto. Só no estado atual. A largura é a típica da categoria da via, não medida.`,
  src: ['osm'] };
// árvores com o tronco na faixa da estrada (ou a menos de 1,5 m da berma) saem
const segD = (x, z, [ax, az], [bx, bz]) => { const dx = bx - ax, dz = bz - az, l = dx * dx + dz * dz || 1, t = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / l)); return Math.hypot(x - ax - t * dx, z - az - t * dz); };
const nt0 = meta.trees.length;
meta.trees = meta.trees.filter(t => !V.some(v => v.pts.some((q, i) => i > 0 && segD(t[0], -t[1], v.pts[i - 1], q) < v.largura / 2 + 1.5)));
console.log(id, `árvores na estrada: ${nt0 - meta.trees.length}`);
meta.cat = meta.cat.filter(c => c.id !== 'RD').concat([item]);
if (!meta.sources.osm) meta.sources.osm = 'OpenStreetMap (contribuidores), ODbL.';
fs.writeFileSync(`${F}.json`, JSON.stringify(meta));
execSync(`python3 -c "import json,sys;p=sys.argv[1];json.dump(json.load(open(p)),open(p,'w'))" ${F}.json`);
console.log(id, `estradas: ${V.length} vias, ${Math.round(comp)} m, ${IX.length / 3} triângulos`);
