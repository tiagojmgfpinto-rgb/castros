"""Static pages for search engines and links (called by tools/site.py after it copies app/ to _site/):
/castros/ (catalogue), /castro/<id>/ (one record per site, with canonical URL and Open Graph), /creditos/ (sources and licences),
sitemap.xml and robots.txt. The atlas stays at / and its links /#<id> keep working; every record page links back to them.
Everything comes from app/data.json, app/fichas.json, app/dio/<id>.json and maquetas/<id>.json: nothing here is written by hand."""
import json, os, html, glob, datetime

URL = 'https://tiagojmgfpinto-rgb.github.io/castros/'
E = lambda x: html.escape(str(x or ''), quote=True)
TYPES = {'castro': 'Castro', 'citania': 'Citânia', 'cividade': 'Cividade', 'povoado': 'Povoado fortificado', 'balneario': 'Balneário castrejo',
         'outro': 'Outro sítio', 'museu': 'Espaço museológico'}
CSS = '''
:root{--bg:#efe7d4;--panel:#f8f3e6;--ink:#1f1a14;--muted:#6a5f50;--line:#cfc3a6;--accent:#9E6B0C;--gules:#9c2a1e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 Alegreya,Georgia,serif}
a{color:var(--accent)}header,main,footer{max-width:860px;margin:0 auto;padding:0 16px}
header{padding-top:22px;display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}header a.home{font-family:Cinzel,serif;font-weight:700;font-size:20px;color:var(--ink);text-decoration:none}
header nav{margin-left:auto;display:flex;gap:16px;font-family:"Alegreya Sans SC",sans-serif;font-size:15px}
h1{font-family:Cinzel,serif;font-weight:600;font-size:clamp(28px,6vw,42px);line-height:1.1;margin:18px 0 6px}
h2{font-family:Cinzel,serif;font-weight:600;font-size:21px;margin:28px 0 8px}
.eyebrow{font-family:"Alegreya Sans SC",sans-serif;color:var(--gules);letter-spacing:.08em;font-size:14px}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.tags span{border:1px solid var(--line);padding:1px 8px;font-size:14px;background:var(--panel)}
.btn{display:inline-block;margin:10px 8px 6px 0;padding:8px 14px;background:var(--ink);color:var(--panel);text-decoration:none;font-family:"Alegreya Sans SC",sans-serif;letter-spacing:.05em}
.btn.alt{background:transparent;color:var(--ink);border:1px solid var(--ink)}
figure{margin:16px 0}figure .crop{overflow:hidden;background:var(--panel)}figure img{display:block;width:100%;height:100%;object-fit:cover}
figcaption{font-size:14px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:15.5px}td,th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{font-family:"Alegreya Sans SC",sans-serif;font-weight:600}
ol,ul{padding-left:20px}li{margin:4px 0}.muted{color:var(--muted)}.src{font-size:15px}
footer{margin-top:40px;padding:18px 16px 40px;border-top:1px solid var(--line);font-size:14px;color:var(--muted)}
.dist{columns:2 260px;column-gap:28px}.dist section{break-inside:avoid;margin-bottom:14px}.dist h3{font-family:Cinzel,serif;font-size:16px;margin:0 0 4px}
'''

def page(path, title, desc, body, canon, og_img=None, ld=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    depth = canon[len(URL):].count('/')
    up = '../' * depth
    img = og_img or URL + 'maq.jpg'
    out = f'''<!doctype html>
<html lang="pt-PT"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}">
<meta property="og:type" content="article"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canon}"><meta property="og:image" content="{img}"><meta property="og:locale" content="pt_PT"><meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Alegreya:ital,wght@0,400;0,600;1,400&family=Alegreya+Sans+SC:wght@500;600&display=swap">
<style>{CSS}</style>{f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ''}</head>
<body><header><a class="home" href="{up}">Castros do Noroeste</a><nav><a href="{up}">Atlas</a><a href="{up}castros/">Catálogo</a><a href="{up}creditos/">Créditos</a></nav></header>
<main>{body}</main>
<footer>Castros do Noroeste — atlas de campo a partir da tese de doutoramento em Turismo de Tiago Pinto (Universidade de Santiago de Compostela).
Textos de análise e fotografias © Tiago Pinto; reprodução só com autorização. <a href="{up}creditos/">Fontes e licenças</a>.</footer></body></html>
'''
    open(path, 'w', encoding='utf-8').write(out)

def srcs(lst):
    return ''.join(f'<li>{f"<a href=\"{E(x.get("u"))}\" rel=\"noopener\">{E(x.get("t"))}</a>" if x.get("u") else E(x.get("t"))}</li>' for x in lst)

def build(OUT):
    D = json.load(open('app/data.json', encoding='utf-8')); F = json.load(open('app/fichas.json', encoding='utf-8'))
    dios = {os.path.basename(f)[:-5] for f in glob.glob('maquetas/*.json') if not f.endswith('luz.json')}
    sites = sorted(D['sites'], key=lambda s: (s['distrito'], s['municipio'], s['name']))
    today = datetime.date.today().isoformat(); urls = [(URL, None), (URL + 'castros/', None), (URL + 'creditos/', None)]
    # --- one page per site
    for s in sites:
        sid = s['id']; h = F['hist'].get(sid) or {}; fic = F['fic'].get(sid) or {}; paras = h.get('p') or []
        canon = f'{URL}castro/{sid}/'; t = TYPES.get(s['kind'], s['kind'])
        desc = (paras[0] if paras else f'{t} em {s["municipio"]}, distrito de {s["distrito"]}.')
        desc = desc if len(desc) <= 158 else desc[:155].rsplit(' ', 1)[0] + '…'
        cls = s.get('cls') or {}
        tags = [t] + ([f'{cls["l"]}{" · " + cls["y"] if cls.get("y") else ""}'] if cls.get('l') else []) + (['Maqueta 3D'] if sid in dios else [])
        ph = s.get('ph'); fig = ''
        if ph and ph.get('p'):
            y, hh = ph['p'][0]; pos = 0 if ph['H'] == hh else y / (ph['H'] - hh) * 100
            fig = (f'<figure><div class="crop" style="aspect-ratio:900/{hh}"><img src="../../{E(ph["f"])}" alt="{E(s["name"])}" '
                   f'style="object-position:50% {pos:.2f}%" loading="eager"></div><figcaption>Fotografia © Tiago Pinto</figcaption></figure>')
        med = fic.get('med') or []
        medh = ('<h2>Medidas</h2><table>' + ''.join(f'<tr><th>{E(k)}</th><td>{E(v)}</td></tr>' for k, v, *_ in med) + '</table>') if med else ''
        cro = fic.get('cro') or []
        croh = ('<h2>Cronologia</h2><table>' + ''.join(f'<tr><th>{E(k)}</th><td>{E(v)}</td></tr>' for k, v, *_ in cro) + '</table>') if cro else ''
        ver = fic.get('ver') or []
        verh = ('<h2>O que ver</h2><ul>' + ''.join(f'<li>{E(v[0])}</li>' for v in ver) + '</ul>') if ver else ''
        refs = list((fic.get('refs') or {}).values())
        hrs = s.get('hrs') or {}
        visit = (f'<h2>Visita</h2><p>{E(hrs.get("h"))}{f" · Tel. {E(hrs.get("t"))}" if hrs.get("t") else ""}'
                 f'{f" · fonte: <a href=\"{E(hrs.get("u"))}\" rel=\"noopener\">{E(hrs.get("src") or "ver")}</a>" if hrs.get("u") else ""}</p>') if hrs.get('h') else ''
        lat, lon = (s.get('coords') or [None, None])
        body = (f'<div class="eyebrow">{E(s["municipio"])} · distrito de {E(s["distrito"])}</div><h1>{E(s["name"])}</h1>'
                f'<div class="tags">{"".join(f"<span>{E(x)}</span>" for x in tags)}</div>'
                f'<a class="btn" href="../../#{E(sid)}">Abrir no atlas{" com a maqueta 3D" if sid in dios else ""}</a>'
                f'{f"<a class=\"btn alt\" href=\"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}\" rel=\"noopener\">Ver no mapa (OSM)</a>" if lat else ""}'
                f'{fig}{"".join(f"<p>{E(p)}</p>" for p in paras)}{medh}{croh}{verh}{visit}'
                f'{("<h2>Fontes</h2><ol class=\"src\">" + srcs(h.get("src") or []) + srcs(refs) + "</ol>") if (h.get("src") or refs) else ""}'
                f'{f"<p class=\"muted\">Coordenadas: {lat:.5f}, {lon:.5f} (WGS84).</p>" if lat else ""}')
        ld = {'@context': 'https://schema.org', '@type': 'LandmarksOrHistoricalBuildings', 'name': s['name'], 'description': desc, 'url': canon,
              'address': {'@type': 'PostalAddress', 'addressLocality': s['municipio'], 'addressRegion': s['distrito'], 'addressCountry': 'PT'}}
        if lat: ld['geo'] = {'@type': 'GeoCoordinates', 'latitude': lat, 'longitude': lon}
        page(f'{OUT}/castro/{sid}/index.html', f'{s["name"]} ({s["municipio"]}) — Castros do Noroeste', desc, body, canon, ld=ld)
        urls.append((canon, URL + ph['f'] if ph else None))
    # --- catalogue, by district and municipality
    by = {}
    for s in sites: by.setdefault(s['distrito'], {}).setdefault(s['municipio'], []).append(s)
    cat = ''.join(f'<h2>Distrito de {E(d)}</h2><div class="dist">' + ''.join(
        f'<section><h3>{E(m)}</h3><ul>' + ''.join(f'<li><a href="../castro/{E(s["id"])}/">{E(s["name"])}</a> <span class="muted">· {E(TYPES.get(s["kind"], s["kind"]))}'
                                                   f'{" · maqueta 3D" if s["id"] in dios else ""}</span></li>' for s in L) + '</ul></section>' for m, L in ms.items()) + '</div>'
        for d, ms in by.items())
    page(f'{OUT}/castros/index.html', 'Catálogo dos castros — Castros do Noroeste', f'Os {len(sites)} sítios do atlas, por distrito e concelho: castros, citânias, cividades, balneários e museus.',
         f'<div class="eyebrow">Catálogo</div><h1>Os {len(sites)} sítios do atlas</h1><p>Por distrito e concelho. Cada ficha liga ao atlas interativo, com o mapa em relevo e, onde existe, a maqueta 3D.</p>{cat}',
         URL + 'castros/')
    # --- credits: the atlas's own statement of sources, the photographs from Commons and the sources of every 3D model
    ext = [(s, x) for s in sites for x in ((F['fic'].get(s['id']) or {}).get('ext') or [])]
    exth = ''.join(f'<li><a href="../castro/{E(s["id"])}/">{E(s["name"])}</a>: {E(x.get("c"))}. {E(x.get("a"))}{", " + E(x.get("y")) if x.get("y") else ""}, '
                   f'{E(x.get("l"))}, <a href="{E(x.get("u"))}" rel="noopener">Wikimedia Commons</a>.</li>' for s, x in ext)
    dioh = ''
    for sid in sorted(dios):
        f = f'app/dio/{sid}.json'
        if not os.path.exists(f): continue
        so = json.load(open(f, encoding='utf-8')).get('sources') or {}; s = next((x for x in sites if x['id'] == sid), None)
        dioh += f'<h3>{E(s["name"] if s else sid)}</h3><ul class="src">' + ''.join(f'<li>{E(v)}</li>' for v in so.values()) + '</ul>'
    page(f'{OUT}/creditos/index.html', 'Créditos, fontes e licenças — Castros do Noroeste', 'Fontes dos textos, das fotografias, da cartografia e das maquetas 3D do atlas dos castros do Noroeste.',
         '<div class="eyebrow">Créditos</div><h1>Fontes e licenças</h1><ul>'
         '<li>Textos de análise, fotografias e diário de campo: © Tiago Pinto. Reprodução só com autorização.</li>'
         '<li>Textos históricos: redigidos a partir das fontes indicadas em cada sítio (SIPA/DGPC, bibliografia científica, municípios e outras entidades; Wikipedia, CC BY-SA, como fonte secundária).</li>'
         '<li>Limites administrativos: CAOP 2024 © DGT; províncias de Espanha: geoBoundaries (CC BY 4.0); rios: HydroRIVERS (WWF/HydroSHEDS).</li>'
         '<li>3D: ortofotos 2021 © DGT; LiDAR 2025 © DGT; elevação Mapzen/AWS Terrain Tiles; edifícios e estruturas © contribuidores do OpenStreetMap (ODbL).</li>'
         '<li>Classificação legal: extraída dos textos da tese e das fontes históricas; confirmar no SIPA/DGPC para efeitos oficiais.</li></ul>'
         f'{"<h2>Fotografias de outros autores</h2><ul class=\"src\">" + exth + "</ul>" if exth else ""}'
         f'<h2>Fontes das maquetas 3D</h2>{dioh}', URL + 'creditos/')
    # --- sitemap and robots
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for u, im in urls: sm.append(f'<url><loc>{u}</loc><lastmod>{today}</lastmod>{f"<image:image><image:loc>{im}</image:loc></image:image>" if im else ""}</url>')
    open(f'{OUT}/sitemap.xml', 'w').write('\n'.join(sm + ['</urlset>']) + '\n')
    open(f'{OUT}/robots.txt', 'w').write(f'User-agent: *\nAllow: /\nSitemap: {URL}sitemap.xml\n')
    return len(urls)
