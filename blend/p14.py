import numpy as np,cv2,json
src=np.array([(197.5,214.25),(188.75,225.75),(160.75,217.5)],float)     # plan px: RH1, RH2, chapel
dst=np.array([(-70.25,-88.5),(-77.75,-75.5),(-103.0,-81.0)],float)      # local m (x east, z south)
M,_=cv2.estimateAffinePartial2D(src,dst);print(M, 'scale',np.hypot(M[0,0],M[1,0]),'rot',np.degrees(np.arctan2(M[1,0],M[0,0])))
res=(src@M[:,:2].T+M[:,2])-dst;print('res m',np.hypot(*res.T).round(2))
json.dump(M.tolist(),open('blend/p14_M.json','w'))
im=cv2.imread('blend/brit/plan14.png');g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
U=6;big=cv2.resize(g,None,fx=U,fy=U,interpolation=cv2.INTER_CUBIC)
cs=cv2.HoughCircles(cv2.GaussianBlur(255-big,(0,0),1.2),cv2.HOUGH_GRADIENT,dp=1,minDist=U*3.2,param1=60,param2=14,minRadius=int(U*1.7),maxRadius=int(U*3.6))
cs=[] if cs is None else cs[0]
# ring test: darker rim than inside
out=[]
yy,xx=np.mgrid[0:big.shape[0],0:big.shape[1]]
for X,Y,R in cs:
    x0,x1,y0,y1=int(X-R*1.6),int(X+R*1.6)+1,int(Y-R*1.6),int(Y+R*1.6)+1
    if x0<0 or y0<0 or x1>=big.shape[1] or y1>=big.shape[0]:continue
    d=np.hypot(xx[y0:y1,x0:x1]-X,yy[y0:y1,x0:x1]-Y);a=big[y0:y1,x0:x1].astype(float)
    ang=np.arctan2(yy[y0:y1,x0:x1]-Y,xx[y0:y1,x0:x1]-X);ring=(d>R*.8)&(d<R*1.2);inn=d<R*.5
    bins=np.array([a[ring&(ang>=q)&(ang<q+np.pi/4)].min() for q in np.arange(-np.pi,np.pi,np.pi/4)])
    outr=(d>R*1.45)&(d<R*1.75)
    ob=np.array([np.median(a[outr&(ang>=q)&(ang<q+np.pi/4)]) for q in np.arange(-np.pi,np.pi,np.pi/4)])
    if (bins<a[inn].mean()-45).mean()>=1 and a[inn].mean()>215 and (ob>200).mean()>=.62: out.append((X/U,Y/U,R/U))
print(len(cs),len(out))
L=[]
for x,y,r in out:
    q=M[:,:2]@[x,y]+M[:,2];L.append([float(v) for v in [round(q[0],2),round(q[1],2),round(r*np.hypot(M[0,0],M[1,0]),2),round(x,1),round(y,1)]])
json.dump(L,open('blend/p14_circles.json','w'))
vis=cv2.resize(im,None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC)
for x,y,r in out: cv2.circle(vis,(int(x*4),int(y*4)),int(r*4),(0,180,0),2)
cv2.imwrite('blend/brit/p14_det.png',vis[60*4:330*4,140*4:330*4])
