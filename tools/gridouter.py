import cv2,sys
# gridded crop of the outer 2 km orthophoto (1536 px) — coordinates in inner-image pixels (2048 = 512 m) for tracing ramparts
id,x0,y0,w,out=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),sys.argv[5]
im=cv2.imread(f'app/t3/{id}.jpg')  # 1536 px = 2000 m; inner px = (outer px - 768)*2048/(1536*0.256) + 1024
f=1536*0.256/2048  # outer px per inner px
ox0=int(768+(x0-1024)*f);oy0=int(768+(y0-1024)*f);ow=int(w*f)
c=im[oy0:oy0+ow,ox0:ox0+ow];c=cv2.resize(c,(900,900),interpolation=cv2.INTER_CUBIC);k=900/w
step=100
for v in range(0,w+1,step):
    p=int(v*k);cv2.line(c,(p,0),(p,899),(0,220,220),1);cv2.line(c,(0,p),(899,p),(0,220,220),1)
    cv2.putText(c,str(x0+v),(p+2,12),cv2.FONT_HERSHEY_SIMPLEX,.38,(255,255,255),1);cv2.putText(c,str(y0+v),(2,p+12),cv2.FONT_HERSHEY_SIMPLEX,.38,(255,255,255),1)
cv2.imwrite(out,c,[cv2.IMWRITE_JPEG_QUALITY,88])
