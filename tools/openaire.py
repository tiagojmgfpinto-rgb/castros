import json,urllib.request,urllib.parse,unicodedata,re,time,html
n=lambda s:unicodedata.normalize('NFKD',(s or '').lower()).encode('ascii','ignore').decode()
def val(x):
    if isinstance(x,list): x=x[0] if x else None
    if isinstance(x,dict): return x.get('$')
    return x
def search(q):
    u='https://api.openaire.eu/search/publications?'+urllib.parse.urlencode({'keywords':q,'format':'json','size':15})
    for i in range(3):
        try: return json.load(urllib.request.urlopen(u,timeout=60))
        except Exception: time.sleep(3)
    return {}
d=json.load(open('data.json')); out={}
for s in d['sites']:
    core=re.sub(r'^(Castro|Povoado Fortificado|Povoado|Citânia|Cividade|Balneário Castrejo|Museu|Centro Interpretativo|Núcleo Interpretativo)\s+(de |do |da |dos |das |na |a )?','',s['name'],flags=re.I)
    q=f'"{core}" {s["municipio"]}' if s['kind']!='museu' else s['name']
    r=search(q); res=(((r.get('response') or {}).get('results') or {}).get('result')) or []
    if isinstance(res,dict): res=[res]
    keep=[]
    for x in res:
        try: m=x['metadata']['oaf:entity']['oaf:result']
        except Exception: continue
        t=val(m.get('title')); ab=val(m.get('description')) or ''
        ab=html.unescape(re.sub(r'<[^>]+>','',ab))
        if n(core) not in n(t+' '+ab): continue
        cr=m.get('creator'); cr=cr if isinstance(cr,list) else [cr] if cr else []
        auth=[val(c) for c in cr][:4]
        yr=(val(m.get('dateofacceptance')) or '')[:4]
        pid=m.get('pid'); pid=pid if isinstance(pid,list) else [pid] if pid else []
        doi=next((val(p) for p in pid if isinstance(p,dict) and p.get('@classid')=='doi'),None)
        inst=m.get('children',{}).get('instance'); inst=inst if isinstance(inst,list) else [inst] if inst else []
        url=None
        for i in inst:
            w=i.get('webresource') if isinstance(i,dict) else None
            w=w if isinstance(w,list) else [w] if w else []
            for ww in w:
                url=url or val(ww.get('url'))
        keep.append({'title':t,'authors':auth,'year':yr,'doi':doi,'url':('https://doi.org/'+doi) if doi else url,'abstract':ab[:2500]})
        if len(keep)>=4: break
    out[s['id']]=keep
    print(len(keep),s['name'],flush=True)
    time.sleep(0.4)
json.dump(out,open('openaire.json','w'),ensure_ascii=False,indent=0)
