import json,cv2,numpy as np,os
# 12x12 sprite of 128 px stamp images: aerial (25 cm orthophoto, central ~140 m) for sites with 3D, best photo for the rest
d=json.load(open('data.json'));S=d['sites'];N=128;cols=12
th=cv2.imread('app/thumbs.jpg');TC=d['thumbs']['cols']
out=np.full((N*12,N*cols,3),255,np.uint8);cl=cv2.createCLAHE(clipLimit=2.2,tileGridSize=(4,4))
for i,s in enumerate(S):
    f=f"app/t3/{s['id']}-c.jpg"
    if s['kind']!='museu' and os.path.exists(f):
        im=cv2.imread(f);c=im[1024-280:1024+280,1024-280:1024+280]     # 140 m around the site point
    else:
        c0=s['th']%TC;r0=s['th']//TC;c=th[r0*120:(r0+1)*120,c0*160+20:c0*160+140]
    g=cv2.cvtColor(cv2.resize(c,(N,N),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY);g=cl.apply(g)
    g=cv2.normalize(g,None,0,255,cv2.NORM_MINMAX)
    out[(i//cols)*N:(i//cols+1)*N,(i%cols)*N:(i%cols+1)*N]=cv2.cvtColor(g,cv2.COLOR_GRAY2BGR)
    s['si']=i
cv2.imwrite('app/stamps.jpg',out,[cv2.IMWRITE_JPEG_QUALITY,78])
json.dump(d,open('data.json','w'),ensure_ascii=False,separators=(',',':'))
print(os.path.getsize('app/stamps.jpg'),len(S))
