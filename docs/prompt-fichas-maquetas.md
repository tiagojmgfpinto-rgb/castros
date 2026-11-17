# Prompt para uma nova ficha + maqueta 3D (castros do Noroeste)

> Como usar: copia tudo a partir da linha «PROMPT», substitui o que está entre `«»` e cola numa conversa nova do projeto.
> Se enviares ficheiros (LAZ, MDT/MDS, PDFs, plantas, fotografias), põe-nos na pasta do projeto antes de colar.

---

PROMPT

Quero a ficha e a maqueta 3D do **«nome do sítio»** («concelho»), ao nível máximo de pormenor: **metro a metro**.
Lê primeiro o `CLAUDE.md` do repositório `tiagojmgfpinto-rgb/castros`, o `site/README.md` e a memória do projeto, e segue
o modelo das maquetas já feitas (Briteiros, Sabroso, S. Miguel-o-Anjo, Santa Marta das Cortiças, Castro Máximo).
Ficheiros que te enviei para este sítio: «LAZ / MDT / MDS (blocos …) / PDFs / plantas / fotografias, ou "nenhum"».

## 0. Regras que não se negociam

1. **Nunca inventar.** Cada muralha, casa, rua, medida ou data tem uma fonte citada (autor, ano, página ou figura).
   O que não tem fonte não se modela: vai para as lacunas (`gaps`), com o motivo.
2. Cada estrutura tem nível de evidência: **confirmado** (visível hoje no LiDAR, na ortofoto ou em fotografia, ou
   escavado e publicado), **documentado** (em planta ou texto publicado, sem confirmação no terreno) ou **hipotético**
   (reconstituição por paralelo, dito como tal).
3. «Metro a metro» quer dizer:
   - terreno com **25 cm** quando houver nuvem LAZ, nunca pior que os **50 cm** do MDT da DGT;
   - plantas georreferenciadas com **erro médio ≤ 1 m** (registar o erro e os pontos de controlo usados);
   - muralhas, casas e ruas posicionadas com **≤ 1 m** de erro face à planta e ao LiDAR, com as dimensões publicadas
     (diâmetro de cada casa, largura e altura de cada troço), não com valores médios repetidos;
   - depois de simplificar o terreno para o visor, erro vertical **p95 ≤ 10 cm** dentro da área arqueológica
     (relatório em `tools/gltf/reports/<id>.json`);
   - onde as fontes não chegam a 1 m, digo-o nas lacunas em vez de fingir precisão.
4. Português de Portugal em tudo o que aparece no site. Nada de scripts para eu correr no meu computador.

## 1. Fontes e bibliografia

Procura, lê (pdftotext) e cita, por esta ordem:
- **Revista de Guimarães** e outras publicações da Sociedade Martins Sarmento (csarmento.uminho.pt);
- **SIPA / DGPC / Património Cultural** (monumentos.gov.pt, patrimoniocultural.gov.pt): classificação, decreto, zona de proteção;
- **Portal do Arqueólogo** (endovélico): CNS, trabalhos, relatórios;
- artigos e teses em repositórios (RepositóriUM, Repositório Aberto da U. Porto, Dialnet, Academia), sobretudo as **plantas de escavação**;
- município e painéis interpretativos do sítio;
- **Wikimedia Commons** para fotografias (autor, licença, ano, ligação);
- a minha tese (já em `data.json`: `hist`, `sa`, textos).
Se um site estiver bloqueado pelo proxy, tenta outra via (WebFetch, outra cópia do PDF). Se mesmo assim não der,
**diz-me exatamente que PDF ou figura falta** (título, autor, figura) para eu a enviar, e continua com o resto.
Bibliografia em formato autor-data, com URL quando houver.

## 2. Ficha (`data.json` → `fic`, depois `python3 tools/split.py` e `python3 tools/site_conteudo.py`)

- `refs`: todas as fontes, com chave curta, referência completa e URL.
- `med`: medidas (área, cota, comprimento e altura das muralhas, número e diâmetro das casas, população estimada…),
  cada uma com as fontes. Incluir as medidas tiradas do LiDAR, ditas como tal.
- `cro`: cronologia (ocupação, escavações, classificação, intervenções), cada linha com fonte.
- `ver`: o que ver hoje no sítio, com fonte.
- `sab`: «sabia que», curiosidades com fonte.
- `ext`: fotografias Commons (ficheiro, legenda, autor, licença, ano, ligação, tamanho).
- No site: coordenadas verificadas, classificação, tipologia, resumo curto. Os textos da tese e o diário de campo **não** entram no site.

## 3. Terreno a partir do LiDAR

- Blocos DGT: `200+floor(x/1000)` e `301+floor(y/1000)` em PT-TM06 (EPSG:3763). Confirma que o disco da maqueta cabe nos
  blocos que tenho; se faltar algum, diz-me qual e porquê. Ver `docs/blocos_lidar_castros.md`.
- Com LAZ: terreno de 25 cm a partir dos pontos de solo (modelo: `lidar/sab_laz.py`, `lidar/smc_laz.py`); copas e edifícios das classes do LAZ.
- **Conta os pontos por célula** antes de confiar no terreno: a DGT apaga zonas sensíveis (no Castro Máximo, um círculo
  de ≈ 190 m à volta da prisão). Vazios: preencher com outra fonte, ajustada à borda, e dizê-lo nas lacunas.
- **Muralhas em talude podem estar dentro do MDT** (Sabroso): verifica no perfil se o talude de pedra foi classificado
  como solo; se sim, a pedra cobre o talude real em vez de assentar por cima.
- Granito com penedos (Santa Marta): tirar os penedos por abertura morfológica antes de traçar linhas ou ajustar muros.
- Exagero vertical só se ajudar a ler o relevo (Sabroso 1,15×), e sempre dito na legenda.

## 4. Muralhas, casas, arruamentos e outras estruturas

- Georreferenciar cada planta de escavação por pontos fixos (casas, capela, muralha visível no LiDAR, OSM) com
  `cv2.estimateAffinePartial2D`; registar o erro. Se houver várias plantas, cruzá-las e dizer qual manda em cada zona.
- Traçar a crista das muralhas à mão sobre o relevo e ajustá-la ao maior declive do talude (resultou melhor que os ajustes automáticos).
- MDS − MDT nas clareiras = muros visíveis; ajuste de círculos = casas; classe 6 do LAZ = edifícios modernos e capelas.
- Cada casa com o seu diâmetro e posição da planta; vestíbulos, portas, lajeados e ruas **só se estiverem na fonte**.
- Sem casas retangulares, coberturas ou portas inventadas; a cobertura cónica de colmo é reconstituição (hipotético).
- Edifícios modernos, estradas, capelas e muros atuais do LiDAR e do OSM, só no estado atual.
- Cada estrutura: objeto `A-<sid>` / `B-<sid>` / `AB-<sid>` com `extras` (sid, mode, ev) e entrada no catálogo
  `app/dio/<id>.json` (nome, tipo, fase, evidência, dimensões com números, nota e fontes).

## 5. Vegetação

- Árvores nas posições e alturas reais do LiDAR (máximos de MDS − MDT), com a largura de copa medida.
- Espécies do Minho, variadas e sem clones: **sobretudo eucalipto**, com castanheiro, carvalho e sobreiro; **sem pinheiros**
  (copa alta e estreita = eucalipto, larga = castanheiro; modelo em `blend/dio_sab.py` e `tools/brit_species.py`).
- Sítio arqueológico limpo: dentro das muralhas só 10–15 % das árvores e nenhuma a menos de 5 m das estruturas; floresta realista à volta.
- Dizer nas lacunas que a espécie não vem do LiDAR.

## 6. Blender, exportação e site

- Script `blend/dio_<sigla>.py` a partir dos existentes; luz comum com `blend/luz.py`.
- `bash mkparts.sh <id>` → `app/dio/<id>.glb.png` (sem Draco na app do artifact; ≤ 16 MB; rótulos `LBL-*` mantidos).
- `maquetas/<id>.json`: `cap` com as fontes do modelo, visita guiada (`tour`) com fonte em cada paragem, `gaps`, `layers`, `cam` se for preciso.
- Site: `node tools/gltf/castelos.mjs <id>` → `site/public/maquetas/<id>/<id>.glb` + `site/src/data/maquetas/<id>.json`
  (só o estado atual, peças A/AB); capa com `node tests/capas.mjs`. O sítio só entra no mapa quando tiver maqueta publicada
  (`estadoMaqueta: "concluida"`); até lá fica em «Próximas adições».

## 7. Validação antes de entregar

- **Contra fotografias reais** (Commons, as minhas, Google/painéis): pelo menos 3 vistas da maqueta tiradas do mesmo ponto
  e com a mesma direção de cada fotografia, lado a lado. Verificar silhueta do relevo, posição e altura das muralhas,
  casas visíveis, caminhos, capela, árvores. Listar o que não bate e corrigir ou explicar.
- **Sobreposição** das estruturas modeladas sobre o relevo sombreado do LiDAR e sobre a planta georreferenciada (imagem).
- Tabela de medidas: valor publicado vs. valor no modelo, para cada muralha e uma amostra de casas.
- Relatório do terreno simplificado (p95, máximo) e tamanho dos ficheiros.
- Testes: `node tests/dio_pick.mjs` (camadas), capturas computador e telemóvel (`tests/dio_all.mjs`), `npm test` e
  Playwright do `site/`; render de controlo no Blender (`blend/luz_render.py`).

## 8. Entrega

- Um **PR** no repositório com tudo (dados, scripts, GLB, ficha, site), descrição com as fontes, o erro de georreferenciação e as lacunas.
- Na pasta do projeto, numa subpasta com o nome do sítio: imagens **antes/depois**, comparação com as fotografias,
  sobreposição sobre o LiDAR e capturas de computador e telemóvel.
- Atualizar a app do artifact (link do `CLAUDE.md`) e o `CLAUDE.md` / memória com o estado e as lições novas.
- No fim, uma mensagem curta: o que ficou ao metro, o que ficou aproximado e porquê, e o que me falta enviar para fechar as lacunas.
