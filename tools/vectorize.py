import cv2,numpy as np,json,sys
from skimage.morphology import skeletonize
# wall pixel samples (dig/<id>-walls.json "pts", inner-image px) → continuous wall polylines
# usage: vectorize.py id [preview.jpg]
id=sys.argv[1]
d=json.load(open(f'dig/{id}-walls.json'));P=np.array(d['pts'],int).reshape(-1,2)
H=W=2048;m=np.zeros((H,W),np.uint8)
for x,y in P: m[y:y+2,x:x+2]=1
m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))  # join broken stretches
sk=skeletonize(m>0).astype(np.uint8)
# trace skeleton into polylines: walk from endpoints/junctions along 8-connected pixels
nb=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
deg=cv2.filter2D(sk,-1,np.ones((3,3),np.float32),borderType=cv2.BORDER_CONSTANT)*sk-sk
seen=np.zeros_like(sk);lines=[]
ys,xs=np.nonzero(sk)
starts=[(y,x) for y,x in zip(ys,xs) if deg[y,x]!=2]+[(y,x) for y,x in zip(ys,xs)]
for y0,x0 in starts:
    if seen[y0,x0] and deg[y0,x0]==2: continue
    for dy,dx in nb:
        y,x=y0+dy,x0+dx
        if not(0<=y<H and 0<=x<W) or not sk[y,x] or seen[y,x]: continue
        path=[(x0,y0),(x,y)];seen[y,x]=1;py,px=y0,x0
        while deg[y,x]==2:
            nxt=None
            for ey,ex in nb:
                yy,xx=y+ey,x+ex
                if (yy,xx)!=(py,px) and 0<=yy<H and 0<=xx<W and sk[yy,xx] and not seen[yy,xx]: nxt=(yy,xx);break
            if nxt is None: break
            py,px=y,x;y,x=nxt;seen[y,x]=1;path.append((x,y))
        lines.append(path)
    seen[y0,x0]=1
out=[]
for pth in lines:
    a=np.array(pth,np.float32).reshape(-1,1,2)
    L=cv2.arcLength(a,False)
    if L<6: continue                      # < 1.5 m: specks
    s=cv2.approxPolyDP(a,1.2,False).reshape(-1,2)
    out.append([[round(float(x),1),round(float(y),1)] for x,y in s])
d['vlines']=out;json.dump(d,open(f'dig/{id}-walls.json','w'))
tot=sum(cv2.arcLength(np.array(l,np.float32).reshape(-1,1,2),False) for l in out)*.25
print(id,'polylines',len(out),'length m',round(tot))
if len(sys.argv)>2:
    im=cv2.imread(f'app/t3/{id}-c.jpg')
    for l in out: cv2.polylines(im,[np.array(l,np.int32)],False,(255,0,255),2)
    ys,xs=P[:,1],P[:,0];x0,x1,y0,y1=xs.min()-30,xs.max()+30,ys.min()-30,ys.max()+30;sc=900/max(x1-x0,y1-y0)
    cv2.imwrite(sys.argv[2],cv2.resize(im[max(0,y0):y1,max(0,x0):x1],None,fx=sc,fy=sc),[cv2.IMWRITE_JPEG_QUALITY,85])
