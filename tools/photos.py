import re,json,glob,os,html
d=json.load(open('data.json'))
byname={(s['slug'],s['name']):s for s in d['sites']}
out={};orphans=0
for f in glob.glob('site/*.html'):
    slug=os.path.basename(f)[:-5]
    if slug=='outros': continue
    t=open(f).read(); t=re.sub(r'<script[^>]*>.*?</script>','',t,flags=re.S)
    cur=None
    for m in re.finditer(r'<h1[^>]*>(.*?)</h1>|data-content="(\{[^"]*&quot;items&quot;[^"]*\})"|<img [^>]*id="wnd_ImageBlock[^>]*src="([^"]+)"',t,flags=re.S):
        if m.group(1) is not None:
            h=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',m.group(1)))).strip()
            cur=byname.get((slug,h)); continue
        items=[]
        if m.group(2):
            g=json.loads(html.unescape(m.group(2)))
            for it in g.get('items',[]):
                jp=[s for s in it.get('sources',[]) if s['mimeType']!='image/webp']
                sz=sorted(jp[0]['sizes'],key=lambda x:x['width']) if jp else []
                pick=next((x for x in sz if x['width']>=1000),sz[-1] if sz else None)
                src=(pick or {}).get('src') or it['img']['src']
                items.append({'u':src.split('?')[0],'cap':(it.get('title') or it.get('alt') or '').strip(),'w':it['size']['width'],'h':it['size']['height']})
        else:
            items.append({'u':html.unescape(m.group(3)).split('?')[0],'cap':'','w':0,'h':0})
        if not cur: orphans+=len(items); continue
        L=out.setdefault(cur['id'],[])
        for it in items:
            if it['u'] not in [x['u'] for x in L]: L.append(it)
json.dump(out,open('photos.json','w'),ensure_ascii=False,indent=0)
n=sum(len(v) for v in out.values()); print(len(out),'sites with photos;',n,'photos; orphans',orphans)
miss=[s['name']+' ('+s['municipio']+')' for s in d['sites'] if s['id'] not in out]; print('without photos:',len(miss),miss)
print('captions:',[p['cap'] for v in out.values() for p in v if p['cap']][:15])
