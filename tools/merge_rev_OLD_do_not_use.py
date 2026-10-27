import json,glob
d=json.load(open('data_premuni.json'));R={}
for f in sorted(glob.glob('rev/r*.json')): R.update(json.load(open(f)))
O={'sipa':0,'muni':1,'sci':2,'tese':3,'wiki':4};n=0;nw=0
for s in d['sites']:
    r=R.get(s['id'])
    if not r: continue
    h=s.setdefault('hist',{'p':[],'src':[]}); h['p']=r['p']
    src=[x for x in h.get('src',[]) if not (r.get('drop_wiki') and x['k']=='wiki')]
    urls={x.get('u') for x in src}
    src+= [x for x in r.get('add',[]) if x['u'] not in urls]
    h['src']=sorted(src,key=lambda x:O.get(x['k'],9)); n+=1; nw+=bool(r.get('drop_wiki'))
json.dump(d,open('data.json','w'),ensure_ascii=False,separators=(',',':'))
import shutil; shutil.copy('data.json','app/data.json')
print(n,'sites revised;',nw,'without wikipedia')
