"""Gera o conteúdo do site (site/, cópia do site dos Castelos) a partir de data.json.

Saída:
  site/src/content/monumentos/<id>.md   uma ficha por sítio, no esquema de site/src/content.config.ts
  site/public/imagens/<id>/NN.jpg       fotografias da tese (recortadas da tira app/ph/<id>.jpg) e imagens Commons (app/ext)

Os textos da tese (campo `text`, «Análise do Local no Estudo») e o diário de campo ficam de fora de propósito:
são os apontamentos do Tiago e ele decide depois onde vão. Continuam em data.json e na app do artifact.
Uso: python3 tools/site_conteudo.py            (fichas e imagens)
     python3 tools/site_conteudo.py --imagens   (só as imagens, que não ficam no git: a publicação gera-as)
"""
import json, os, re, shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
OUT_MD = os.path.join(SITE, 'src', 'content', 'monumentos')
OUT_IMG = os.path.join(SITE, 'public', 'imagens')
ADICIONADO = '2026-10-27T23:41:11Z'   # primeiro commit do repositório: os 144 sítios entraram juntos

REGIAO = {'Braga': 'norte', 'Viana do Castelo': 'norte', 'Vila Real': 'norte', 'Porto': 'norte', 'Bragança': 'norte',
          'Aveiro': 'centro', 'Lisboa': 'lisboa-vale-tejo'}
TIPO_NOME = {'castro': 'Castro', 'citania': 'Citânia', 'cividade': 'Cividade', 'povoado': 'Povoado fortificado',
             'balneario': 'Balneário castrejo', 'museu': 'Espaço museológico', 'outro': 'Outro sítio'}
# maquetas publicadas: dia do primeiro commit do GLB em app/dio
MAQUETAS = {'guimaraes-citania-de-briteiros': '2026-10-27', 'guimaraes-castro-de-sabroso': '2026-10-27',
            'guimaraes-castro-de-sao-miguel-o-anjo': '2026-11-02', 'braga-castro-de-santa-marta-das-corticas': '2026-11-02',
            'braga-castro-maximo': '2026-11-03'}


def q(s):
    return json.dumps(str(s), ensure_ascii=False)


def yaml(v, ind=0):
    """YAML simples (escalares em JSON, que é YAML válido)."""
    p = '  ' * ind
    if isinstance(v, dict):
        out = []
        for k, x in v.items():
            if x is None or x == [] or x == {}:
                continue
            if isinstance(x, (dict, list)):
                out.append(f'{p}{k}:\n{yaml(x, ind + 1)}')
            else:
                out.append(f'{p}{k}: {sc(x)}')
        return '\n'.join(out)
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, dict):
                body = yaml(x, ind + 1).lstrip()
                out.append(f'{p}- {body}')
            else:
                out.append(f'{p}- {sc(x)}')
        return '\n'.join(out)
    return p + sc(v)


def sc(x):
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, (int, float)):
        return repr(x)
    return q(x)


def fonte(t, u=None):
    f = {'titulo': t}
    if u and re.match(r'^https?://', u):
        f['url'] = u
    return f


def refs_txt(keys, refs):
    return [k for k in keys if k in refs]


def main():
    import sys
    so_imagens = '--imagens' in sys.argv
    d = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    os.makedirs(OUT_MD, exist_ok=True)
    for f in ([] if so_imagens else os.listdir(OUT_MD)):
        if f.endswith('.md'):
            os.remove(os.path.join(OUT_MD, f))
    if os.path.isdir(OUT_IMG):
        shutil.rmtree(OUT_IMG)
    for s in d['sites']:
        sid = s['id']
        hist = s.get('hist') or {}
        par = [p for p in hist.get('p', []) if p.strip()]
        fic = s.get('fic') or {}
        refs = fic.get('refs') or {}
        fontes, vistos = [], set()
        for x in hist.get('src', []):
            if x.get('t') and x['t'] not in vistos:
                vistos.add(x['t']); fontes.append(fonte(x['t'], x.get('u')))
        for k, x in refs.items():
            if x.get('t') and x['t'] not in vistos:
                vistos.add(x['t']); fontes.append(fonte(x['t'], x.get('u')))
        cls = s.get('cls') or {}
        protecao = f"{cls['l']} ({cls['y']})" if cls.get('l') and cls.get('y') else cls.get('l')
        lat, lon = s['coords']
        fm = {
            'nome': s['name'],
            'tipologia': s['kind'],
            'territorio': 'continente',
            'regiao': REGIAO.get(s['distrito'], 'norte'),
            'distrito': s['distrito'],
            'concelho': s['municipio'],
            'localidade': s['municipio'],
            'coordenadas': {'lat': lat, 'lon': lon, 'verificadas': True,
                            'fonte': f"Tese de Tiago Pinto (USC), visita de {s['visit']}" if s.get('visit') else 'Tese de Tiago Pinto (USC)'},
        }
        if protecao:
            fm['classificacao'] = {'categoria': protecao}
        fm['estadoFicha'] = 'publicada' if fontes and par else 'em-preparacao'
        fm['estadoMaqueta'] = 'concluida' if sid in MAQUETAS else 'pendente'
        # um sítio com maqueta entra no mapa no dia em que a maqueta foi publicada
        fm['adicionado'] = MAQUETAS[sid] + 'T00:00:00Z' if sid in MAQUETAS else ADICIONADO
        fm['prioritario'] = sid in MAQUETAS
        if par:
            fm['resumo'] = par[0]
        ft = {'tipologia': TIPO_NOME.get(s['kind'], s['kind'])}
        if protecao:
            ft['protecao'] = protecao
        fm['fichaTecnica'] = ft
        if fic.get('ver'):
            fm['oQueVer'] = [{'nome': re.sub(r'[.;]$', '', t), 'texto': ''} for t, _ in fic['ver']]
        if fic.get('cro'):
            fm['cronologia'] = [{'ano': a, 'texto': t} for a, t, _ in fic['cro']]
        if fic.get('med'):
            fm['medidas'] = [{'conceito': c, 'valor': v} for c, v, _ in fic['med']]
        if fic.get('sab'):
            fm['curiosidades'] = [t for t, _ in fic['sab']]
        # imagens: fotografias da tese (tira vertical app/ph) e imagens Commons da ficha
        imgs = []
        ph = s.get('ph') or {}
        if ph.get('f') and os.path.exists(os.path.join(ROOT, 'app', ph['f'])):
            tira = Image.open(os.path.join(ROOT, 'app', ph['f'])).convert('RGB')
            os.makedirs(os.path.join(OUT_IMG, sid), exist_ok=True)
            for i, (y, h) in enumerate(ph.get('p', [])):
                nome = f'{i + 1:02d}.jpg'
                tira.crop((0, y, tira.width, y + h)).save(os.path.join(OUT_IMG, sid, nome), quality=84, optimize=True, progressive=True)
                imgs.append({'ficheiro': f'imagens/{sid}/{nome}', 'legenda': f"{s['name']}, fotografia da visita de {s['visit']}." if s.get('visit') else s['name'],
                             'autor': 'Tiago Pinto', 'licenca': 'todos os direitos reservados'})
        for i, e in enumerate(fic.get('ext') or []):
            src = os.path.join(ROOT, 'app', e['f'])
            if not os.path.exists(src):
                continue
            os.makedirs(os.path.join(OUT_IMG, sid), exist_ok=True)
            nome = f'commons-{i + 1:02d}.jpg'
            Image.open(src).convert('RGB').save(os.path.join(OUT_IMG, sid, nome), quality=86, optimize=True, progressive=True)
            img = {'ficheiro': f'imagens/{sid}/{nome}', 'legenda': e.get('c') or s['name'], 'autor': e.get('a') or 'desconhecido', 'licenca': e.get('l') or ''}
            if e.get('u'):
                img['url'] = e['u']
            imgs.append(img)
        if imgs:
            fm['imagens'] = imgs
        hrs = s.get('hrs')
        if hrs and hrs.get('h'):
            v = {'resumo': hrs['h'].split(' · ')[0], 'horario': hrs['h']}
            if hrs.get('t'):
                v['contactos'] = hrs['t']
            if hrs.get('u'):
                v['site'] = fonte(hrs.get('src') or 'Horário', hrs['u'])
            fm['visita'] = v
        if sid in MAQUETAS:
            fm['maquetas'] = [{'tipo': 'estado-atual', 'ficheiro': f'maquetas/{sid}/{sid}.glb', 'validada': True,
                               'capa': f'maquetas/{sid}/capa.jpg', 'publicada': MAQUETAS[sid]}]
        fm['fontes'] = fontes
        corpo = '\n\n'.join(par[1:]) if len(par) > 1 else ''
        if so_imagens:
            continue
        with open(os.path.join(OUT_MD, f'{sid}.md'), 'w', encoding='utf-8') as f:
            f.write('---\n' + yaml(fm) + '\n---\n\n' + corpo + ('\n' if corpo else ''))
    print(len(d['sites']), 'sítios', '(só imagens)' if so_imagens else '')


if __name__ == '__main__':
    main()
