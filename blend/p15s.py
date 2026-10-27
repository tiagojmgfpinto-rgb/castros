import numpy as np,cv2,json
LB={1:(555,200),2:(645,278),3:(428,295),4:(312,513),5:(378,469),6:(487,422),7:(527,355),8:(550,553),9:(668,432),10:(705,604),11:(650,698),12:(446,689),13:(342,799),14:(230,898),15:(394,854),16:(592,776)}
im=cv2.imread('blend/brit/plan15.png');hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
red=(((hsv[...,0]<14)|(hsv[...,0]>160))&(hsv[...,1]>28)&(hsv[...,2]>100)).astype(np.uint8)
# remove the sector label glyphs themselves (they are red too)
for k,(x,y) in LB.items(): cv2.rectangle(red,(x-22,y-14),(x+22,y+14),0,-1)
bar=cv2.dilate(red,np.ones((5,5),np.uint8))
n,lab=cv2.connectedComponents((1-bar).astype(np.uint8),connectivity=4)
comp={}
for k,(x,y) in LB.items(): comp.setdefault(int(lab[y,x]),[]).append(k)
yy,xx=np.mgrid[0:lab.shape[0],0:lab.shape[1]];S=np.zeros(lab.shape,np.int16)
pts=np.array(list(LB.values()),float);keys=np.array(list(LB.keys()))
d=np.stack([np.hypot(xx-x,yy-y) for x,y in pts],0);near=keys[np.argmin(d,0)]
S[:]=near
for c,ks in comp.items():
    m=lab==c
    if len(ks)==1: S[m]=ks[0]
    else:
        sub=np.stack([np.hypot(xx[m]-LB[k][0],yy[m]-LB[k][1]) for k in ks],0);S[m]=np.array(ks)[np.argmin(sub,0)]
S=cv2.medianBlur(S.astype(np.uint8),5)
np.save('blend/p15_sectors.npy',S);print({c:ks for c,ks in comp.items() if len(ks)>1})
col=(np.array([[hash(str(k))%200+40,(k*67)%200+40,(k*131)%200+40] for k in range(17)],np.uint8))
v=(col[S]*.5+im*.5).astype(np.uint8);cv2.imwrite('blend/brit/sectors.png',v[120:960,160:780])
