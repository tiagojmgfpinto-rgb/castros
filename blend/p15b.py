import numpy as np,cv2,json
M=None
src=np.array([(428,463),(408,488),(349,469)],float);dst=np.array([(-70.25,-88.5),(-77.75,-75.5),(-103.0,-81.0)],float)
M,_=cv2.estimateAffinePartial2D(src,dst);sc=np.hypot(M[0,0],M[1,0])
im=cv2.imread('blend/brit/plan15.png');hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
g[hsv[...,1]>80]=255                     # drop red/orange annotations
U=4;inv=255-cv2.resize(g,None,fx=U,fy=U,interpolation=cv2.INTER_CUBIC)
best=np.full(inv.shape,-1,np.float32);brad=np.zeros(inv.shape,np.float32)
for r in np.arange(3.8,8.6,.4):
    R=r*U;S=int(R*2+U*4)|1;T=np.zeros((S,S),np.float32);c=S//2
    cv2.circle(T,(c,c),int(round(R)),1.0,int(U*1.5))
    T-=T.mean()   # zero-mean template; interior of ring stays negative => must be blank
    sc_=cv2.matchTemplate(inv,T,cv2.TM_CCOEFF_NORMED)
    pad=S//2;full=np.full(inv.shape,-1,np.float32);full[pad:pad+sc_.shape[0],pad:pad+sc_.shape[1]]=sc_
    m=full>best;best[m]=full[m];brad[m]=r
pk=(best==cv2.dilate(best,np.ones((int(U*6),int(U*6)),np.uint8)))&(best>.42)
ys,xs=np.nonzero(pk);cand=sorted([(best[y,x],x/U,y/U,brad[y,x]) for y,x in zip(ys,xs)],reverse=True)
keep=[]
for s,x,y,r in cand:
    if all(np.hypot(x-k[1],y-k[2])>(r+k[3])*.9 for k in keep):keep.append((s,x,y,r))
print(len(keep));
H=[[*(M[:,:2]@[x,y]+M[:,2]).round(2).tolist(),round(float(r*sc),2),round(float(s),3)] for s,x,y,r in keep]
json.dump(H,open('blend/p15_houses.json','w'))
vis=im.copy()
for s,x,y,r in keep: cv2.circle(vis,(int(round(x)),int(round(y))),int(round(r)),(0,170,0) if s>.5 else (0,120,255),1)
big2=cv2.resize(vis,None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)
cv2.imwrite('blend/brit/p15a.png',big2[2*180:2*560,2*300:2*720]);cv2.imwrite('blend/brit/p15b.png',big2[2*480:2*860,2*380:2*780])
# second pass: angular continuity of the ring at native resolution, inside the walled area
import sys;sys.path.insert(0,'blend');import brit_plan as P
from matplotlib.path import Path as MP
f=json.load(open('blend/brit_fit.json'));mean=np.array(f['mean']);tx,tz,th,k=f['x']
def Tp(p):
    q=(np.asarray(p,float)-mean)/f['pxm']*k;c,s=np.cos(th),np.sin(th);return np.stack([q[...,0]*c-q[...,1]*s,q[...,0]*s+q[...,1]*c],-1)+[tx,tz]
R2=MP(Tp(P.R2));gg=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(float)
yy,xx=np.mgrid[0:gg.shape[0],0:gg.shape[1]];F=[]
for (s,x,y,r),h in zip(keep,H):
    if s<.47 or not R2.contains_point(h[:2]):continue
    x0,x1,y0,y1=int(x-r-3),int(x+r+4),int(y-r-3),int(y+r+4);d=np.hypot(xx[y0:y1,x0:x1]-x,yy[y0:y1,x0:x1]-y);a=gg[y0:y1,x0:x1];ang=np.arctan2(yy[y0:y1,x0:x1]-y,xx[y0:y1,x0:x1]-x)
    ring=(d>r-1.3)&(d<r+1.3);bins=np.array([a[ring&(ang>=q)&(ang<q+np.pi/4)].min() if np.any(ring&(ang>=q)&(ang<q+np.pi/4)) else 255 for q in np.arange(-np.pi,np.pi,np.pi/4)])
    if (bins<175).mean()>=.75 and np.median(a[d<r-2.2])>205:F.append(h+[float(x),float(y)])
print('final',len(F));json.dump(F,open('blend/p15_houses.json','w'))
vis=im.copy()
for h in F: cv2.circle(vis,(int(round(h[4])),int(round(h[5]))),int(round(h[2]/sc)),(0,170,0),1)
big2=cv2.resize(vis,None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)
cv2.imwrite('blend/brit/p15a.png',big2[2*180:2*560,2*300:2*720]);cv2.imwrite('blend/brit/p15b.png',big2[2*480:2*860,2*380:2*780])
