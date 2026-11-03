"""Monta o site estático (GitHub Pages) em _site/ a partir de app/.

O app/index.html é um fragmento para o artifact do claude.ai (o runtime acrescenta o esqueleto);
aqui junta-se o <!doctype>, as metas e a descrição. Sem window.claude, a app corre só em leitura:
sem comentários, histórico editado nem castros acrescentados pela base de dados do artifact.
Uso: python3 build.py && python3 tools/site.py
"""
import os, shutil

SRC, OUT = 'app', '_site'
SKIP = {'src.html', 'test.html', 'test2.html', 'index.html'}
URL = 'https://tiagojmgfpinto-rgb.github.io/castros/'
DESC = ('Atlas interativo dos castros do Noroeste Peninsular: mapa em relevo, fichas, fontes '
        'e maquetas 3D dos sítios, a partir da tese de doutoramento de Tiago Pinto (USC).')

head = f'''<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{DESC}">
<meta property="og:type" content="website">
<meta property="og:title" content="Castros do Noroeste">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="{URL}maq.jpg">
<link rel="canonical" href="{URL}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='15' fill='%239E6B0C'/%3E%3Ccircle cx='16' cy='16' r='9' fill='none' stroke='%23F5F4EF' stroke-width='2.5'/%3E%3C/svg%3E">
<style>html,body{{margin:0;height:100%}}[hidden]{{display:none!important}}</style>
</head>
<body>
'''

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT, ignore=lambda d, names: [n for n in names if d == SRC and n in SKIP])
app = open(os.path.join(SRC, 'index.html'), encoding='utf-8').read()
with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(head + app + '\n</body>\n</html>\n')
open(os.path.join(OUT, '.nojekyll'), 'w').close()
total = sum(os.path.getsize(os.path.join(r, n)) for r, _, ns in os.walk(OUT) for n in ns)
print(f'{OUT}/: {total/1e6:.0f} MB')
