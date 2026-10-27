import numpy as np,cv2,json,sys
from skimage.morphology import skeletonize,remove_small_objects
from skimage.measure import approximate_polygon
sys.path.insert(0,'blend');import brit_plan as P
from matplotlib.path import Path as MP
src=np.array([(428,463),(408,488),(349,469)],float);dst=np.array([(-70.25,-88.5),(-77.75,-75.5),(-103.0,-81.0)],float)
M,_=cv2.estimateAffinePartial2D(src,dst)
f=json.load(open('blend/brit_fit.json'));mean=np.array(f['mean']);tx,tz,th,k=f['x']
def Tp(p):
    q=(np.asarray(p,float)-mean)/f['pxm']*k;c,s=np.cos(th),np.sin(th);return np.stack([q[...,0]*c-q[...,1]*s,q[...,0]*s+q[...,1]*c],-1)+[tx,tz]
Mi=cv2.invertAffineTransform(M);R2px=MP((Tp(P.R2)@Mi[:,:2].T+Mi[:,2]))
im=cv2.imread('blend/brit/plan15.png');hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
U=3;G=cv2.resize(g,None,fx=U,fy=U,interpolation=cv2.INTER_CUBIC);S_=cv2.resize(hsv[...,1],None,fx=U,fy=U)
ink=(G<165)&(S_<70)
# keep strokes at least ~2 native px wide (walls are drawn as filled double lines; contours are hairlines)
# walls are drawn as two parallel lines ~1-2 px apart: close the gap, then keep only strokes thicker than a hairline pair
cl=cv2.morphologyEx(ink.astype(np.uint8),cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)))
op=cv2.morphologyEx(cl,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(6,6)))
# reject dense contour bundles: areas where the closed mask is very wide (>4 native px) are slopes, not walls
wide=cv2.morphologyEx(cl,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(15,15)))
op[cv2.dilate(wide,np.ones((5,5),np.uint8))>0]=0
H=json.load(open('blend/p15_houses.json'))
for h in H: cv2.circle(op,(int(h[4]*U),int(h[5]*U)),int(h[2]/np.hypot(M[0,0],M[1,0])*U+4),0,10)
yy,xx=np.mgrid[0:op.shape[0],0:op.shape[1]]
inside=R2px.contains_points(np.c_[xx.ravel()/U,yy.ravel()/U]).reshape(op.shape)
op=(op>0)&inside;op=remove_small_objects(op,40)
sk=skeletonize(op)
pts=set(zip(*np.nonzero(sk)));nb=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
deg={p:sum((p[0]+a,p[1]+b) in pts for a,b in nb) for p in pts};used=set();lines=[]
def walk(p,q):
    L=[p,q];used.add(frozenset((p,q)))
    while deg[q]==2:
        nx=[(q[0]+a,q[1]+b) for a,b in nb if (q[0]+a,q[1]+b) in pts and frozenset((q,(q[0]+a,q[1]+b))) not in used and (q[0]+a,q[1]+b)!=L[-2]]
        if not nx:break
        n=nx[0];used.add(frozenset((q,n)));L.append(n);q=n
    return L
for p in pts:
    if deg[p]!=2:
        for a,b in nb:
            q=(p[0]+a,p[1]+b)
            if q in pts and frozenset((p,q)) not in used:lines.append(walk(p,q))
W=[]
for L in lines:
    a=np.array(L,float)[:,::-1]/U
    if len(a)<4:continue
    ln=np.sum(np.hypot(*np.diff(a,axis=0).T))*np.hypot(M[0,0],M[1,0])
    if ln<1.6:continue
    poly=approximate_polygon(a,.6);W.append((poly@M[:,:2].T+M[:,2]).round(2).tolist())
print('walls',len(W),'total m',round(sum(np.sum(np.hypot(*np.diff(np.array(w),axis=0).T)) for w in W)))
json.dump(W,open('blend/p15_walls.json','w'))
vis=im.copy();vis=cv2.resize(vis,None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)
for w in W:
    q=((np.array(w)@Mi[:,:2].T+Mi[:,2])*2).astype(np.int32);cv2.polylines(vis,[q],False,(255,0,200),2)
for h in H: cv2.circle(vis,(int(h[4]*2),int(h[5]*2)),int(h[2]/np.hypot(M[0,0],M[1,0])*2),(0,170,0),2)
cv2.imwrite('blend/brit/p15w1.png',vis[2*250:2*500,2*350:2*620]);cv2.imwrite('blend/brit/p15w2.png',vis[2*560:2*780,2*380:2*700])
