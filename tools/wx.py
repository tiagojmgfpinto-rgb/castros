import json,urllib.request,urllib.parse,sys,time,re,unicodedata
UA={'User-Agent':'CastrosAtlas/1.0 (thesis research app; tiago.pinto@rai.usc.es)'}
n=lambda s:unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode()
cache=json.load(open('wxcache.json')) if __import__('os').path.exists('wxcache.json') else {}
def ext(t):
    if t in cache: return cache[t]
    u='https://pt.wikipedia.org/w/api.php?'+urllib.parse.urlencode({'action':'query','prop':'extracts','explaintext':1,'titles':t,'redirects':1,'format':'json'})
    for i in range(5):
        try:
            r=json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30))
            pg=next(iter(r['query']['pages'].values())); x=pg.get('extract') or ''
            if x: cache[t]=x; json.dump(cache,open('wxcache.json','w'),ensure_ascii=False)
            if x or 'missing' in pg: return x
            time.sleep(4+i*3)
        except Exception: time.sleep(3+i*3)
    return ''
# args: title::keyword1,keyword2 ...
for a in sys.argv[1:]:
    t,_,kw=a.partition('::'); x=ext(t); kws=[n(k) for k in kw.split(',') if k]
    print('#####',t,len(x))
    paras=[p for p in x.split('\n') if p.strip()]
    if kws: paras=[p for p in paras if any(k in n(p) for k in kws)]
    print('\n'.join(paras)[:3500])
