import json,sys,numpy as np;sys.path.insert(0,'blend');import brit_plan as P
from PIL import Image,ImageDraw
f=json.load(open('blend/brit_fit.json'));mean=np.array(f['mean']);tx,tz,th,k=f['x']
def T(p):
    q=(np.asarray(p,float)-mean)/f['pxm']*k;c,s=np.cos(th),np.sin(th);return np.stack([q[...,0]*c-q[...,1]*s,q[...,0]*s+q[...,1]*c],-1)+[tx,tz]
im=Image.open('app/t3/guimaraes-citania-de-briteiros-c.jpg').convert('RGB');d=ImageDraw.Draw(im)
px=lambda m:[(1024+a*4,1024+b*4) for a,b in m]
for L,c in [(P.R1+[P.R1[0]],(255,60,0)),(P.R2+[P.R2[0]],(255,200,0)),(P.R3,(0,255,0)),(P.R3E,(0,255,0)),(P.R5,(255,0,255))]+[(t,(0,200,255)) for t in P.TRENCH]+[(w,(255,255,255)) for w in P.WAYS]:
    d.line(px(T(L)),fill=c,width=5)
for n,x,y in P.GATES:
    X,Y=px([T([x,y])])[0];d.ellipse([X-9,Y-9,X+9,Y+9],outline=(255,0,0),width=4)
for (x,y) in [P.COUNCIL[:2],P.BATH,P.YOU]:
    X,Y=px([T([x,y])])[0];d.rectangle([X-10,Y-10,X+10,Y+10],outline=(0,0,255),width=4)
v=json.load(open('app/t3/vol.json'))['guimaraes-citania-de-briteiros']
for r in v['r']:
    if r['k']=='wall':
        Pp=np.array(r['p']).reshape(-1,2)/10;d.line(px(Pp),fill=(255,255,120),width=2)
o=json.load(open('osm/mask_sites.json'))['guimaraes-citania-de-briteiros']
for r in o['rl']:
    Pp=np.array(r[1:]).reshape(-1,2);d.line(px(Pp),fill=(160,160,160),width=2)
im.resize((1024,1024)).save('blend/brit/fit.jpg')
