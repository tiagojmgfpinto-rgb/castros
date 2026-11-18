// Draco compression of a site model (step 5 of the pipeline in CLAUDE.md), after lighten.mjs: every mesh gets
// KHR_draco_mesh_compression (edgebreaker; the attributes are already quantized 14/8/12 by lighten.mjs, so Draco keeps those
// integers as they are). No weld or prune here: the empty LBL-* nodes (labels) and the extras must survive; the script checks
// that the node names, mesh count and number of (non-degenerate) triangles are the same before and after.
// Use: node tools/gltf/draco.mjs <in .glb> <out .glb>      (the viewer decodes it with app/draco/, see dioDraco in app/src.html)
import fs from 'fs';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, KHRDracoMeshCompression } from '@gltf-transform/extensions';
import draco3d from 'draco3dgltf';

const [inp, out] = process.argv.slice(2);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'draco3d.encoder': await draco3d.createEncoderModule(), 'draco3d.decoder': await draco3d.createDecoderModule() });
// triangles that are not degenerate (Draco drops those with two equal corners, which draw nothing)
const tris = p => { const P = p.getAttribute('POSITION').getArray(), I = p.getIndices() ? p.getIndices().getArray() : null, n = I ? I.length : P.length / 3;
  const k = i => { const j = (I ? I[i] : i) * 3; return P[j] + ',' + P[j + 1] + ',' + P[j + 2]; };
  let c = 0; for (let i = 0; i < n; i += 3) { const a = k(i), b = k(i + 1), d = k(i + 2); if (a !== b && b !== d && a !== d) c++; } return c; };
const sig = d => { const r = d.getRoot(), t = r.listMeshes().flatMap(m => m.listPrimitives()).reduce((s, p) => s + tris(p), 0);
  return JSON.stringify([r.listNodes().map(n => n.getName()), r.listMeshes().length, t]); };
const doc = await io.read(inp), before = sig(doc);
doc.createExtension(KHRDracoMeshCompression).setRequired(true).setEncoderOptions({
  method: KHRDracoMeshCompression.EncoderMethod.EDGEBREAKER, encodeSpeed: 5, decodeSpeed: 5,
  quantizationBits: { POSITION: 14, NORMAL: 8, COLOR: 8, TEX_COORD: 12, GENERIC: 12 } });
const bin = await io.writeBinary(doc);
const after = sig(await io.readBinary(bin));   // decode again: same nodes, meshes and triangles
if (before !== after) { console.error(a[0].length, b[0].length, a[1], b[1], a[2], b[2], a[0].filter(n => !b[0].includes(n)).slice(0, 10));console.error('draco: the model changed in the round trip'); process.exit(1); }
fs.writeFileSync(out, bin);
console.log(`draco: ${fs.statSync(inp).size} -> ${bin.length} bytes`);
