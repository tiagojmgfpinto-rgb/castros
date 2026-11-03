# Castros do Noroeste — atlas interativo

App web (artifact do claude.ai) com o atlas dos castros do Noroeste Peninsular, feita a partir da tese de doutoramento de
**Tiago Pinto** (Turismo, Universidade de Santiago de Compostela; site original castrosdonoroestedeportugal.pt).
Escreve em português (muitas vezes no telemóvel); responder sempre em português de Portugal.

- **App publicada:** https://claude.ai/artifact/J1zReem6sDceCc7CVTBHB8 (partilhada "qualquer pessoa com o link").
  Para atualizar: Artifact `publish` com `file_path` = `app/index.html` e `url` = esse link; ficheiros de apoio em `files`
  (`{"caminho/publicado": {"from": "app/..."}}`). Ler o artifact primeiro (`action: read`) numa conversa nova.
  As `capabilities` (user, db com coleções comments/history/extra, assets) passam de versão para versão: omitir o campo.
- **Site público (GitHub Pages):** https://tiagojmgfpinto-rgb.github.io/castros/ — o workflow `.github/workflows/publicar.yml`
  corre `python3 build.py` e `python3 tools/site.py` (→ `_site/`, com esqueleto HTML e metas) a cada push no `main`, como no castelos-site.
  Sem `window.claude` a app corre só em leitura (sem comentários, histórico editado nem castros acrescentados pela base de dados do artifact).
- Estilo visual pedido: como **castillos.site** (maqueta 3D inclinada do noroeste, miniaturas brancas, título Cinzel com escudo).

## Estrutura

| Caminho | O quê |
|---|---|
| `app/src.html` | código-fonte da app (HTML+CSS+JS num ficheiro; Leaflet 1.9.4, three.js 0.160 via CDN) |
| `app/index.html` | build publicado (gerado por `python3 build.py`) |
| `data.json` | dados completos dos sítios (fonte). **Depois de editar, correr `python3 tools/split.py`** → `app/data.json` + `app/texts.json` |
| `app/dio/<id>.glb.png`, `<id>.json` | maquetas 3D por sítio (GLB dentro de PNG) + catálogo de estruturas/fontes/árvores |
| `app/maq-*.jpg`, `app/maq-h.png` | textura e alturas da maqueta do noroeste (gerados por `tools/maquette.py`) |
| `blend/` | scripts Blender das maquetas por sítio e dados georreferenciados (plantas, ajustes, casas, muros) |
| `lidar/` | LiDAR DGT 2025 (`raw/*.tif`: Briteiros 184507/185507, Sabroso 182505, S. Miguel-o-Anjo 178499/178500/179499/179500, Santa Marta das Cortiças 177505/177506/178505/178506, Castro Máximo 175511 v03) e scripts. Castro Máximo: `cmx_laz.py`, `cmx_fill.py` (buraco da prisão), `cmx_osm.py`, `cmx_roofs.py` (casas da ortofoto). Santa Marta: `smc_laz.py`, `smc_lines.py` (linhas de `blend/smc_trace.py`, com os penedos retirados por abertura morfológica). S. Miguel-o-Anjo: `sma_laz.py` (LAZ 178499+179499 → terreno 25 cm), `sma_lines.py` (linhas de `blend/sma_trace.py` ajustadas ao talude). Sabroso: `sab_laz.py` (nuvem LAZ → terreno e copas de 25 cm), `sab_georef.py` (planta de 1930 ajustada ao talude da muralha) |
| `dig/`, `tools/` | digitalizações antigas e scripts de dados; **nunca** usar `tools/merge_rev_OLD_do_not_use.py` |
| `geo/`, `osm/` | limites (CAOP, geoBoundaries), rios, OSM (`braga.pbf`, `mask_sites.json` = estradas/água por sítio) |
| `tests/` | scripts Playwright de captura (`mock.html` simula o runtime `window.claude`) |
| `docs/blocos_lidar_castros.md` | blocos LiDAR DGT a pedir para cada um dos 100 sítios, por prioridade |

## Ambiente (reinstalar numa sessão nova)

```sh
python3 -m venv /opt/bvenv && /opt/bvenv/bin/pip install bpy==5.1.2 numpy pillow scipy matplotlib opencv-python-headless scikit-image rasterio pyproj osmium
python3 lidar/mosaic.py          # → lidar/mdt.npy, lidar/mds.npy (Briteiros)
/opt/bvenv/bin/python lidar/sab_laz.py   # Sabroso: precisa de /mnt/project-files/LO-182505-07-2025_v05.laz (128 MB, fora do repo)
sh tools/fetch_dem.sh            # só para refazer a maqueta do noroeste
```
- bpy 5.1 exige Python 3.13. gltf-transform: `npx -y @gltf-transform/cli@4.1.1` (ou definir `GLTF_TRANSFORM`).
- Teste local: `cd app && python3 -m http.server 8765 &`, depois `python3 build.py` e `node tests/<script>.mjs`
  (Playwright em `/opt/node22/lib/node_modules/playwright/index.mjs`, Chromium com `--use-angle=swiftshader --enable-unsafe-swiftshader`).
  As páginas de teste são `app/test.html` (com mock) e `app/test2.html`.

## Pipeline de uma maqueta de sítio (modelo: Citânia de Briteiros)

1. **Fontes**: procurar na *Revista de Guimarães* (csarmento.uminho.pt), SIPA/DGPC, município. Ler os PDFs (pdftotext).
   Escrever a ficha em `data.json` → `fic` (`refs`, `med`, `sab`, `cro`, `ver`, `ext` para imagens Commons com autor/licença).
2. **Georreferenciação**: as plantas são alinhadas por pontos fixos (casas, capela, muralha OSM) com `cv2.estimateAffinePartial2D`;
   registar o erro (Briteiros < 1 m). Referencial local: metros a partir do ponto do sítio, x = este, z = sul; PT-TM06 = EPSG:3763.
3. **LiDAR DGT (MDT + MDS 50 cm)**: o servidor da DGT (stor-002.a.acnca.pt:9000) está **bloqueado** pelo proxy; o Tiago descarrega
   e envia os blocos. Nome do bloco: `200+floor(x/1000)` e `301+floor(y/1000)` em PT-TM06. **Não** lhe dar scripts para correr no PC.
   MDT = relevo; MDS−MDT nas clareiras = muros (`lidar/walls.py`); ajuste de círculos = casas (`lidar/houses.py`); máximos do MDS−MDT = árvores.
4. **Blender** (`blend/dio_brit.py <id>` como modelo; Sabroso: `blend/dio_sab.py`): disco com saia estratificada, terreno + plataformas das casas, muralhas, casas,
   muros, ruas, edifícios modernos (só no estado atual), estrada com textura pintada, árvores instanciadas (carvalho, sobreiro, pinheiro),
   AO cozido no solo. Cada estrutura é um objeto `A-<sid>` / `B-<sid>` / `AB-<sid>` com `extras` (sid, mode, ev) e entrada no catálogo.
5. **Exportar**: `bash mkparts.sh <id>` (weld + quantize, **sem Draco**: o descodificador não corre no artifact) → `app/dio/<id>.glb.png`.
   O artifact não serve `.glb`; o PNG reduz ~3× e o visualizador extrai os bytes. Limite de 16 MB por ficheiro publicado.
6. **Visualizador** (em `app/src.html`: `DIOS`, `TOURS`, `dioMount`): estado atual/reconstituição, evidência (confirmado / documentado /
   hipotético), camadas, ficha por estrutura, visita guiada, fontes e lacunas.

## Regras do Tiago

- **Nunca inventar** estruturas, medidas ou datas: tudo com fonte, e o que falta vai para a lista de lacunas (`DIOS[id].gaps`).
- Distinguir sempre confirmado / reconstituído com fundamento / hipotético.
- Manter o sítio arqueológico limpo de árvores (rarear dentro das muralhas), mas com floresta realista à volta.
- Miniaturas do mapa principal: brancas/cinzentas com contorno, como no castillos.site; fronteira PT–ES bem marcada.
- Em Sabroso, sem casas retangulares inventadas (só muros).

## Estado e próximos passos

- Feito com nível máximo: **Citânia de Briteiros** (LiDAR, levantamento geral da U. Minho, painel, fotografias), **Castro de Sabroso**
  (planta de 1930 + LiDAR 2025 bloco 182505 com nuvem de pontos; a muralha do recinto superior está no MDT, por isso no estado atual a pedra
  cobre o talude real em vez de assentar por cima), **Castro de S. Miguel-o-Anjo** (Guimarães; sem planta publicada: três linhas
  de muralha traçadas no LiDAR 2025, troço dos escuteiros pelo ponto «Muro Celta» do OSM, capela; `blend/dio_sma.py`; falta o MDT 179499, não preciso), **Castro de Santa Marta das Cortiças** (Braga; `blend/dio_smc.py`: duas linhas traçadas no LiDAR,
  basílica e palácio com as medidas de Barroca, Arezes e Morais em posição aproximada (as coordenadas dos núcleos A e B parecem trocadas),
  capela pela classe edifício do LiDAR + fotografia, monumento de N.ª Sr.ª da Assunção 16 m; faltam as plantas do artigo, fig. 2-6, que o proxy bloqueia), **Castro Máximo** (Braga; `blend/dio_cmx.py`: só estado atual, `DIOS[id].noB` esconde a reconstituição;
  nada visível nem planta consultada, por isso sem muralhas nem casas castrejas; terreno, pedreira, estádio e casas do LiDAR 175511
  (edifícios = classe 6 + MDS em blocos de 1 m; o estádio inteiro no disco, com bancadas procedimentais, coberturas medidas e os 34 cabos que o LAZ apanha sobre o relvado); a DGT **não tem pontos num círculo de ≈ 190 m à volta da prisão**, que tapa a encosta
  nascente do cume: relevo por SRTM ajustado à borda e casas pela ortofoto; falta a dissertação de D. Rocha 2017, com as plantas de 2001). A nuvem de pontos (LAZ, quando o Tiago a envia) dá terreno de 25 cm, melhor que o MDT de 50 cm.
- O Tiago quer este nível em **todos** os sítios, um a um. Próximo: **Citânia de Sanfins** (blocos 178484, 178485, 179484, 179485),
  depois Santa Luzia, Bagunte, Cossourado. (Sabroso já tem LiDAR: o bloco 182506 não é preciso, o disco cabe todo no 182505.) Ver `docs/blocos_lidar_castros.md`.
- Por confirmar com o Tiago: classificação de Roriz e de N.ª Sr.ª da Graça; Ázere MN 1910.
