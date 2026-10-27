import json,glob,os
# vector walls (dig/<id>-walls.json "vlines") → vol.json as k:"vwall"; drops the old per-sample blocks ("w")
V=json.load(open('app/t3/vol.json'))
L=lambda px,py:(px/2048*512-256,py/2048*512-256)
for f in glob.glob('dig/*-walls.json'):
    id=os.path.basename(f)[:-11];a=json.load(open(f))
    if id not in V or not a.get('vlines'): continue
    v=V[id];v.pop('w',None);v['r']=[r for r in v['r'] if r['k']!='vwall']
    for ln in a['vlines']: v['r'].append({'k':'vwall','c':0,'src':'dig','p':[int(round(c*10)) for p in ln for c in L(*p)]})
    print(id,len(a['vlines']))
json.dump(V,open('app/t3/vol.json','w'),separators=(',',':'))
