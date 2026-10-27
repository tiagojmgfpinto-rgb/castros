import json,math,io,os,sys,urllib.request,concurrent.futures as cf
from PIL import Image
D=json.load(open('data.json'));R=6378137
def get(u):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'castros-thesis-app/1.0'}),timeout=180) as r:
                b=r.read()
                if 'image' in r.headers.get('Content-Type',''): return b
                err=Exception(b[:200])
        except Exception as e: err=e
    raise err
def wms(cx,cy,h,px): return Image.open(io.BytesIO(get(f'https://cartografia.dgterritorio.gov.pt/ortos2021/service?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=Ortos2021-RGB&STYLES=&SRS=EPSG:3857&BBOX={cx-h},{cy-h},{cx+h},{cy+h}&WIDTH={px}&HEIGHT={px}&FORMAT=image/png'))).convert('RGB')
def do(s):
    lat,lon=s['coords'];cx=math.radians(lon)*R;cy=math.log(math.tan(math.pi/4+math.radians(lat)/2))*R;k=1/math.cos(math.radians(lat))
    o=f'hd/{s["id"]}.jpg';c=f'hd/{s["id"]}-c.jpg'
    if not os.path.exists(o): wms(cx,cy,1000*k,1536).save(o+'.tmp.jpg',quality=74,optimize=True,progressive=True);os.replace(o+'.tmp.jpg',o)
    if not os.path.exists(c): wms(cx,cy,256*k,2048).save(c+'.tmp.jpg',quality=72,optimize=True,progressive=True);os.replace(c+'.tmp.jpg',c)
    return s['id']
os.makedirs('hd',exist_ok=True)
sites=[s for s in D['sites'] if s.get('t3')];ok=0
with cf.ThreadPoolExecutor(10) as ex:
    for f in cf.as_completed([ex.submit(do,s) for s in sites]):
        try: f.result();ok+=1
        except Exception as e: print('ERR',e,file=sys.stderr)
print(ok,'of',len(sites))
