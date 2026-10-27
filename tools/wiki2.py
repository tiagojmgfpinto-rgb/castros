import json,urllib.request,urllib.parse,time,re,html
UA={'User-Agent':'CastrosAtlas/1.0 (thesis research app; tiago.pinto@rai.usc.es)'}
def get(params):
    u='https://pt.wikipedia.org/w/api.php?'+urllib.parse.urlencode({**params,'format':'json'})
    for i in range(5):
        try:
            r=json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30))
            if 'error' not in r: return r
        except Exception: pass
        time.sleep(2+i*2)
    return {}
d=json.load(open('data.json')); out={}
for s in d['sites']:
    c=[]
    for q in [f'intitle:"{s["name"]}"', s['name']+' '+s['municipio']]:
        r=get({'action':'query','list':'search','srsearch':q,'srlimit':5})
        for h in r.get('query',{}).get('search',[]):
            if h['title'] not in [x[0] for x in c]: c.append((h['title'],html.unescape(re.sub(r'<[^>]+>','',h['snippet']))[:160]))
        time.sleep(0.3)
    out[s['id']]=c
    print(s['id'],'|',' || '.join(t for t,_ in c[:6]),flush=True)
json.dump(out,open('wikicand.json','w'),ensure_ascii=False,indent=0)
