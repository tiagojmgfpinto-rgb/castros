# Castros do Noroeste — site público

Site do atlas dos castros do Noroeste, construído **sobre o site dos Castelos** (repositório `castelos-site`): a mesma
disposição, navegação, páginas, componentes e visor 3D, em computador e telemóvel. Só a simbologia muda para símbolos
castrejos: a marca é uma roda com o tríscele (com o aro de contas das cordas entrançadas), e no mapa e no índice cada
tipo de sítio tem o seu símbolo (casa redonda de colmo para castros e povoados, três casas num anel de muralha para
citânias e cividades, pedra formosa para os balneários, roda com tríscele para os museus).

Publicado no GitHub Pages pelo workflow `.github/workflows/publicar.yml` a cada push no `main`.

## De onde vêm os dados

| O quê | Como se gera |
| --- | --- |
| `src/content/monumentos/<id>.md` (144 fichas) | `python3 ../tools/site_conteudo.py` a partir de `../data.json` (história com fontes, ficha técnica, cronologia, medidas, «sabia que», horários) |
| `public/imagens/<id>/` (fotografias da tese) | o mesmo script; não ficam no git, o workflow corre `--imagens` |
| `public/maquetas/<id>/<id>.glb` e `src/data/maquetas/<id>.json` | `node ../tools/gltf/castelos.mjs <id>` a partir de `../app/dio/<id>.glb.png`, `../app/dio/<id>.json` e `../maquetas/<id>.json` |
| `public/maquetas/<id>/capa.jpg` | `node ../tests/capas.mjs` com o site compilado a servir em `BASE` |
| `public/terrain/` (relevo do mapa) | pipeline de `pipeline/terrain/` (Copernicus GLO-30), igual aos Castelos; não fica no git |

Os textos da tese («Análise do Local no Estudo») e o diário de campo **não entram neste site por agora**: são os
apontamentos do Tiago, que decide depois onde ficam. Continuam em `../data.json` e na app do artifact.

Como nos Castelos, o mapa principal mostra só os sítios com maqueta 3D publicada; os outros estão em
«Próximas adições» e no catálogo `/castros/`, cada um com a sua ficha permanente. Os endereços antigos
`/castro/<id>/` reencaminham para as fichas novas.

## Desenvolvimento

```bash
npm ci
pip install -r pipeline/requirements.txt
# relevo (uma vez): ver o passo «Relevo Copernicus GLO-30» do workflow
npm run dev
npm test                      # vitest
BASE_PATH=/castros/ npm run build && npx playwright test
```
