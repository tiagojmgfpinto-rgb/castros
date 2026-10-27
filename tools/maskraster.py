import json
from PIL import Image,ImageDraw
# no-tree masks per site: water, waterways, roads, buildings — outer (2 km, 7.8 m/px) and inner (512 m, 2 m/px), packed in one sprite
M=json.load(open('osm/mask_sites.json'));V=json.load(open('app/t3/vol.json'));d=json.load(open('data.json'))
ids=[s['id'] for s in d['sites'] if s.get('t3')];N=256;cols=10;rows=(len(ids)+cols-1)//cols
spr=Image.new('L',(cols*N*2,rows*N),0)
def draw(o,b,half,img):
    sc=N/(2*half);T=lambda x,z:((x+half)*sc,(z+half)*sc);dr=ImageDraw.Draw(img)
    for p in o['wp']:
        pts=[T(p[i],p[i+1]) for i in range(0,len(p),2)]
        if len(pts)>2: dr.polygon(pts,fill=255)
    for l in o['wl']+o['rl']:
        w=l[0];pts=[T(l[i],l[i+1]) for i in range(1,len(l),2)]
        dr.line(pts,fill=255,width=max(1,round(w*sc)),joint='curve')
    for x in b:   # buildings: [h, x,z (×10)...]
        pts=[T(x[i]/10,x[i+1]/10) for i in range(1,len(x),2)]
        if len(pts)>2: dr.polygon(pts,fill=255)
for k,id in enumerate(ids):
    o=M.get(id,{'wp':[],'wl':[],'rl':[]});b=(V.get(id) or {}).get('b',[])
    for j,half in enumerate((1000,256)):
        img=Image.new('L',(N,N),0);draw(o,b,half,img)
        spr.paste(img,((k%cols)*2*N+j*N,(k//cols)*N))
    for s in d['sites']:
        if s['id']==id: s['mk']=k
spr.convert('1').save('app/t3/nomask.png',optimize=True)
json.dump(d,open('data.json','w'),ensure_ascii=False,separators=(',',':'))
import os;print(os.path.getsize('app/t3/nomask.png'),spr.size)
