import re,html,sys,json,glob,os,urllib.parse
D=sys.argv[1]
def clean(s):
    s=re.sub(r'<br\s*/?>',' ',s); s=re.sub(r'<[^>]+>','',s); s=html.unescape(s)
    return re.sub(r'\s+',' ',s).strip()
def dms(s):
    s=urllib.parse.unquote_plus(s)
    m=re.findall(r'(\d+)°(\d+)\'([\d.]+)"([NSEW])',s)
    if len(m)!=2: return None
    out=[]
    for d,mi,se,h in m:
        v=int(d)+int(mi)/60+float(se)/3600
        if h in 'SW': v=-v
        out.append(round(v,6))
    return out
def tokens(t):
    t=re.sub(r'<(script|style)[^>]*>.*?</\1>','',t,flags=re.S)
    a=t.find('<main'); 
    if a<0: a=t.find('id="menu-submit"')
    b=t.find('webnode.pt/?utm_source')
    t=t[a:b]
    for m in re.finditer(r'<h1[^>]*>(.*?)</h1>|<h[23][^>]*>(.*?)</h[23]>|<p(?:\s[^>]*)?>(.*?)</p>|<img [^>]*src="([^"]+)"|<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>|<iframe[^>]*src="([^"]+)"',t,flags=re.S):
        h1,h2,p,img,ah,at,ifr=m.groups()
        if h1 is not None: yield ('h1',clean(h1))
        elif h2 is not None: yield ('h2',clean(h2))
        elif p is not None:
            c=clean(p)
            if c: yield ('p',c)
        elif img: yield ('img',html.unescape(img))
        elif ah: yield ('a',html.unescape(ah),clean(at))
        elif ifr: yield ('map',html.unescape(ifr))
res={}
for f in sorted(glob.glob(D+'/*.html')):
    slug=os.path.basename(f)[:-5]
    res[slug]=list(tokens(open(f).read()))
json.dump(res,open(sys.argv[2],'w'),ensure_ascii=False,indent=0)
