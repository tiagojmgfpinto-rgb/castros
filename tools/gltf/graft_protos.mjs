// Copies tree prototypes (PROTO-<kind>-* nodes) from one site model into another and drops others, so a model can take
// the vegetation of another without a new Blender run. Materials are matched by name to the target's when they exist.
// Use: node tools/gltf/graft_protos.mjs <target.glb> <source.glb> <out.glb> --add euc,euc2,chest --drop pine
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {copyToDocument, prune} from '@gltf-transform/functions';
const [tgt, src, out] = process.argv.slice(2, 5), arg = k => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1].split(',') : [] };
const add = arg('--add'), drop = arg('--drop'), kind = n => n.getName().split('-')[1];
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const T = await io.read(tgt), S = await io.read(src), scene = T.getRoot().listScenes()[0];
for (const n of T.getRoot().listNodes()) if (n.getName().startsWith('PROTO-') && drop.includes(kind(n))) { scene.removeChild(n); n.dispose() }
const pick = S.getRoot().listNodes().filter(n => n.getName().startsWith('PROTO-') && add.includes(kind(n)));
const byName = new Map(T.getRoot().listMaterials().map(m => [m.getName(), m])), map = copyToDocument(T, S, pick);
const copiedMats = new Set();
for (const n of pick) { const c = map.get(n); scene.addChild(c);
  for (const p of c.getMesh().listPrimitives()) { const m = p.getMaterial(), keep = [...byName.entries()].find(([k, v]) => k === m.getName() && v !== m);
    if (keep) { p.setMaterial(keep[1]); copiedMats.add(m) } } }
copiedMats.forEach(m => { if (!m.listParents().some(p => p.propertyType === 'Primitive')) m.dispose() });
const buf = T.getRoot().listBuffers()[0];   // one buffer, as GLB needs
T.getRoot().listAccessors().forEach(a => a.setBuffer(buf)); T.getRoot().listBuffers().slice(1).forEach(b => b.dispose());
await T.transform(prune({keepLeaves: true, keepAttributes: true, keepExtras: true}));
await io.write(out, T);
console.log('added', pick.map(n => n.getName()).join(' '), '| prototypes now', T.getRoot().listNodes().filter(n => n.getName().startsWith('PROTO-')).length);
