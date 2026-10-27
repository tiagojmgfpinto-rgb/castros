import re
s=open('app/src.html').read()
mock=open('tests/mock.html').read()   # stand-in for the artifact runtime (window.claude) used by the local test pages
css=open('leaflet.css').read(); css=re.sub(r'/\*.*?\*/','',css,flags=re.S); css=re.sub(r'\n\s*\n','\n',css)
out=s.replace('/*LEAFLET_CSS*/',css); open('app/index.html','w').write(out)
sk='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}[hidden]{display:none!important}</style></head><body>'
open('app/test2.html','w').write(sk+out+'</body></html>');open('app/test.html','w').write(sk+mock+out+'</body></html>')
