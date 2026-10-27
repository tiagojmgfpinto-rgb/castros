import json,urllib.request,urllib.parse,unicodedata,re,time
UA={'User-Agent':'CastrosAtlas/1.0 (thesis research app; tiago.pinto@rai.usc.es)'}
def get(params):
    u='https://pt.wikipedia.org/w/api.php?'+urllib.parse.urlencode({**params,'format':'json'})
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30))
        except Exception as e: time.sleep(2)
    return {}
n=lambda s:unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode()
STOP=set('castro de do da dos das o a e povoado fortificado citania cividade museu municipal centro interpretativo nucleo espaco museologico balneario castrejo monte s sao santa santo'.split())
def key(s): return [w for w in re.findall(r'[a-z]+',n(s)) if w not in STOP and len(w)>2]
d=json.load(open('data.json')); out={}
for s in d['sites']:
    ks=key(s['name'])
    best=None
    for q in [s['name']+' '+s['municipio'], s['name']]:
        r=get({'action':'query','list':'search','srsearch':q,'srlimit':5})
        for h in r.get('query',{}).get('search',[]):
            tk=key(h['title'])
            if ks and all(k in tk or k in n(h['title']) for k in ks):
                best=h['title'];break
            if not ks and n(s['name'])==n(h['title']): best=h['title'];break
        if best: break
    if best:
        r=get({'action':'query','prop':'extracts','explaintext':1,'titles':best,'redirects':1})
        pg=next(iter(r.get('query',{}).get('pages',{}).values()),{})
        out[s['id']]={'title':best,'text':(pg.get('extract') or '')[:9000]}
    print(('OK  ' if best else '--  ')+s['name']+(' -> '+best if best else ''),flush=True)
json.dump(out,open('wiki.json','w'),ensure_ascii=False,indent=0)
print(len(out))
