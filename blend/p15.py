import numpy as np,cv2,json
from skimage.morphology import skeletonize
from skimage.measure import approximate_polygon
src=np.array([(428,463),(408,488),(349,469)],float)
dst=np.array([(-70.25,-88.5),(-77.75,-75.5),(-103.0,-81.0)],float)
M,_=cv2.estimateAffinePartial2D(src,dst);sc=np.hypot(M[0,0],M[1,0])
res=(src@M[:,:2].T+M[:,2])-dst;print('m/px',round(sc,3),'rot',round(np.degrees(np.arctan2(M[1,0],M[0,0])),1),'res',np.hypot(*res.T).round(2))
im=cv2.imread('blend/brit/plan15.png');hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
ink=((g<150)&(hsv[...,1]<70)).astype(np.uint8)         # black/grey drawing, no red/orange
U=4;big=cv2.resize(g,None,fx=U,fy=U,interpolation=cv2.INTER_CUBIC);inkb=cv2.resize(ink,None,fx=U,fy=U,interpolation=cv2.INTER_NEAREST)
cs=cv2.HoughCircles(cv2.GaussianBlur(255-big,(0,0),1.5),cv2.HOUGH_GRADIENT,dp=1,minDist=U*7,param1=60,param2=16,minRadius=int(U*3.6),maxRadius=int(U*9.5))
cs=[] if cs is None else cs[0]
yy,xx=np.mgrid[0:big.shape[0],0:big.shape[1]];out=[]
for X,Y,R in cs:
    x0,x1,y0,y1=int(X-R*1.7),int(X+R*1.7)+1,int(Y-R*1.7),int(Y+R*1.7)+1
    if x0<0 or y0<0 or x1>=big.shape[1] or y1>=big.shape[0]:continue
    d=np.hypot(xx[y0:y1,x0:x1]-X,yy[y0:y1,x0:x1]-Y);ik=inkb[y0:y1,x0:x1];ang=np.arctan2(yy[y0:y1,x0:x1]-Y,xx[y0:y1,x0:x1]-X)
    ring=(d>R*.82)&(d<R*1.18);inn=d<R*.6
    bins=np.array([ik[ring&(ang>=q)&(ang<q+np.pi/6)].mean() for q in np.arange(-np.pi,np.pi,np.pi/6)])
    cont=(bins>.18).mean();fill=ik[inn].mean()
    if cont>=.66 and fill<.12: out.append((float(X/U),float(Y/U),float(R/U),float(cont)))
out.sort(key=lambda q:-q[3]);keep=[]
for q in out:
    if all(np.hypot(q[0]-k[0],q[1]-k[1])>(q[2]+k[2])*.85 for k in keep):keep.append(q)
print('circles',len(cs),len(out),len(keep))
H=[]
for x,y,r,c in keep:
    p=M[:,:2]@[x,y]+M[:,2];H.append([round(float(p[0]),2),round(float(p[1]),2),round(float(r*sc),2),round(c,2)])
json.dump(H,open('blend/p15_houses.json','w'))
# walls: thick strokes (survive a 2x2 erosion at native res)
th=cv2.erode(ink,np.ones((2,2),np.uint8));th=cv2.dilate(th,np.ones((2,2),np.uint8))
for x,y,r,c in keep: cv2.circle(th,(int(round(x)),int(round(y))),int(round(r))+2,0,4)
sk=skeletonize(th>0)
n,lab=cv2.connectedComponents(sk.astype(np.uint8),connectivity=8)
W=[]
for k in range(1,n):
    ys,xs=np.nonzero(lab==k)
    if len(xs)<6:continue
    pts=np.c_[xs,ys].astype(float)
    # order by projection along principal axis (rough polyline per component)
    c=pts.mean(0);u,s_,vt=np.linalg.svd(pts-c);t=(pts-c)@vt[0];o=np.argsort(t);pp=pts[o]
    if s_[1]>s_[0]*.5 and len(pts)>12:   # branched/curvy: split in chunks along axis
        pass
    poly=approximate_polygon(pp,1.0)
    loc=(poly@M[:,:2].T+M[:,2]).round(2).tolist();W.append(loc)
print('wall comps',len(W))
json.dump(W,open('blend/p15_walls.json','w'))
vis=im.copy()
for x,y,r,c in keep: cv2.circle(vis,(int(x),int(y)),int(r),(0,170,0),1)
vis[sk]=(255,0,200)
big2=cv2.resize(vis,None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)
cv2.imwrite('blend/brit/p15a.png',big2[2*180:2*560,2*300:2*720]);cv2.imwrite('blend/brit/p15b.png',big2[2*480:2*860,2*380:2*780])
