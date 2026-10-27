import cv2,numpy as np,sys,json
id=sys.argv[1];x0,y0,w=int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4])
im=cv2.imread(f'app/t3/{id}-c.jpg');crop=im[y0:y0+w,x0:x0+w].copy()
g=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY);g=cv2.GaussianBlur(g,(5,5),1.2)
# rings: 4.5–8 m diameter → radius 9–16 px at 25 cm
cs=cv2.HoughCircles(g,cv2.HOUGH_GRADIENT,dp=1,minDist=16,param1=60,param2=14,minRadius=8,maxRadius=16)
cs=[] if cs is None else cs[0]
L=cv2.cvtColor(crop,cv2.COLOR_BGR2LAB)[...,0].astype(float)
keep=[]
for (cx,cy,r) in cs:
    # ring must be lighter than its interior and its outside (stone wall on soil/grass), not a dark blob (tree)
    yy,xx=np.ogrid[:w,:w];d=np.hypot(xx-cx,yy-cy)
    ring=L[(d>r-2.5)&(d<r+2.5)].mean();inn=L[d<r-4].mean();out=L[(d>r+4)&(d<r+9)].mean()
    sd=L[d<r-3].std()
    if abs(inn-out)<9 and abs(ring-inn)>2.5 and inn>out-6 and sd<14: keep.append((float(cx),float(cy),float(r),round(ring-inn,1)))
vis=crop.copy()
for i,(cx,cy,r,c) in enumerate(keep):
    cv2.circle(vis,(int(cx),int(cy)),int(r),(255,0,255),2);cv2.putText(vis,str(i),(int(cx)-6,int(cy)+5),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,255,255),1)
cv2.imwrite(f'dig/{id[:20]}_raw.jpg',crop,[cv2.IMWRITE_JPEG_QUALITY,85]);cv2.imwrite(f'dig/{id[:20]}_det.jpg',vis,[cv2.IMWRITE_JPEG_QUALITY,85])
json.dump({'id':id,'x0':x0,'y0':y0,'c':keep},open(f'dig/{id}.json','w'))
print(len(cs),'candidates',len(keep),'kept')
