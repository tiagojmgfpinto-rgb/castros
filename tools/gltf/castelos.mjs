// Converte uma maqueta dos castros (app/dio/<id>.glb.png + app/dio/<id>.json + maquetas/<id>.json) para o formato
// do visor do site, que é o dos Castelos (site/src/components/maqueta/Maqueta.tsx):
//   site/public/maquetas/<id>/<id>.glb   estado atual (peças A e AB), terreno, árvores instanciadas
//   site/src/data/maquetas/<id>.json     elementos com fontes e confiança, placas, limitações (= lacunas)
//
// O que muda no GLB:
//  - as peças da interpretação/reconstituição (modo B) saem: o visor dos Castelos mostra o estado atual;
//  - cada peça leva `extras.elemento` = sid e fica num grupo `<Tipo>_grupo` (muralhas, casas, …), e o terreno e a saia
//    do disco ficam em `Terreno_grupo` com os nomes `Terreno` e `Base` (o botão Terreno esconde-os);
//  - as árvores, que a app do artifact instanciava em tempo de execução a partir de `trees`, passam a nós com
//    EXT_mesh_gpu_instancing (posição, rotação, escala e cor de cada copa iguais às da app), no grupo `Vegetacao_grupo`;
//  - os rótulos `LBL-*` passam a placas (ponto da placa = posição do rótulo).
// Uso: node tools/gltf/castelos.mjs <id> [<id> …]     (instalar uma vez: npm ci --prefix tools/gltf)
import { Document, NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, EXTMeshGPUInstancing } from '@gltf-transform/extensions';
import { dequantizePrimitive, prune, transformMesh } from '@gltf-transform/functions';
import sharp from 'sharp';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);

// Tipo do catálogo -> grupo do visor (os grupos fora do enquadramento seguem FORA_DO_ENQUADRAMENTO do Maqueta.tsx)
const GRUPO = {
  'Muralha': ['Muralhas', 'Muralhas'], 'Muro': ['Muros', 'Muros'], 'Porta': ['Muralhas', 'Portas'], 'Entrada': ['Muralhas', 'Entradas'],
  'Habitação': ['Casas', 'Casas'], 'Edifício comunitário': ['Casas', 'Edifícios comunitários'], 'Indeterminada': ['Casas', 'Estruturas indeterminadas'],
  'Balneário': ['Balnearios', 'Balneários'], 'Estrutura hidráulica': ['Balnearios', 'Estruturas hidráulicas'], 'Arruamento': ['Ruas', 'Ruas'],
  'Reconstrução (séc. XIX)': ['Casas', 'Reconstruções do século XIX'], 'Afloramento': ['Afloramentos', 'Afloramentos'], 'Relevo': ['Afloramentos', 'Relevo'],
  'Pedreira': ['Afloramentos', 'Pedreira'], 'Escavação': ['Escavacao', 'Escavação'], 'Capela': ['Santuario', 'Capela'], 'Igreja': ['Igreja', 'Basílica'],
  'Palácio': ['Palacio', 'Edifício palatino'], 'Ruína': ['Palacio', 'Ruínas'], 'Monumento': ['Santuario', 'Monumentos'], 'Cruzeiro': ['Santuario', 'Monumentos'],
  'Marco': ['Santuario', 'Monumentos'], 'Edifício moderno': ['Edificios', 'Envolvente'], 'Infraestrutura moderna': ['Edificios', 'Envolvente'],
  'Equipamento moderno': ['Edificios', 'Envolvente'], 'Muro moderno': ['Edificios', 'Envolvente'],
};
const CONFIANCA = { conf: 'alta', doc: 'média', hip: 'baixa' };
const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const norm = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

async function glbDoPng(f) {
  const { data } = await sharp(f).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const n = data.readUInt32LE(0);
  return data.subarray(4, 4 + n);
}

function quatY(a) { return [0, Math.sin(a / 2), 0, Math.cos(a / 2)]; }

async function converter(id) {
  const meta = JSON.parse(fs.readFileSync(path.join(ROOT, 'app/dio', `${id}.json`), 'utf8'));
  const maq = JSON.parse(fs.readFileSync(path.join(ROOT, 'maquetas', `${id}.json`), 'utf8'));
  const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'data.json'), 'utf8'));
  const sitio = data.sites.find((s) => s.id === id);
  const doc = await io.readBinary(new Uint8Array(await glbDoPng(path.join(ROOT, 'app/dio', `${id}.glb.png`))));
  const root = doc.getRoot();
  const cena = root.listScenes()[0];
  const cat = new Map(meta.cat.map((c) => [c.id, c]));

  const grupos = new Map();
  const grupo = (nome) => {
    if (!grupos.has(nome)) { const g = doc.createNode(`${nome}_grupo`); cena.addChild(g); grupos.set(nome, g); }
    return grupos.get(nome);
  };
  const protos = {};
  const rotulos = [];
  const elementosVistos = new Set();
  for (const n of [...cena.listChildren()]) {
    const nome = n.getName();
    const x = n.getExtras() || {};
    if (nome.startsWith('PROTO-')) { const [, k, p] = nome.split('-'); (protos[k] ||= []).push({ p, n }); continue; }
    if (nome.startsWith('LBL-')) { rotulos.push({ texto: nome.slice(4).replace(/-\d+$/, '').replace(/_/g, ' '), pos: n.getTranslation() }); n.dispose(); continue; }
    if (nome === 'terrain' || nome === 'skirt') { n.setName(nome === 'terrain' ? 'Terreno' : 'Base'); cena.removeChild(n); grupo('Terreno').addChild(n); continue; }
    if (x.mode === 'B') { n.dispose(); continue; }
    if (x.sid) {
      const sid = x.sid.replace(/R$/, '');
      const c = cat.get(sid);
      const [g] = GRUPO[c?.kind] ?? ['Estruturas'];
      n.setExtras({ elemento: sid, ev: x.ev });
      cena.removeChild(n); grupo(g).addChild(n);
      elementosVistos.add(sid);
      continue;
    }
    // restantes peças sem catálogo (estradas, caminhos): envolvente
    cena.removeChild(n); grupo('Caminhos').addChild(n);
  }

  // Árvores: um nó instanciado por parte de cada protótipo, com a geometria já no sítio do protótipo
  const inst = doc.createExtension(EXTMeshGPUInstancing).setRequired(true);
  const veg = grupo('Vegetacao');
  veg.setExtras({ elemento: 'vegetacao' });
  const buf = root.listBuffers()[0];
  let nArvores = 0;
  (meta.types || []).forEach((k, ti) => {
    const lista = meta.trees.filter((t) => t[4] === ti);
    if (protos[k]?.length) nArvores += lista.length;
    for (const { p, n } of protos[k] || []) {
      if (!lista.length) continue;
      const malha = n.getMesh().clone();
      // as normais quantizadas (int8) não se podem transformar no sítio: passam a float antes
      for (const prim of malha.listPrimitives()) dequantizePrimitive(prim, { pattern: /.*/ });
      transformMesh(malha, n.getWorldMatrix());
      if (p === 'leaf') {
        for (const prim of malha.listPrimitives()) {
          const m = prim.getMaterial()?.clone();
          if (m) { m.setBaseColorFactor([1, 1, 1, 1]); if (k === 'tuft') m.setDoubleSided(true); prim.setMaterial(m); }
        }
      }
      const T = new Float32Array(lista.length * 3), R = new Float32Array(lista.length * 4), S = new Float32Array(lista.length * 3);
      const C = p === 'leaf' ? new Float32Array(lista.length * 3) : null;
      lista.forEach((t, i) => {
        T.set([t[0], t[2], -t[1]], i * 3);
        R.set(quatY(t[6]), i * 4);
        S.set([t[3] * (t[7] || 0.85 + (0.3 * ((i * 7) % 10)) / 10), t[3], t[3] * (t[7] || 1)], i * 3);
        if (C) { const L = (meta.pal ? meta.pal[k] : meta.leaf)[t[5]]; C.set([lin(L[0]), lin(L[1]), lin(L[2])], i * 3); }
      });
      const acc = (a, tipo) => doc.createAccessor().setType(tipo).setArray(a).setBuffer(buf);
      const gi = inst.createInstancedMesh().setAttribute('TRANSLATION', acc(T, 'VEC3')).setAttribute('ROTATION', acc(R, 'VEC4')).setAttribute('SCALE', acc(S, 'VEC3'));
      if (C) gi.setAttribute('_COLOR_0', acc(C, 'VEC3'));
      const no = doc.createNode(`Arvores-${k}-${p}`).setMesh(malha).setExtension('EXT_mesh_gpu_instancing', gi);
      veg.addChild(no);
    }
    for (const { n } of protos[k] || []) n.dispose();
  });
  for (const ps of Object.values(protos)) for (const { n } of ps) if (!n.isDisposed()) n.dispose();
  await doc.transform(prune({ keepLeaves: false, keepAttributes: true, keepExtras: true }));

  const pasta = path.join(ROOT, 'site/public/maquetas', id);
  fs.mkdirSync(pasta, { recursive: true });
  fs.writeFileSync(path.join(pasta, `${id}.glb`), await io.writeBinary(doc));

  // ——— dados do visor ———
  const fontes = Object.fromEntries(Object.entries(meta.sources || {}).map(([k, t]) => {
    const u = (t.match(/https?:\/\/\S+/) || [])[0];
    // o endereço sai do título (uma palavra tão longa transborda das caixas no telemóvel) e fica só como ligação
    return [k, u ? { titulo: t.replace(u, '').replace(/[\s:;,—-]+$/, '').trim(), url: u.replace(/[).,]+$/, '') } : { titulo: t }];
  }));
  const tour = new Map((maq.tour || []).map((t) => [t.sid, t]));
  // primeira frase (sem partir em «D.», «N.ª», «c.», números decimais…), ou o primeiro troço antes de « · »; até 90 carateres
  const frase = (s) => {
    s = (s || '').trim();
    if (!s) return undefined;
    let fim = s.length;
    for (const m of s.matchAll(/([.;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ«(])/g)) {
      const antes = s.slice(0, m.index).split(/[\s(]/).pop();
      if (antes.length <= 2 || /^(n|sr|sra|séc|st|aprox|cf|fig)$/i.test(antes.replace(/[.ªº]/g, ''))) continue;
      fim = m.index; break;
    }
    let f = s.slice(0, fim).replace(/[.;]$/, '');
    if (f.length > 90 && f.includes(' · ')) f = f.split(' · ')[0];
    if (f.length > 90) { const v = f.slice(0, 90).lastIndexOf(', '); if (v > 30) f = f.slice(0, v); }
    return f.length <= 90 ? f : undefined;
  };
  const elementos = [];
  for (const sid of elementosVistos) {
    const c = cat.get(sid);
    if (!c) continue;
    const [, rotulo] = GRUPO[c.kind] ?? [null, c.kind];
    const e = {
      id: sid, nome: c.name, grupo: rotulo, estado: 'estado-atual', confianca: CONFIANCA[c.ev] ?? 'média',
      descricao: [c.note, c.phase ? `Fase: ${c.phase}.` : ''].filter(Boolean).join(' '),
      fontes: (c.src || []).filter((k) => fontes[k]),
    };
    if (c.dims) e.medidas = c.dims;
    const t = tour.get(sid);
    const r = (t && frase(t.text)) || frase(c.note) || frase(c.dims);
    if (r) e.resumo = r;
    elementos.push(e);
  }
  const arvoresTxt = (maq.gaps || []).find((g) => /^Árvores/.test(g));
  elementos.push({ id: 'vegetacao', nome: 'Vegetação', grupo: 'Envolvente', estado: 'estado-atual', confianca: 'média',
    descricao: arvoresTxt ? arvoresTxt.replace(/^Árvores:\s*/, '') : `${nArvores} árvores nas posições e alturas medidas pelo LiDAR.`, fontes: fontes.lidar ? ['lidar'] : [] });

  // placas: os rótulos da maqueta (com o elemento do mesmo nome, se houver) e as paragens da visita guiada
  const porNome = new Map(elementos.map((e) => [norm(e.nome), e]));
  const placas = [];
  const PARADAS = new Set(['para', 'com', 'dos', 'das', 'aproximada', 'posicao', 'local', 'aprox', 'troco', 'fase']);
  const palavras = (s) => new Set(norm(s).split(/[^a-z0-9]+/).filter((w) => w.length >= 4 && !PARADAS.has(w)));
  const parecido = (texto) => {
    const p = palavras(texto);
    let melhor = null, nota = 0;
    for (const e of elementos) {
      if (e.id === 'vegetacao') continue;
      const q = palavras(e.nome);
      const comuns = [...p].filter((w) => q.has(w) || [...q].some((v) => v.startsWith(w.slice(0, 6)) && w.length >= 6)).length;
      const n = comuns / Math.max(1, Math.min(p.size, q.size));
      if (comuns > 0 && n > nota) { nota = n; melhor = e; }
    }
    return nota >= 0.5 ? melhor : null;
  };
  for (const r of rotulos) {
    let e = porNome.get(norm(r.texto)) || [...tour.values()].map((t) => (norm(t.title) === norm(r.texto) ? elementos.find((x) => x.id === t.sid) : null)).find(Boolean) || parecido(r.texto);
    if (!e) {
      e = { id: `rotulo-${norm(r.texto).replace(/[^a-z0-9]+/g, '-')}`, nome: r.texto, grupo: 'Rótulos', estado: 'estado-atual', confianca: 'média', descricao: '', fontes: [] };
      const t = [...tour.values()].find((t) => norm(t.title).includes(norm(r.texto)) || norm(r.texto).includes(norm(t.title)));
      if (t) { e.descricao = t.text; const r = frase(t.text); if (r) e.resumo = r; }
      // um rótulo sem peça nem texto não vira placa (as placas são só de elementos documentados, como nos Castelos)
      if (!e.descricao) continue;
      elementos.push(e);
    }
    if (!e.resumo) { const r = frase(e.descricao) || frase(e.medidas); if (r) e.resumo = r; }
    e.ancora = [r.pos[0], r.pos[1] + 2, r.pos[2]].map((v) => Math.round(v * 100) / 100);
    if (!placas.includes(e.id)) placas.push(e.id);
  }
  for (const t of maq.tour || []) if (elementos.some((e) => e.id === t.sid) && !placas.includes(t.sid)) placas.push(t.sid);

  const dados = {
    monumento: id,
    titulo: sitio.name,
    variante: 'estado-atual',
    versao: '1.0',
    data: (sitio.fic && sitio.date) || new Date().toISOString().slice(0, 10),
    origem: { lat: sitio.coords[0], lon: sitio.coords[1], nota: 'Ponto do sítio na tese. Eixos da maqueta: x para este, y para cima, z para sul, em metros; o relevo está exagerado ' + String(meta.ex).replace('.', ',') + '× na vertical.' },
    fontes,
    limitacoes: [maq.cap, ...(maq.gaps || [])].filter(Boolean),
    placas,
    elementos,
  };
  if (maq.cam && Number.isFinite(maq.cam.az)) {
    const az = (maq.cam.az * Math.PI) / 180, el = ((maq.cam.el ?? 35) * Math.PI) / 180;
    dados.direcao = [Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el)].map((v) => Math.round(v * 1000) / 1000);
  }
  fs.writeFileSync(path.join(ROOT, 'site/src/data/maquetas', `${id}.json`), JSON.stringify(dados, null, 2) + '\n');
  const kb = Math.round(fs.statSync(path.join(pasta, `${id}.glb`)).size / 1024);
  console.log(id, `${kb} KB`, `${elementos.length} elementos`, `${placas.length} placas`, `${nArvores} árvores`);
}

const ids = process.argv.slice(2);
for (const id of ids.length ? ids : fs.readdirSync(path.join(ROOT, 'maquetas')).filter((f) => f !== 'luz.json').map((f) => f.replace(/\.json$/, ''))) await converter(id);
