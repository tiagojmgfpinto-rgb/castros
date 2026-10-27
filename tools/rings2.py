import cv2,numpy as np,sys,json
# round houses: circle fits on top-hat/black-hat masks at several sensitivities, merged with manual marks
id=sys.argv[1];poly=np.array([[int(v) for v in p.split(',')] for p in sys.argv[2].split()],np.int32);out=sys.argv[3]
im=cv2.imread(f'app/t3/{id}-c.jpg');H,W=im.shape[:2];reg=np.zeros((H,W),np.uint8);cv2.fillPoly(reg,[poly],1)
L=cv2.GaussianBlur(cv2.cvtColor(im,cv2.COLOR_BGR2LAB)[...,0],(3,3),0);S=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)[...,1]
k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9))
R={'bright':cv2.morphologyEx(L,cv2.MORPH_TOPHAT,k).astype(np.float32),'dark':cv2.morphologyEx(L,cv2.MORPH_BLACKHAT,k).astype(np.float32)}
for r in R.values(): r[S>90]=0
def fits(m):
    o=[];n,lab,st,_=cv2.connectedComponentsWithStats(cv2.dilate(m,np.ones((3,3),np.uint8)))
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if not(12<=w<=46 and 12<=h<=46) or a<20: continue
        ys,xs=np.nonzero(lab[y:y+h,x:x+w]==i);xs=xs+x;ys=ys+y
        cx,cy,c=np.linalg.lstsq(np.c_[2*xs,2*ys,np.ones(len(xs))],xs**2+ys**2,rcond=None)[0];r=np.sqrt(max(c+cx*cx+cy*cy,0))
        if 7<=r<=16 and reg[int(min(H-1,max(0,cy))),int(min(W-1,max(0,cx)))] and np.abs(np.hypot(xs-cx,ys-cy)-r).mean()<2.2 and np.unique((np.degrees(np.arctan2(ys-cy,xs-cx))//20).astype(int)).size>=10: o.append([float(cx),float(cy),float(r)])
    return o
med=np.median(L[reg>0])
def bright_in(cx,cy,r):
    yy,xx=np.ogrid[:H,:W];d=np.hypot(xx-cx,yy-cy);return L[d<r*.7].mean()>med-6 and S[d<r*.7].mean()<85
rings=[]
man=json.load(open('dig/manual.json')).get(id)
if man: rings=[[man['x0']+px/man['k'],man['y0']+py/man['k'],man['r']/man['k']] for px,py in man['pts']]
for mode,resp in R.items():
    for pct in (6,9,12,16,20):
        thr=np.percentile(resp[reg>0],100-pct);m=((resp>thr)&(reg>0)).astype(np.uint8)
        for r in fits(m):
            if bright_in(*r) and all(np.hypot(r[0]-q[0],r[1]-q[1])>max(r[2],q[2])*.9 for q in rings): rings.append(r)
vis=im.copy();[cv2.circle(vis,(int(round(a)),int(round(b))),int(round(c)),(0,255,255),2) for a,b,c in rings];cv2.polylines(vis,[poly],True,(0,255,0),2)
x0,y0=poly.min(0);x1,y1=poly.max(0);sc=900/max(x1-x0+40,y1-y0+40)
cv2.imwrite(out,cv2.resize(vis[max(0,y0-20):y1+20,max(0,x0-20):x1+20],None,fx=sc,fy=sc),[cv2.IMWRITE_JPEG_QUALITY,85])
d=json.load(open(f'dig/{id}-walls.json'));d['rings']=rings;json.dump(d,open(f'dig/{id}-walls.json','w'))
print(id,'rings',len(rings),'manual',len(man['pts']) if man else 0)
