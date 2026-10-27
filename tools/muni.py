import json,re,hashlib,subprocess,os,html
from concurrent.futures import ThreadPoolExecutor
d=json.load(open('data.json'))
INST=re.compile(r'(cm-|municipio|concelho\.|jf-|portoenorte|altominho|geoparque|terracallaeci|visit|valedotua|eixoatlantico|csarmento|atlas\.cm|e-cultura|pportodosmuseus|infopedia|valpacos\.pt|paredesdecoura|turismo\.|aroucanet|alvora-loureda|eiras-mei|patrimoniobarcelense)',re.I)
jobs=[]
for m in d['municipios']:
    for b in m['bib']:
        for u in re.findall(r'https?://\S+?(?=\s*\[|\s|$)',b):
            u=u.rstrip('.,;)')
            if INST.search(u) and 'monumentos' not in u: jobs.append((m['slug'],u,b))
print(len(jobs))
def get(j):
    slug,u,b=j; f='muni/'+hashlib.md5(u.encode()).hexdigest()+'.html'
    if not os.path.exists(f):
        subprocess.run(['curl','-sL','-m','40','-A','Mozilla/5.0 (Windows NT 10.0) Chrome/120','-o',f,u])
    ok=os.path.exists(f) and os.path.getsize(f)>2000
    return {'slug':slug,'url':u,'bib':b,'file':f,'ok':ok}
with ThreadPoolExecutor(12) as ex: res=list(ex.map(get,jobs))
print(sum(r['ok'] for r in res),'ok of',len(res))
for r in res:
    if r['ok']:
        t=open(r['file'],errors='ignore').read()
        t=re.sub(r'<(script|style|nav|header|footer)[^>]*>.*?</\1>','',t,flags=re.S|re.I)
        t=re.sub(r'<br\s*/?>','\n',t); t=re.sub(r'</(p|div|h\d|li)>','\n',t,flags=re.I)
        t=html.unescape(re.sub(r'<[^>]+>','',t))
        r['text']='\n'.join(l.strip() for l in t.split('\n') if len(l.strip())>40)
json.dump(res,open('muni.json','w'),ensure_ascii=False)
