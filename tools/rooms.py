import cv2,numpy as np,sys,json
# rectangular rooms: spaces enclosed by the traced walls (dig/<id>-walls.json pts), kept when close to a rectangle
# usage: rooms.py id "x,y ..." out.jpg [close_px]
id=sys.argv[1];poly=np.array([[int(v) for v in p.split(',')] for p in sys.argv[2].split()],np.int32);out=sys.argv[3]
cl=int(sys.argv[4]) if len(sys.argv)>4 else 5
im=cv2.imread(f'app/t3/{id}-c.jpg');H,W=im.shape[:2];reg=np.zeros((H,W),np.uint8);cv2.fillPoly(reg,[poly],1)
d=json.load(open(f'dig/{id}-walls.json'))
wm=np.zeros((H,W),np.uint8)
for x,y in d['pts']: wm[y:y+2,x:x+2]=1
wm=cv2.morphologyEx(wm,cv2.MORPH_CLOSE,np.ones((cl,cl),np.uint8))  # bridge gaps in walls
wm=cv2.dilate(wm,np.ones((3,3),np.uint8))
free=((wm==0)&(reg>0)).astype(np.uint8)
n,lab,st,_=cv2.connectedComponentsWithStats(free,connectivity=4)
rooms=[];rings=[(r[0],r[1]) for r in d.get('rings',[])]
for i in range(1,n):
    a=st[i,4]
    if not(130<=a<=2400): continue          # ≈ 8–150 m² at 25 cm/px
    ys,xs=np.nonzero(lab==i);pts=np.c_[xs,ys].astype(np.float32)
    (cx,cy),(w,h),ang=cv2.minAreaRect(pts)
    if w*h==0 or a/(w*h)<0.72 or max(w,h)/max(1,min(w,h))>3.2 or min(w,h)<9: continue
    if any(np.hypot(cx-rx,cy-ry)<12 for rx,ry in rings): continue   # already a round house
    # the room must be walled on most of its outline
    ring=cv2.dilate((lab==i).astype(np.uint8),np.ones((7,7),np.uint8))-(lab==i).astype(np.uint8)
    if wm[ring>0].mean()<0.55: continue
    rooms.append([float(cx),float(cy),float(w+4),float(h+4),float(ang)])   # +4 px: outer face of the walls
vis=im.copy();vis[wm>0]=(vis[wm>0]*.4+np.array([255,0,255])*.6).astype(np.uint8)
for cx,cy,w,h,a in rooms: cv2.polylines(vis,[cv2.boxPoints(((cx,cy),(w,h),a)).astype(np.int32)],True,(0,255,255),2)
cv2.polylines(vis,[poly],True,(0,255,0),2);x0,y0=poly.min(0);x1,y1=poly.max(0);sc=900/max(x1-x0+40,y1-y0+40)
cv2.imwrite(out,cv2.resize(vis[max(0,y0-20):y1+20,max(0,x0-20):x1+20],None,fx=sc,fy=sc),[cv2.IMWRITE_JPEG_QUALITY,85])
d['rooms']=rooms;json.dump(d,open(f'dig/{id}-walls.json','w'))
print(id,'rooms',len(rooms))
