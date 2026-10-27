import json,sys,numpy as np;sys.path.insert(0,'blend');from sab_plan import *
from PIL import Image,ImageDraw
f=json.load(open('blend/sab_fit.json'));mean=np.array(f['mean']);K=f['K']
tx,tz,th,k=[float(a) for a in sys.argv[1:5]] if len(sys.argv)>4 else f['x']
def T(p):
    q=(np.array(p,float)-mean)*K*k;c,s=np.cos(th),np.sin(th);return np.stack([q[...,0]*c-q[...,1]*s,q[...,0]*s+q[...,1]*c],-1)+[tx,tz]
im=Image.open('app/t3/guimaraes-castro-de-sabroso-c.jpg').convert('RGB');d=ImageDraw.Draw(im)
px=lambda m:[(1024+a*4,1024+b*4) for a,b in m]
for L in [W_WEST,W_EAST_INNER,W_LOWER,W_EAST_OUTER,W_SE]+W_INNER:d.line(px(T(L)),fill=(255,60,0),width=4)
for x,y,r in HOUSES:
    c=T([x,y]);rr=r*K*k*4;X,Y=1024+c[0]*4,1024+c[1]*4;d.ellipse([X-rr,Y-rr,X+rr,Y+rr],outline=(0,255,255),width=3)
im.crop((500,500,1700,1700)).resize((900,900)).save('blend/ov.jpg')
