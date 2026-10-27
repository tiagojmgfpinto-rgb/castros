import json
# app/data.json (lean, loads first) + app/texts.json (thesis texts + municipal bibliographies, loaded in the background)
d=json.load(open('data.json'));T={'t':{},'b':{}}
for s in d['sites']: T['t'][s['id']]=s.pop('text',[])
for m in d['municipios']: T['b'][m['slug']]=m.pop('bib',[])
json.dump(d,open('app/data.json','w'),ensure_ascii=False,separators=(',',':'))
json.dump(T,open('app/texts.json','w'),ensure_ascii=False,separators=(',',':'))
import os;print(os.path.getsize('app/data.json'),os.path.getsize('app/texts.json'))
