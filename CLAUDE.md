# Castros do Noroeste — atlas interativo

App web (artifact do claude.ai) com o atlas dos castros do Noroeste Peninsular, feita a partir da tese de doutoramento de
**Tiago Pinto** (Turismo, Universidade de Santiago de Compostela; site original castrosdonoroestedeportugal.pt).
Escreve em português (muitas vezes no telemóvel); responder sempre em português de Portugal.

- **App publicada:** https://claude.ai/artifact/J1zReem6sDceCc7CVTBHB8 (partilhada "qualquer pessoa com o link").
  Para atualizar: Artifact `publish` com `file_path` = `app/index.html` e `url` = esse link; ficheiros de apoio em `files`
  (`{"caminho/publicado": {"from": "app/..."}}`). Ler o artifact primeiro (`action: read`) numa conversa nova.
  As `capabilities` (user, db com coleções comments/history/extra, assets) passam de versão para versão: omitir o campo.
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
| `lidar/` | LiDAR DGT 2025 de Briteiros (`raw/*.tif`) e scripts de vetorização |
| `dig/`, `tools/` | digitalizações antigas e scripts de dados; **nunca** usar `tools/merge_rev_OLD_do_not_use.py` |
| `geo/`, `osm/` | limites (CAOP, geoBoundaries), rios, OSM (`braga.pbf`, `mask_sites.json` = estradas/água por sítio) |
| `tests/` | scripts Playwright de captura (`mock.html` simula o runtime `window.claude`) |
| `docs/blocos_lidar_castros.md` | blocos LiDAR DGT a pedir para cada um dos 100 sítios, por prioridade |

## Ambiente (reinstalar numa sessão nova)

```sh
python3 -m venv /opt/bvenv && /opt/bvenv/bin/pip install bpy==5.1.2 numpy pillow scipy matplotlib opencv-python-headless scikit-image rasterio pyproj osmium
python3 lidar/mosaic.py          # → lidar/mdt.npy, lidar/mds.npy
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
4. **Blender** (`blend/dio_brit.py <id>` como modelo): disco com saia estratificada, terreno + plataformas das casas, muralhas, casas,
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

- Feito com nível máximo: **Citânia de Briteiros** (LiDAR, levantamento geral da U. Minho, painel, fotografias), **Castro de Sabroso** (planta de 1930, sem LiDAR).
- O Tiago quer este nível em **todos** os sítios, um a um. Próximo: **Citânia de Sanfins** (blocos 178484, 178485, 179484, 179485),
  depois Santa Luzia, Bagunte, Cossourado; atualizar Sabroso com LiDAR (182505, 182506). Ver `docs/blocos_lidar_castros.md`.
- Por confirmar com o Tiago: classificação de Roriz e de N.ª Sr.ª da Graça; Ázere MN 1910.
