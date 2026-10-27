import threading,json,math,io,os,sys,urllib.request,concurrent.futures as cf
from PIL import Image
import numpy as np
D=json.load(open('data.json'));R=6378137;HALF=1000;N=129;Z=14
UA={'User-Agent':'castros-thesis-app/1.0'}
def get(u,tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=90) as r: return r.read(),r.headers.get('Content-Type','')
        except Exception as e: err=e
    raise err
def merc(lat,lon): return math.radians(lon)*R, math.log(math.tan(math.pi/4+math.radians(lat)/2))*R
TC={}
def tile(x,y):
    k=(x,y)
    if k not in TC:
        p=f'cache3d/z{Z}_{x}_{y}.png'
        if not os.path.exists(p):
            t=p+f'.{threading.get_ident()}.tmp';open(t,'wb').write(get(f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png')[0]);os.replace(t,p)
        a=np.asarray(Image.open(p).convert('RGB')).astype(np.float64)
        TC[k]=a[:,:,0]*256+a[:,:,1]+a[:,:,2]/256-32768
    return TC[k]
def elev(mx,my):
    W=2*math.pi*R; px=(mx+W/2)/W*(256<<Z)-.5; py=(W/2-my)/W*(256<<Z)-.5
    x0=math.floor(px);y0=math.floor(py);fx=px-x0;fy=py-y0
    def v(X,Y): return tile(X>>8,Y>>8)[Y&255,X&255]
    return (v(x0,y0)*(1-fx)+v(x0+1,y0)*fx)*(1-fy)+(v(x0,y0+1)*(1-fx)+v(x0+1,y0+1)*fx)*fy
def do(s):
    lat,lon=s['coords'];cx,cy=merc(lat,lon);h=HALF/math.cos(math.radians(lat))
    oj=f'app/t3/{s["id"]}.jpg';dp=f'app/t3/{s["id"]}.png'
    if not os.path.exists(oj):
        b,ct=get(f'https://cartografia.dgterritorio.gov.pt/ortos2021/service?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=Ortos2021-RGB&STYLES=&SRS=EPSG:3857&BBOX={cx-h},{cy-h},{cx+h},{cy+h}&WIDTH=1024&HEIGHT=1024&FORMAT=image/png')
        if 'image' not in ct: raise Exception('ortho '+b[:200].decode('latin1'))
        Image.open(io.BytesIO(b)).convert('RGB').save(oj,quality=76,optimize=True,progressive=True)
    H=np.zeros((N,N))
    for j in range(N):
        for i in range(N):
            H[j,i]=elev(cx-h+2*h*i/(N-1), cy+h-2*h*j/(N-1))
    v=np.clip(np.round((H+100)*10),0,65535).astype(np.uint32)
    rgb=np.stack([(v>>8)&255,v&255,np.zeros_like(v)],-1).astype(np.uint8)
    Image.fromarray(rgb,'RGB').save(dp,optimize=True)
    c=H[N//2,N//2]
    return s['id'],round(float(H.min())),round(float(H.max())),round(float(c))
sites=[s for s in D['sites'] if s['kind']!='museu' and s.get('coords')]
# tiles first sequentially-safe via threads per site
out={}
with cf.ThreadPoolExecutor(6) as ex:
    for f in cf.as_completed([ex.submit(do,s) for s in sites]):
        try: i,a,b,c=f.result(); out[i]=[a,b,c]
        except Exception as e: print('ERR',e,file=sys.stderr)
json.dump(out,open('t3meta.json','w'))
print(len(out),'of',len(sites))
