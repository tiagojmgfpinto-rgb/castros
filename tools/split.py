import json
# data.json (source) -> app/data.json (lean index, loads first), app/fichas.json (history texts, stamp art and site records, loaded
# right after; a link to a site waits for it) and app/texts.json (thesis texts + municipal bibliographies, loaded in the background)
d=json.load(open('data.json'));T={'t':{},'b':{}};F={'hist':{},'sa':{},'fic':{}}
for s in d['sites']:
    T['t'][s['id']]=s.pop('text',[])
    for k in F:
        if k in s: F[k][s['id']]=s.pop(k)
for m in d['municipios']: T['b'][m['slug']]=m.pop('bib',[])
for f,o in (('app/data.json',d),('app/fichas.json',F),('app/texts.json',T)): json.dump(o,open(f,'w'),ensure_ascii=False,separators=(',',':'))
import os;print(*[f'{f} {os.path.getsize(f)}' for f in ('app/data.json','app/fichas.json','app/texts.json')])
