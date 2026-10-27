import cv2,numpy as np,sys,json
# rectangular houses from manual seeds: each seed (display x,y,size) is refined with the wall pixels around it
# usage: rects.py id ox oy scale "x,y,s;x,y,s;..." out.jpg
id=sys.argv[1];ox,oy,k=float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4]);out=sys.argv[6]
seeds=[[float(v) for v in t.split(',')] for t in sys.argv[5].split(';') if t.strip()]
im=cv2.imread(f'app/t3/{id}-c.jpg');H,W=im.shape[:2]
d=json.load(open(f'dig/{id}-walls.json'));P=np.array(d['pts'],np.float32).reshape(-1,2)+1
rects=[]
def dom_angle(cx,cy,R):
    # dominant wall direction near the seed (degrees), from a Hough transform of the local wall mask
    sel=P[(np.abs(P[:,0]-cx)<R)&(np.abs(P[:,1]-cy)<R)]
    if len(sel)<8: return None
    m=np.zeros((int(2*R)+3,int(2*R)+3),np.uint8)
    for x,y in sel-[cx-R,cy-R]: m[int(y):int(y)+2,int(x):int(x)+2]=255
    ls=cv2.HoughLines(m,1,np.pi/90,max(8,int(R*.5)))
    return None if ls is None else float(np.degrees(ls[0][0][1]))-90
for x,y,s in seeds:
    cx,cy,half=ox+x/k,oy+y/k,s/k*0.62
    ang=dom_angle(cx,cy,half*2.2)
    sel=P[(np.abs(P[:,0]-cx)<half)&(np.abs(P[:,1]-cy)<half)] if len(P) else np.zeros((0,2),np.float32)
    w,h,rx,ry=s/k*.9,s/k*.75,cx,cy
    if ang is not None and len(sel)>=12:
        # extent of nearby walls measured along the dominant axes
        t=np.radians(ang);u=(sel-[cx,cy])@np.array([np.cos(t),np.sin(t)]);v=(sel-[cx,cy])@np.array([-np.sin(t),np.cos(t)])
        du,dv=np.percentile(u,95)-np.percentile(u,5),np.percentile(v,95)-np.percentile(v,5)
        if 0.4*s/k<=du<=1.5*s/k: w=du
        if 0.4*s/k<=dv<=1.5*s/k: h=dv
        mu,mv=(np.percentile(u,95)+np.percentile(u,5))/2,(np.percentile(v,95)+np.percentile(v,5))/2
        rx,ry=cx+mu*np.cos(t)-mv*np.sin(t),cy+mu*np.sin(t)+mv*np.cos(t)
        if np.hypot(rx-cx,ry-cy)>half*.6: rx,ry=cx,cy
    rects.append([float(rx),float(ry),float(w),float(h),float(ang or 0.0)])
vis=im.copy()
for x,y in P.astype(int): vis[y-1:y+1,x-1:x+1]=(255,0,255)
for cx,cy,w,h,a in rects: cv2.polylines(vis,[cv2.boxPoints(((cx,cy),(w,h),a)).astype(np.int32)],True,(0,255,255),2)
xs=[r[0] for r in rects];ys=[r[1] for r in rects];x0,x1,y0,y1=int(min(xs))-60,int(max(xs))+60,int(min(ys))-60,int(max(ys))+60
sc=900/max(x1-x0,y1-y0);cv2.imwrite(out,cv2.resize(vis[max(0,y0):y1,max(0,x0):x1],None,fx=sc,fy=sc),[cv2.IMWRITE_JPEG_QUALITY,85])
d['rooms']=rects;json.dump(d,open(f'dig/{id}-walls.json','w'))
print(id,'rect houses',len(rects))
