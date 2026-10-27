import json
# ramparts traced on the orthophoto (inner-image px) → vol.json as k:"rampart"
V=json.load(open('app/t3/vol.json'));R=json.load(open('dig/ramparts.json'))
L=lambda px,py:(px/2048*512-256,py/2048*512-256)
for id,lines in R.items():
    v=V.setdefault(id,{'b':[],'r':[]})
    v['r']=[r for r in v['r'] if not (r.get('src')=='dig' and r['k']=='wall' and not r.get('q'))]
    v['r']=[r for r in v['r'] if r['k']!='rampart']
    for ln in lines: v['r'].append({'k':'rampart','c':int(ln[0]==ln[-1]),'src':'dig','p':[int(round(c*10)) for p in ln for c in L(*p)]})
json.dump(V,open('app/t3/vol.json','w'),separators=(',',':'));print(len(R),'sites with ramparts')
