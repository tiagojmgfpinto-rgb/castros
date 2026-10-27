import cv2,numpy as np,sys,json
# thin wall lines: top-hat (bright stone) and/or black-hat (shadowed edge) inside a polygon
# usage: lines.py id "x,y ..." mode(bright|dark|both) pct out.jpg
id=sys.argv[1];poly=np.array([[int(v) for v in p.split(',')] for p in sys.argv[2].split()],np.int32);mode=sys.argv[3];pct=float(sys.argv[4])
MINL=int(sys.argv[6]) if len(sys.argv)>6 else 8
im=cv2.imread(f'app/t3/{id}-c.jpg');H,W=im.shape[:2];reg=np.zeros((H,W),np.uint8);cv2.fillPoly(reg,[poly],1)
L=cv2.cvtColor(im,cv2.COLOR_BGR2LAB)[...,0];S=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)[...,1]
k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9));Lb=cv2.GaussianBlur(L,(3,3),0)
resp=np.zeros((H,W),np.float32)
if mode in('bright','both'): resp=np.maximum(resp,cv2.morphologyEx(Lb,cv2.MORPH_TOPHAT,k).astype(np.float32))
if mode in('dark','both'): resp=np.maximum(resp,cv2.morphologyEx(Lb,cv2.MORPH_BLACKHAT,k).astype(np.float32)*(.8 if mode=='both' else 1))
resp[S>90]=0  # vegetation is saturated
thr=np.percentile(resp[reg>0],100-pct);m=((resp>thr)&(reg>0)).astype(np.uint8)
# keep elongated components (lines), drop specks and blobs
n,lab,st,_=cv2.connectedComponentsWithStats(m,connectivity=8);keep=np.zeros_like(m)
for i in range(1,n):
    x,y,w,h,a=st[i]
    if a<10: continue
    if max(w,h)>=MINL and a/(w*h)<0.55: keep[lab==i]=1
ys,xs=np.nonzero(keep[::2,::2]);pts=np.stack([xs*2,ys*2],1)
vis=im.copy();vis[keep>0]=(255,0,255);cv2.polylines(vis,[poly],True,(0,255,0),2)
x0,y0=poly.min(0);x1,y1=poly.max(0);sc=900/max(x1-x0+40,y1-y0+40)
cv2.imwrite(sys.argv[5],cv2.resize(vis[max(0,y0-20):y1+20,max(0,x0-20):x1+20],None,fx=sc,fy=sc),[cv2.IMWRITE_JPEG_QUALITY,85])
old=json.load(open(f'dig/{id}-walls.json')) if __import__('os').path.exists(f'dig/{id}-walls.json') else {'rings':[]}
json.dump({'pts':pts.tolist(),'rings':old.get('rings',[])},open(f'dig/{id}-walls.json','w'))
print(id,'line px',int(keep.sum()),'samples',len(pts))
