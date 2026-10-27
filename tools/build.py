import json,re,sys,urllib.parse,unicodedata
d=json.load(open(sys.argv[1]))
idx={'castros-de-aveiro':'Aveiro','castros-de-braga':'Braga','copia-de-castros-de-braga':'Porto','copia-de-castros-de-viana-do-castelo':'Vila Real','copia-de-castros-do-porto':'Viana do Castelo'}
# verify via headings
dist={}
for k in idx:
    title=[t[1] for t in d[k] if t[0]=='h1'][0]
    D=re.sub(r'.*Distrito d[eo] ','',title); idx[k]=D
    for t in d[k]:
        if t[0]=='a' and t[1].startswith('/'): dist[t[1].strip('/')]=D
dist['lisboa']='Lisboa'
def dms(s):
    s=urllib.parse.unquote_plus(s)
    m=re.findall(r'(\d+)°(\d+)\'([\d.]+)"([NSEW])',s)
    if len(m)!=2:
        m2=re.search(r'!2s(-?\d+\.\d+),\s*(-?\d+\.\d+)',s)
        return [round(float(m2[1]),6),round(float(m2[2]),6)] if m2 else None
    o=[]
    for a,b,c,h in m:
        v=int(a)+int(b)/60+float(c)/3600
        o.append(round(-v if h in 'SW' else v,6))
    return o
def kind(n,sec):
    if sec=='museu': return 'museu'
    l=n.lower()
    if 'balne' in l or 'forno' in l: return 'balneario'
    if 'citânia' in l: return 'citania'
    if 'cividade' in l: return 'cividade'
    if 'castro' in l: return 'castro'
    if 'povoado' in l: return 'povoado'
    return 'outro'
sites=[];munis=[]
for slug,toks in d.items():
    if slug not in dist: continue
    mun=toks[0][1]; sec=None; cur=None; bib=[]
    def close():
        if cur: sites.append(cur)
    for t in toks[1:]:
        if t[0]=='h1':
            h=t[1]
            if h.startswith('Sítios Arqueológicos'): close();cur=None;sec='sitio';continue
            if h=='Espaços Museológicos': close();cur=None;sec='museu';continue
            if h=='Bibliografia': close();cur=None;sec='bib';continue
            close()
            cur={'id':slug+'-'+re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',h.lower()).encode('ascii','ignore').decode()).strip('-'),'name':h,'municipio':mun,'slug':slug,'distrito':dist[slug],'kind':kind(h,sec),'visit':None,'text':[],'ficha':None,'img':None,'coords':None}
        elif sec=='bib':
            if t[0]=='p': bib.append(t[1])
        elif cur:
            if t[0]=='p':
                if re.match(r'Visitad[oa]',t[1]) and not cur['visit']: cur['visit']=re.sub(r'^Visitad[oa] (a|em) ','',t[1])
                else: cur['text'].append(t[1])
            elif t[0]=='a' and 'drive.google' in t[1]: cur['ficha']=t[1]
            elif t[0]=='img' and not cur['img']: cur['img']=t[1]
            elif t[0]=='map': cur['coords']=dms(t[1])
    close()
    munis.append({'slug':slug,'name':mun,'distrito':dist[slug],'bib':bib})
M={'janeiro':1,'fevereiro':2,'março':3,'abril':4,'maio':5,'junho':6,'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12}
for s in sites:
    m=re.match(r'(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})',s['visit'] or '',re.I)
    s['date']=f"{m[3]}-{M[m[2].lower()]:02d}-{int(m[1]):02d}" if m else None
bad=[s['id'] for s in sites if not s['coords']]
print(len(sites),'sites', sum(s['kind']!='museu' for s in sites),'arch', 'nocoords',bad, 'nodate',[s['id'] for s in sites if not s['date']], file=sys.stderr)
import collections;print(collections.Counter(s['kind'] for s in sites),collections.Counter(s['distrito'] for s in sites),file=sys.stderr)
json.dump({'sites':sites,'municipios':munis},open(sys.argv[2],'w'),ensure_ascii=False)
