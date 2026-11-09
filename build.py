import re
s=open('app/src.html').read()
mock=open('tests/mock.html').read()   # stand-in for the artifact runtime (window.claude) used by the local test pages
css=open('leaflet.css').read(); css=re.sub(r'/\*.*?\*/','',css,flags=re.S); css=re.sub(r'\n\s*\n','\n',css)
import hashlib,json,os
# short content hash of each 3D model file, appended as ?v= so a new version is never hidden by the browser cache
diov={f:hashlib.md5(open('app/dio/'+f,'rb').read()).hexdigest()[:8] for f in sorted(os.listdir('app/dio')) if f.endswith(('.json','.png'))}
s=s.replace('/*DIOV*/{}',json.dumps(diov,separators=(',',':')))
# 3D viewer data: one file per model in maquetas/ (caption, gaps, layers, camera, guided tour) and the shared light maquetas/luz.json
dios={}
for f in sorted(os.listdir('maquetas')):
    if not f.endswith('.json') or f=='luz.json': continue
    d=json.load(open('maquetas/'+f)); sid=d.pop('id',f[:-5]); assert sid==f[:-5],f
    assert os.path.exists(f'app/dio/{sid}.glb.png') or os.path.exists(f'app/dio/{sid}.glb.txt'),'sem modelo: '+sid
    assert d.get('gaps'),'sem lacunas: '+sid
    for t in d.get('tour',[]): assert set(t)=={'sid','title','text'},(sid,t)
    dios[sid]=d
dios=dict(sorted(dios.items(),key=lambda kv:(kv[1].pop('order',999),kv[0])))   # order of the novelties notice and of the lists
luz={k:v for k,v in json.load(open('maquetas/luz.json')).items() if k!='_'}
js=lambda o:json.dumps(o,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
s=s.replace('/*DIOS*/{}',js(dios)).replace('/*LUZ*/{}',js(luz))
out=s.replace('/*LEAFLET_CSS*/',css); open('app/index.html','w').write(out)
sk='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}[hidden]{display:none!important}</style></head><body>'
open('app/test2.html','w').write(sk+out+'</body></html>');open('app/test.html','w').write(sk+mock+out+'</body></html>')
