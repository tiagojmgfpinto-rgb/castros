import json,sys,numpy as np,cv2;sys.path.insert(0,'blend');import brit_plan as P
from matplotlib.path import Path as MPath
f=json.load(open('blend/brit_fit.json'));mean=np.array(f['mean']);tx,tz,th,k=f['x']
def T(p):
    q=(np.asarray(p,float)-mean)/f['pxm']*k;c,s=np.cos(th),np.sin(th);return np.stack([q[...,0]*c-q[...,1]*s,q[...,0]*s+q[...,1]*c],-1)+[tx,tz]
img=cv2.imread('app/t3/guimaraes-citania-de-briteiros-c.jpg');g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY).astype(np.float32)
# ring walls: dark thin stone ring with light ground inside and around; enhance local darkness
bg=cv2.GaussianBlur(g,(0,0),6);dark=np.clip(bg-g,0,60);dark=cv2.GaussianBlur(dark,(0,0),1.0)
hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV);veg=(hsv[...,1]>70)&(g<85)    # tree canopy
encl=MPath(T(P.R2)*4+1024)
H,W=g.shape;yy,xx=np.mgrid[0:H,0:W]
out=[]
cs=cv2.HoughCircles((dark*4).clip(0,255).astype(np.uint8),cv2.HOUGH_GRADIENT,dp=1,minDist=12,param1=60,param2=11,minRadius=7,maxRadius=14)
cs=[] if cs is None else cs[0]
for X,Y,R in cs:
    if not encl.contains_point((X,Y)):continue
    sl=(slice(int(Y-R*1.7),int(Y+R*1.7)),slice(int(X-R*1.7),int(X+R*1.7)));d=np.hypot(xx[sl]-X,yy[sl]-Y)
    a=g[sl];dk=dark[sl];vg=veg[sl]
    ringd=dk[(d>R*.8)&(d<R*1.2)].mean();innd=dk[d<R*.55].mean();outd=dk[(d>R*1.35)&(d<R*1.7)].mean()
    vin=vg[d<R*1.2].mean()
    # ring must be continuous: fraction of angular bins with a dark rim
    ang=np.arctan2(yy[sl]-Y,xx[sl]-X)[(d>R*.8)&(d<R*1.2)];vals=dk[(d>R*.8)&(d<R*1.2)]
    bins=np.array([vals[(ang>=a0)&(ang<a0+np.pi/6)].mean() if np.any((ang>=a0)&(ang<a0+np.pi/6)) else 0 for a0 in np.arange(-np.pi,np.pi,np.pi/6)])
    cont=(bins>innd+2).mean()
    score=ringd-max(innd,outd)
    if score>2.2 and vin<.35 and cont>=.58: out.append([float(X),float(Y),float(R),round(float(score),1)])
print(len(cs),'->',len(out))
json.dump(out,open('blend/brit_rings.json','w'))
vis=img.copy()
for X,Y,R,s in out: cv2.circle(vis,(int(X),int(Y)),int(R),(255,255,0),2)
cv2.polylines(vis,[(T(P.R1)*4+1024).astype(np.int32)],True,(0,80,255),3)
cv2.imwrite('blend/brit/rings.jpg',cv2.resize(vis[0:1250,350:1300],(950*1,1250*1)))
