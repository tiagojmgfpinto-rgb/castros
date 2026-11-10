// Lightens a site model for the web, after the Blender export (step 5 of the pipeline in CLAUDE.md):
//  - the LiDAR terrain (node "terrain"), a regular 25-50 cm grid of ~415 000 triangles, is simplified with meshoptimizer down to
//    about TERRAIN_TRIS triangles; the error-driven simplifier keeps the vertices where the relief bends (wall banks, house
//    platforms, quarry faces) and removes them on the even slopes; the outer border is locked so the disc's skirt still fits;
//  - textures wider than MAX_TEX px (the orthophoto) are resized to MAX_TEX;
//  - the vertical error of the simplified terrain is measured at every original vertex and printed (and written to the report).
// Use: node tools/gltf/lighten.mjs <in .glb|.glb.png> <out .glb> [--tris 60000] [--tex 2048] [--report out.json]
// The structures, trees and catalogue extras are not touched. Install once with: npm ci --prefix tools/gltf
import fs from 'fs';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dequantize, prune, quantize, simplifyPrimitive, weld } from '@gltf-transform/functions';
import { MeshoptSimplifier } from 'meshoptimizer';
import sharp from 'sharp';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const [inp, out] = args.filter((a, i) => !a.startsWith('--') && !(i > 0 && args[i - 1].startsWith('--')));
const TERRAIN_TRIS = +opt('--tris', 60000), MAX_TEX = +opt('--tex', 2048), REPORT = opt('--report', null);

// .glb.png: the GLB bytes are packed in the RGB pixels after a 4-byte little-endian length (mkpng.py)
async function readBytes(f) {
  const b = fs.readFileSync(f);
  if (!f.endsWith('.png')) return new Uint8Array(b);
  const { data } = await sharp(b).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const n = data[0] | data[1] << 8 | data[2] << 16 | data[3] << 24;
  return new Uint8Array(data.buffer, data.byteOffset + 4, n);
}

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.readBinary(await readBytes(inp));
await doc.transform(dequantize());
await MeshoptSimplifier.ready;

const triCount = p => (p.getIndices() ? p.getIndices().getCount() : p.getAttribute('POSITION').getCount()) / 3;
const report = { input: inp, terrain: null, textures: [] };

for (const node of doc.getRoot().listNodes()) {
  if (node.getName() !== 'terrain' || !node.getMesh()) continue;
  for (const prim of node.getMesh().listPrimitives()) {
    const before = triCount(prim);
    const P0 = prim.getAttribute('POSITION').getArray().slice();   // original vertices (local space) for the error check
    const SC = node.getWorldMatrix()[5];                            // local -> model units (m): the quantized terrain keeps a node scale
    if (before > TERRAIN_TRIS * 1.1) {
      // the ratio sets the target; the error bound is generous so the target is what stops the simplifier
      simplifyPrimitive(prim, { simplifier: MeshoptSimplifier, ratio: TERRAIN_TRIS / before, error: 0.05, lockBorder: true });
    }
    const after = triCount(prim);
    // vertical error: height of the simplified surface under each original vertex (bucketed triangle lookup in x/z)
    const P = prim.getAttribute('POSITION').getArray(), I = prim.getIndices().getArray();
    let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
    for (let i = 0; i < P.length; i += 3) { x0 = Math.min(x0, P[i]); x1 = Math.max(x1, P[i]); z0 = Math.min(z0, P[i + 2]); z1 = Math.max(z1, P[i + 2]); }
    const G = 256, cw = (x1 - x0) / G || 1, ch = (z1 - z0) / G || 1, cells = Array.from({ length: G * G }, () => []);
    for (let t = 0; t < I.length; t += 3) {
      const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
      const gx0 = Math.max(0, Math.floor((Math.min(P[a], P[b], P[c]) - x0) / cw)), gx1 = Math.min(G - 1, Math.floor((Math.max(P[a], P[b], P[c]) - x0) / cw));
      const gz0 = Math.max(0, Math.floor((Math.min(P[a + 2], P[b + 2], P[c + 2]) - z0) / ch)), gz1 = Math.min(G - 1, Math.floor((Math.max(P[a + 2], P[b + 2], P[c + 2]) - z0) / ch));
      for (let gz = gz0; gz <= gz1; gz++) for (let gx = gx0; gx <= gx1; gx++) cells[gz * G + gx].push(t);
    }
    const errs = [];
    for (let i = 0; i < P0.length; i += 3) {
      const x = P0[i], z = P0[i + 2], gx = Math.min(G - 1, Math.floor((x - x0) / cw)), gz = Math.min(G - 1, Math.floor((z - z0) / ch));
      if (gx < 0 || gz < 0) continue;
      for (const t of cells[gz * G + gx]) {
        const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
        const d = (P[b + 2] - P[c + 2]) * (P[a] - P[c]) + (P[c] - P[b]) * (P[a + 2] - P[c + 2]);
        if (!d) continue;
        const l1 = ((P[b + 2] - P[c + 2]) * (x - P[c]) + (P[c] - P[b]) * (z - P[c + 2])) / d;
        const l2 = ((P[c + 2] - P[a + 2]) * (x - P[c]) + (P[a] - P[c]) * (z - P[c + 2])) / d, l3 = 1 - l1 - l2;
        if (l1 < -1e-6 || l2 < -1e-6 || l3 < -1e-6) continue;
        errs.push(SC * Math.abs(l1 * P[a + 1] + l2 * P[b + 1] + l3 * P[c + 1] - P0[i + 1])); break;
      }
    }
    errs.sort((a, b) => a - b);
    const q = k => +(errs[Math.min(errs.length - 1, Math.floor(errs.length * k))] * 100).toFixed(1);
    report.terrain = { before, after, checked: errs.length, of: P0.length / 3, err_cm: { median: q(.5), p95: q(.95), p99: q(.99), max: q(1) } };
    console.log(`terrain: ${before} -> ${after} triangles; vertical error (cm) median ${q(.5)}, p95 ${q(.95)}, p99 ${q(.99)}, max ${q(1)}`);
  }
}

for (const tex of doc.getRoot().listTextures()) {
  const img = tex.getImage(); if (!img) continue;
  const meta = await sharp(Buffer.from(img)).metadata();
  if (Math.max(meta.width, meta.height) <= MAX_TEX) continue;
  const jpg = tex.getMimeType() === 'image/jpeg';
  const buf = await sharp(Buffer.from(img)).resize(MAX_TEX, MAX_TEX, { fit: 'inside' })[jpg ? 'jpeg' : 'png'](jpg ? { quality: 84, mozjpeg: true } : {}).toBuffer();
  report.textures.push({ name: tex.getName(), from: `${meta.width}x${meta.height}`, to: MAX_TEX, kb: [Math.round(img.byteLength / 1024), Math.round(buf.length / 1024)] });
  console.log(`texture ${tex.getName() || '?'}: ${meta.width}x${meta.height} -> ${MAX_TEX} (${Math.round(img.byteLength / 1024)} -> ${Math.round(buf.length / 1024)} KB)`);
  tex.setImage(new Uint8Array(buf));
}

// same settings as mkparts.sh
await doc.transform(weld({ cleanup: false }), quantize({ quantizePosition: 14, quantizeNormal: 8, quantizeTexcoord: 12, cleanup: false }),
  prune({ keepLeaves: true, keepAttributes: true, keepExtras: true }));   // keepLeaves: the empty LBL-* label nodes must stay
fs.writeFileSync(out, await io.writeBinary(doc));
if (REPORT) fs.writeFileSync(REPORT, JSON.stringify(report, null, 1));
console.log('written', out, fs.statSync(out).size);
