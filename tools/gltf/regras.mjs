// Correções de material das maquetas segundo as regras do Tiago (relatório do perito de São Paio, nov. 2026), sem refazer o Blender:
// - muralhas soterradas (S. Miguel-o-Anjo M1–M3, Santa Marta M1–M2): no estado atual (A-*) deixam de ser um cordão de pedra cinzenta
//   e passam a talude coberto de mato (a mesma textura, tingida de verde-azeitona), porque a pedra não se vê no terreno;
// - Sabroso: os afloramentos de granito (AB-R) saíam quase brancos com o sol; granito cinzento (#958f86 em sRGB).
// Uso: node tools/gltf/regras.mjs <id>   (lê e reescreve app/dio/<id>.glb.png e .drc.glb.png)
import fs from 'fs';
import { execFileSync } from 'child_process';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';

const MATO = [0.95, 0.92, 0.52, 1];   // tinge a textura de pedra: mato e terra por cima da pedra soterrada
const R = {
  'guimaraes-castro-de-sao-miguel-o-anjo': { mato: ['A-M1', 'A-M2', 'A-M3'] },
  'braga-castro-de-santa-marta-das-corticas': { mato: ['A-M1', 'A-M2'] },
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
if (cfg.mato) {
  const cache = new Map();
  for (const node of root.listNodes()) {
    if (!cfg.mato.includes(node.getName().replace(/\.\d+$/, '')) || !node.getMesh()) continue;
    for (const p of node.getMesh().listPrimitives()) {
      const m = p.getMaterial(); if (!m) continue;
      if (!cache.has(m)) cache.set(m, (m.getName() === 'mato' ? m : m.clone().setName('mato')).setBaseColorFactor(MATO).setRoughnessFactor(1));
      p.setMaterial(cache.get(m)); n++;
    }
  }
}
if (cfg.cor) for (const m of root.listMaterials()) if (cfg.cor[m.getName()]) { m.setBaseColorFactor(cfg.cor[m.getName()]); n++; }
await io.write(`${tmp}.glb`, doc);
console.log(`${id}: ${n} alterações`);
execFileSync('python3', ['mkpng.py', `${tmp}.glb`, `${F}.glb.png`], { stdio: 'inherit' });
execFileSync('node', ['tools/gltf/draco.mjs', `${tmp}.glb`, `${tmp}.d.glb`], { stdio: 'inherit' });
execFileSync('python3', ['mkpng.py', `${tmp}.d.glb`, `${F}.drc.glb.png`], { stdio: 'inherit' });
fs.rmSync(`${tmp}.glb`); fs.rmSync(`${tmp}.d.glb`);
