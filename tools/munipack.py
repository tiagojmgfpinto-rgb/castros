import json,re,unicodedata,sys
n=lambda s:unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode()
d=json.load(open('data.json')); res=[r for r in json.load(open('muni.json')) if r.get('text')]
STOP=set('castro de do da dos das o a e povoado fortificado citania cividade museu municipal centro interpretativo nucleo espaco museologico balneario castrejo monte s sao santa santo'.split())
key=lambda s:[w for w in re.findall(r'[a-z]+',n(s)) if w not in STOP and len(w)>2]
out={}
for s in d['sites']:
    ks=key(s['name']) or [n(s['name'])]
    best=[]
    for r in res:
        if r['slug']!=s['slug']: continue
        lines=[p for p in r['text'].split('\n') if len(p)>70 and not re.search(r'cookie|direitos reservados|newsletter|subscrev',p,re.I)]
        dedicated=all(k in n(r['bib']) for k in ks[:2])
        paras=lines if dedicated else [p for p in lines if all(k in n(p) for k in ks[:2])]
        seen=set(); paras=[p for p in paras if not (p in seen or seen.add(p))]
        if paras: best.append({'url':r['url'],'bib':re.sub(r'\[Online\].*','',r['bib']).strip(),'text':'\n'.join(paras)[:2500]})
    if best: out[s['id']]=best
json.dump(out,open('munipack.json','w'),ensure_ascii=False,indent=0)
print(len(out),'sites with municipal excerpts')
if len(sys.argv)>2:
    for s in d['sites'][int(sys.argv[1]):int(sys.argv[2])]:
        if s['id'] not in out: continue
        print('=======',s['id'])
        for b in out[s['id']]: print('--',b['bib'][:120],'|',b['url']); print(re.sub(r'(?im)^.*(acolhe|festival|casa sousa|in the box|carlos eduardo|olaria|conquista|plano estrat|fórum|cookie|browser|newsletter|página oficial).*\n?','',b['text'])[:1100])
