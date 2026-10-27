import cv2,sys
id,x0,y0,w=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]);out=sys.argv[5]
im=cv2.imread(f'app/t3/{id}-c.jpg');c=im[y0:y0+w,x0:x0+w];k=900/w;c=cv2.resize(c,(900,900),interpolation=cv2.INTER_CUBIC)
step=25 if w<=450 else 50
for v in range(0,w+1,step):
    p=int(v*k);col=(0,255,255) if v%100==0 else (0,180,180)
    cv2.line(c,(p,0),(p,899),col,1);cv2.line(c,(0,p),(899,p),col,1)
    if v%50==0:
        cv2.putText(c,str(x0+v),(p+2,12),cv2.FONT_HERSHEY_SIMPLEX,.38,(255,255,255),1);cv2.putText(c,str(y0+v),(2,p+12),cv2.FONT_HERSHEY_SIMPLEX,.38,(255,255,255),1)
cv2.imwrite(out,c,[cv2.IMWRITE_JPEG_QUALITY,88])
