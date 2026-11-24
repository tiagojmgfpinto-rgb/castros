// Correções de material das maquetas segundo as regras do Tiago (relatório do perito de São Paio, nov. 2026), sem refazer o Blender:
// - peças do estado atual sem nada à vista (muralhas soterradas de S. Miguel-o-Anjo e Santa Marta, terceira muralha de Briteiros,
//   basílica e palácio de posição aproximada em Santa Marta): saem do estado atual; o talude do terreno LiDAR continua lá;
// - Sabroso: os afloramentos de granito (AB-R) saíam quase brancos com o sol; granito cinzento (#958f86 em sRGB).
// Uso: node tools/gltf/regras.mjs <id>   (lê e reescreve app/dio/<id>.glb.png e .drc.glb.png)
import fs from 'fs';
import { execFileSync } from 'child_process';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { prune } from '@gltf-transform/functions';

// tirar: peças do estado atual (A-*) que não se veem no terreno; ficam só na interpretação (B) e na reconstituição (C).
// Pedido do Tiago (24 nov. 2026): «retirar as pseudo-reconstruções», como a muralha verde de Santa Marta.
const R = {
  'guimaraes-castro-de-sao-miguel-o-anjo': { tirar: ['A-M1', 'A-M2', 'A-M3'],
    lbl: { 'Linha interior': 'M1', 'Muralha intermédia': 'M2', 'Linha exterior': 'M3' } },
  'braga-castro-de-santa-marta-das-corticas': { tirar: ['A-M1', 'A-M2', 'A-BA', 'A-PA', 'A-PC'],
    lbl: { 'Primeira muralha': 'M1', 'Segunda muralha': 'M2', 'Basílica paleocristã': 'BA', 'Edifício palatino': 'PA' } },
  'guimaraes-citania-de-briteiros': { tirar: ['A-M3', 'A-M3E'] },
  'guimaraes-castro-de-sabroso': { cor: { granite: [0.30, 0.285, 0.26, 1] } },
};
const id = process.argv[2], cfg = R[id];
if (!cfg) { console.error('sem regras para', id); process.exit(1); }
const F = `app/dio/${id}`, tmp = `/tmp/_regras_${id}`;
execFileSync('python3', ['tools/unpng.py', `${F}.glb.png`, `${tmp}.glb`]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(`${tmp}.glb`);
const root = doc.getRoot();
let n = 0;
// lbl: rótulo → sid; o visor esconde o rótulo quando a estrutura não está desenhada na camada atual
if (cfg.lbl) for (const node of root.listNodes()) {
  const nm = node.getName().replace(/^LBL-/, '');
  if (nm === node.getName()) continue;
  for (const k in cfg.lbl) if (nm.startsWith(k)) { node.setExtras({ ...node.getExtras(), sid: cfg.lbl[k] }); n++; }
}
if (cfg.tirar) {
  for (const node of root.listNodes()) {
    if (!cfg.tirar.includes(node.getName().replace(/\.\d+$/, ''))) continue;
    node.dispose(); n++;
  }
  await doc.transform(prune({ keepLeaves: true, keepAttributes: true, keepExtras: true }));
}
if (cfg.cor) for (const m of root.listMaterials()) if (cfg.cor[m.getName()]) { m.setBaseColorFactor(cfg.cor[m.getName()]); n++; }
await io.write(`${tmp}.glb`, doc);
console.log(`${id}: ${n} alterações`);
execFileSync('python3', ['mkpng.py', `${tmp}.glb`, `${F}.glb.png`], { stdio: 'inherit' });
execFileSync('node', ['tools/gltf/draco.mjs', `${tmp}.glb`, `${tmp}.d.glb`], { stdio: 'inherit' });
execFileSync('python3', ['mkpng.py', `${tmp}.d.glb`, `${F}.drc.glb.png`], { stdio: 'inherit' });
fs.rmSync(`${tmp}.glb`); fs.rmSync(`${tmp}.d.glb`);
