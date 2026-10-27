import cv2,numpy as np,sys,json
# usage: walls.py id "x,y x,y ..." vthr [out]  — wall pixels from bright, unsaturated stone; rings by circle fitting
id=sys.argv[1];poly=np.array([[int(v) for v in p.split(',')] for p in sys.argv[2].split()],np.int32);vt=float(sys.argv[3])
MODE=sys.argv[5] if len(sys.argv)>5 else 'bright'
im=cv2.imread(f'app/t3/{id}-c.jpg');H,W=im.shape[:2]
reg=np.zeros((H,W),np.uint8);cv2.fillPoly(reg,[poly],1)
hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV).astype(float);V=hsv[...,2];S=hsv[...,1];bg=cv2.blur(V,(31,31))
def mask(t):
    m=(((V>bg+t) if MODE=='bright' else (np.abs(V-bg)>t))&(S<80)&(reg>0)).astype(np.uint8)
    wide=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((9,9),np.uint8))
    m=m&(1-cv2.dilate(wide,np.ones((5,5),np.uint8)));m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(m);k=np.zeros_like(m)
    for i in range(1,n):
        if st[i,4]>=14: k[lab==i]=1
    return k
def rings_of(k,minang):
    out=[];n,lab,st,_=cv2.connectedComponentsWithStats(cv2.dilate(k,np.ones((3,3),np.uint8)))
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if not(12<=w<=44 and 12<=h<=44) or a<22: continue
        ys,xs=np.nonzero(lab[y:y+h,x:x+w]==i);xs=xs+x;ys=ys+y
        cx,cy,c=np.linalg.lstsq(np.c_[2*xs,2*ys,np.ones(len(xs))],xs**2+ys**2,rcond=None)[0];r=np.sqrt(max(c+cx*cx+cy*cy,0))
        if not(7<=r<=18): continue
        if np.abs(np.hypot(xs-cx,ys-cy)-r).mean()<2.4 and np.unique((np.degrees(np.arctan2(ys-cy,xs-cx))//20).astype(int)).size>=minang: out.append([float(cx),float(cy),float(r)])
    return out
keep=mask(vt);rings=[]
for t in (10,13,16,20,25,30):
    for r in rings_of(mask(t),10):
        if all(np.hypot(r[0]-q[0],r[1]-q[1])>max(r[2],q[2])*.8 for q in rings): rings.append(r)
ys,xs=np.nonzero(keep[::2,::2]);pts=np.stack([xs*2,ys*2],1)
vis=im.copy();vis[keep>0]=(255,0,255)
for cx,cy,r in rings: cv2.circle(vis,(int(round(cx)),int(round(cy))),int(round(r)),(0,255,255),2)
cv2.polylines(vis,[poly],True,(0,255,0),2);x0,y0=poly.min(0);x1,y1=poly.max(0);sc=900/max(x1-x0+40,y1-y0+40)
cv2.imwrite(sys.argv[4] if len(sys.argv)>4 else 'dig/walls.jpg',cv2.resize(vis[max(0,y0-20):y1+20,max(0,x0-20):x1+20],None,fx=sc,fy=sc),[cv2.IMWRITE_JPEG_QUALITY,85])
json.dump({'pts':pts.tolist(),'rings':rings},open(f'dig/{id}-walls.json','w'))
print('wall px',int(keep.sum()),'samples',len(pts),'rings',len(rings))
