# Castros do Noroeste — atlas interativo

App web (artifact do claude.ai) com o atlas dos castros do Noroeste Peninsular, feita a partir da tese de doutoramento de
**Tiago Pinto** (Turismo, Universidade de Santiago de Compostela; site original castrosdonoroestedeportugal.pt).
Escreve em português (muitas vezes no telemóvel); responder sempre em português de Portugal.

- **App publicada:** https://claude.ai/artifact/J1zReem6sDceCc7CVTBHB8 (partilhada "qualquer pessoa com o link").
  Para atualizar: Artifact `publish` com `file_path` = `app/index.html` e `url` = esse link; ficheiros de apoio em `files`
  (`{"caminho/publicado": {"from": "app/..."}}`; incluir `dio/<id>.drc.glb.png` e `draco/draco_wasm_wrapper.js`, `draco/draco_decoder.wasm`). Ler o artifact primeiro (`action: read`) numa conversa nova.
  As `capabilities` (user, db com coleções comments/history/extra, assets) passam de versão para versão: omitir o campo.
- **Site público (GitHub Pages):** https://tiagojmgfpinto-rgb.github.io/castros/ — desde nov. 2026 é o projeto **`site/`**, uma cópia do
  site dos Castelos (repo `tiagojmgfpinto-rgb/castelos-site`: Astro + React Three Fiber, relevo Copernicus, visor 3D dos Castelos) com
  símbolos castrejos no lugar dos castelos (marca com tríscele, casa redonda, citânia, pedra formosa, roda). Ver `site/README.md`.
  Fichas: `python3 tools/site_conteudo.py` (data.json → `site/src/content/monumentos/*.md`); maquetas: `node tools/gltf/castelos.mjs`
  (GLB do artifact → `site/public/maquetas/<id>/<id>.glb` + `site/src/data/maquetas/<id>.json`; só o estado atual, peças A/AB); capas:
  `node tests/capas.mjs`. O workflow `.github/workflows/publicar.yml` compila `site/` a cada push no `main`. Regra dos Castelos: o mapa
  só mostra os sítios com maqueta publicada; os outros estão em «Próximas adições». Endereços antigos `/castro/<id>/` reencaminham.
  Os textos da tese («Análise do Local no Estudo») e o diário de campo não entram no site: o Tiago decide depois onde ficam.
  O antigo site (`tools/site.py`, `tools/pages.py`) já não é publicado; a app do artifact (`app/`, `build.py`) continua igual.
- Estilo visual pedido: como **castillos.site** (maqueta 3D inclinada do noroeste, miniaturas brancas, título Cinzel com escudo).

## Estrutura

| Caminho | O quê |
|---|---|
| `app/src.html` | código-fonte da app (HTML+CSS+JS num ficheiro; Leaflet 1.9.4; three.js 0.170 ESM no visor das maquetas e 0.160 UMD na maqueta do noroeste, via CDN) |
| `app/index.html` | build publicado (gerado por `python3 build.py`) |
| `data.json` | dados completos dos sítios (fonte). **Depois de editar, correr `python3 tools/split.py`** → `app/data.json` (índice, 91 KB), `app/fichas.json` (`hist`, `sa`, `fic`, carregado logo a seguir; um link `#<id>` espera por ele) + `app/texts.json` (textos da tese, em segundo plano) |
| `app/dio/<id>.glb.png`, `<id>.drc.glb.png`, `<id>.json` | maquetas 3D por sítio (GLB dentro de PNG; `.drc` = o mesmo com Draco, carregado primeiro) + catálogo de estruturas/fontes/árvores |
| `app/draco/` | descodificador Draco (`draco_wasm_wrapper.js` + `draco_decoder.wasm`), publicado com a app |
| `maquetas/<id>.json`, `maquetas/luz.json` | dados do visualizador de cada maqueta (`order`, `cap`, `gaps`, `layers`, `noB`, `cam`, `tour` [{sid,title,text}], `luz` opcional) e luz comum; o `build.py` escreve-os em `DIOS`/`LUZ`. Uma maqueta nova = GLB + `app/dio/<id>.json` do Blender + este ficheiro, sem mexer no código |
| `app/maq-*.jpg`, `app/maq-h.png` | textura e alturas da maqueta do noroeste (gerados por `tools/maquette.py`) |
| `blend/` | scripts Blender das maquetas por sítio e dados georreferenciados (plantas, ajustes, casas, muros) |
| `lidar/` | LiDAR DGT 2025 (`raw/*.tif`: Briteiros 184507/185507, Sabroso 182505, S. Miguel-o-Anjo 178499/178500/179499/179500, Santa Marta das Cortiças 177505/177506/178505/178506, Castro Máximo 175511 v03, São Paio 149480/150480 v03) e scripts. Castro Máximo: `cmx_laz.py`, `cmx_fill.py` (buraco da prisão), `cmx_osm.py`, `cmx_roofs.py` (casas da ortofoto). Santa Marta: `smc_laz.py`, `smc_lines.py` (linhas de `blend/smc_trace.py`, com os penedos retirados por abertura morfológica). S. Miguel-o-Anjo: `sma_laz.py` (LAZ 178499+179499 → terreno 25 cm), `sma_lines.py` (linhas de `blend/sma_trace.py` ajustadas ao talude). Sabroso: `sab_laz.py` (nuvem LAZ → terreno e copas de 25 cm), `sab_georef.py` (planta de 1930 ajustada ao talude da muralha). Sanfins (178484/178485/179484/179485): `sfn_laz.py` (4 LAZ → terreno/MDS 25 cm), `sfn_walls.py` (muros e 138 casas do MDS−MDT), `sfn_lines.py` (muralha M1 e muros S1–S3 de `blend/sfn_trace.py`). São Paio: `spa_laz.py` (LAZ 150480 do lado de terra + MDT/MDS 50 cm do 149480 no castro, `spa_cnt25.npy` = pontos por célula), `spa_orto.py` (ortofoto: capturas dos mosaicos z19/z20 em `lidar/spa/orto/`, alinhadas ao LiDAR por correlação de arestas), `spa_lines.py` (talude nascente), `spa_views.py` + `tests/dio_spa_views.mjs` (vistas das fotografias; `__dio.cur.setCam` no visor), `spa_overlay.py` (controlo sobre o relevo e a ortofoto) |
| `dig/`, `tools/` | digitalizações antigas e scripts de dados; **nunca** usar `tools/merge_rev_OLD_do_not_use.py` |
| `geo/`, `osm/` | limites (CAOP, geoBoundaries), rios, OSM (`braga.pbf`, `mask_sites.json` = estradas/água por sítio) |
| `tests/` | scripts Playwright de captura (`mock.html` simula o runtime `window.claude`) |
| `docs/blocos_lidar_castros.md` | blocos LiDAR DGT a pedir para cada um dos 100 sítios, por prioridade |
| `docs/prompt-fichas-maquetas.md` | prompt que o Tiago cola para pedir uma nova ficha + maqueta «metro a metro» (critérios, validação, entrega) |

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
  Com as CDN bloqueadas, `CDN=<pasta>` com `node_modules/three` (0.170), `three160` (alias `npm i three160@npm:three@0.160.0`), `leaflet`, `topojson`.
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
5. **Exportar**: `bash mkparts.sh <id>` → `app/dio/<id>.glb.png`. Corre `tools/gltf/lighten.mjs` (instalar uma vez: `npm ci --prefix tools/gltf`):
   terreno simplificado com meshoptimizer para ~60 mil triângulos (borda fixa; erro vertical medido em cada vértice original e escrito
   em `tools/gltf/reports/<id>.json`; nov. 2026: p95 5–13 cm, máximo 0,3–1,4 m só em faces verticais de pedreiras), texturas ≤ 2048 px,
   weld + quantize (14/8/12) e sem apagar os nós vazios `LBL-*` (rótulos) → `app/dio/<id>.glb.png`; depois `tools/gltf/draco.mjs`
   (Google Draco, edgebreaker, sem weld nem prune; verifica nós, malhas e triângulos não degenerados; as posições ficam exatas) → `app/dio/<id>.drc.glb.png`,
   cerca de metade do tamanho (nov. 2026: as 7 maquetas 17,8 → 9,1 MB). O visor carrega o `.drc` e descodifica-o na thread principal com
   `app/draco/` (descodificador glTF do Draco 1.5.7 vindo do three 0.170, WebAssembly; se falhar, a cópia na CDN); se o Draco falhar por
   qualquer motivo, carrega o `.glb.png` normal. Por isso os dois ficheiros são publicados. `NODRACO=1` nos testes `dio_all`/`dio_pick` força o recurso.
   No visor as árvores têm nível de pormenor: uma copa com menos de 24 px no ecrã usa uma cópia simplificada do protótipo (agrupamento de vértices, refeito com a câmara).
   No visor as estruturas são desenhadas juntas por material (Briteiros 906 → 58 chamadas de desenho); as peças originais ficam na camada 1 para a lógica e a seleção.
   O artifact não serve `.glb`; o PNG reduz ~3× e o visualizador extrai os bytes. Limite de 16 MB por ficheiro publicado.
6. **Visualizador** (em `app/src.html`: `dioMount`; dados em `maquetas/<id>.json` e luz em `maquetas/luz.json`; tone mapping `tone` aces/neutral em `luz.json` (comparados em nov. 2026, fica aces); a mesma luz no Blender com `blend/luz.py` e render de controlo `blend/luz_render.py <glb> <png> <id>` (Cycles CPU); computador = sombra 4096 ajustada à maqueta + RoomEnvironment + GTAO, telemóvel/tátil = sombra 1024 sem pós-processamento; enquadramento automático pela silhueta, `"cam":{az,el}` opcional no ficheiro da maqueta; `?v=` dos ficheiros escrito pelo `build.py`; capturas antes/depois de todas as maquetas: `CDN=<pasta npm> node tests/dio_all.mjs <saída> desk|phone`, `BASE=` para outro servidor): camadas A–E (A estado atual, B interpretação = cores de evidência confirmado / documentado / hipotético, C reconstituição se não houver `noB`, D só relevo com curvas de nível de 1 m em altitude real a partir de `ex`/`h0` do `app/dio/<id>.json` e exagero × 1/× 2, E estrutura isolada), grupos de peças (`layers`), rótulos que aproximam a câmara, botão norte, ficha por estrutura, visita guiada, fontes e lacunas. Teste das camadas: `node tests/dio_pick.mjs <saída> [id]` (`VP=desk`). Fases por estrutura só quando houver fonte (ainda nenhuma maqueta tem `phases`).

## Regras do Tiago

- **Nunca inventar** estruturas, medidas ou datas: tudo com fonte, e o que falta vai para a lista de lacunas (`gaps` em `maquetas/<id>.json`).
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
  capela pela classe edifício do LiDAR + fotografia, monumento de N.ª Sr.ª da Assunção 16 m; faltam as plantas do artigo, fig. 2-6, que o proxy bloqueia), **Castro Máximo** (Braga; `blend/dio_cmx.py`: só estado atual, `"noB": true` esconde a reconstituição;
  nada visível nem planta consultada, por isso sem muralhas nem casas castrejas; terreno, pedreira, estádio e casas do LiDAR 175511
  (edifícios = classe 6 + MDS em blocos de 1 m; o estádio inteiro no disco, com bancadas procedimentais, coberturas medidas e os 34 cabos que o LAZ apanha sobre o relvado); a DGT **não tem pontos num círculo de ≈ 190 m à volta da prisão**, que tapa a encosta
  nascente do cume: relevo por SRTM ajustado à borda e casas pela ortofoto; falta a dissertação de D. Rocha 2017, com as plantas de 2001). **Castro de São Paio** (Vila do Conde; `blend/dio_spa.py`: sem planta publicada; o castro está no bloco **149480, só com MDT/MDS 50 cm**
  (o LAZ 150480 cobre só o lado de terra): falta o LAZ 149480; talude nascente traçado no LiDAR (≈ 103 m, 3,6 m de desnível), as duas áreas
  escavadas e a estrutura circular C1 na ortofoto, capela pelo LiDAR (MDS + ajuste de empena), mar plano a 0,3 m; casas da reconstituição
  hipotéticas (4,2 m = diâmetro interior de C1); a cobertura do Centro Interpretativo está classificada como solo no LiDAR (nov. 2026: três blocos, terraço e alpendre em `lidar/spa/ci.json`, contornos da ortofoto em coordenadas do bloco; cota = MDT dentro do contorno e o terreno é baixado por baixo; passadiços `BW` com quatro ramais traçados na ortofoto); faltam as plantas
  das escavações de 1993-96 e a ortofoto da DGT, que o proxy bloqueia — a ortofoto veio de capturas do navegador do Tiago). Refeito em nov. 2026 com o perito (3,5 → 6,5/10; relatório em `/mnt/project-files/revisao-perito/castro-de-sao-paio/`): `blend/spa_tex.py` faz do chão um mapa de classes da ortofoto (mar, areia, rocha, pavimento, relva, mato, terra) com pormenor procedimental, em 4 texturas de quadrante (o `lighten.mjs` simplifica um terreno com várias primitivas, repartindo os triângulos); a vala de E1 é um buraco recortado no terreno com `bmesh.bisect_plane` (fundo, taipais e vigas seguem um plano ajustado à borda); capela pelo MDS (eixo por SVD, cruzes, anexo poente); canavial pela textura do MDS; costa (nov. 2026): malha polar de 2400 ângulos (≈ 0,26 m no rebordo), espuma das ondas do LiDAR (branca, lisa, ligada à água, até 2,5 m) baixada para debaixo de água na grelha com rampa de 1,5 m, rochas com até 1,2 m do MDS, textura das rochas pela altitude (zona molhada, algas, líquenes) e pelas fendas, água com textura de espuma junto às rochas, sem o material de granito nas faces íngremes (fazia dentes); o `sid` de cada objeto é reduzido ao do catálogo antes de exportar (um `sid` sem catálogo conta como casa e desvia o enquadramento). A nuvem de pontos (LAZ, quando o Tiago a envia) dá terreno de 25 cm, melhor que o MDT de 50 cm.
- Briteiros: espécies de Sabroso (eucalipto, castanheiro, carvalho, sobreiro, sem pinheiros) postas sem novo Blender com `tools/gltf/graft_protos.mjs` (protótipos) + `tools/brit_species.py` (altura e largura de copa do MDS−MDT); `tools/unpng.py` tira o GLB do PNG. O `blend/dio_brit.py` já não corre de raiz: faltam `lidar/houses.json`, `lidar/walls.json` e `app/t3/<id>-c.jpg` (e os scripts `lidar/walls.py`/`houses.py`). O `lidar/mosaic.py` precisa de rasterio (`/opt/bvenv`).
- **Citânia de Sanfins** (nov. 2026; `blend/dio_sfn.py`, disco de 225 m, `TRIS=150000 bash mkparts.sh <id>`): sem planta publicada consultada,
  tudo medido na nuvem de pontos. Os muros escavados sobressaem 0,15–2 m no MDS − MDT (a classe 6 «edifício» da DGT inclui muitos muros);
  metade das células de 25 cm não tem retorno, por isso a altura dos muros usa só as células com retorno > 0,1 m e o máximo 3×3 fecha as falhas.
  138 casas por Hough no esqueleto dos muros (≥ 70 % do anel), núcleo reconstruído = bloco com cobertura de uma água + dois cones, marco
  geodésico com base e pilar medidos. A ortofoto `app/t3/<id>-c.jpg` alinha com o LiDAR. Fotografias do Commons: o browser do app do
  Tiago abre a API do Commons (curl e web-fetch não); `tests/dio_views.mjs` tira a maqueta do mesmo ponto de vista de uma fotografia.
  Faltam: plantas de Paço 1953 (Zephyrus 4), Silva e Centeno 1980 (Est. I) e Silva 1999 (roteiro); capela de S. Romão e balneário sem posição.
- O Tiago quer este nível em **todos** os sítios, um a um. Próximo: Santa Luzia, Bagunte, Cossourado. (Sabroso já tem LiDAR: o bloco 182506 não é preciso, o disco cabe todo no 182505.) Ver `docs/blocos_lidar_castros.md`.
- Por confirmar com o Tiago: classificação de Roriz e de N.ª Sr.ª da Graça; Ázere MN 1910.
