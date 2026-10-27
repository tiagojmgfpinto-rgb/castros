import numpy as np, math, heapq, json
from PIL import Image
z=10; x0,x1,y0,y1=485,492,379,386
nx,ny=x1-x0+1,y1-y0+1
M=np.zeros((ny*256,nx*256),dtype=np.float32)
for i,x in enumerate(range(x0,x1+1)):
    for j,y in enumerate(range(y0,y1+1)):
        a=np.asarray(Image.open(f'dem/{z}_{x}_{y}.png').convert('RGB')).astype(np.float32)
        M[j*256:(j+1)*256,i*256:(i+1)*256]=a[...,0]*256+a[...,1]+a[...,2]/256-32768
def lonlat(px,py):
    n=2**z*256; lon=(x0*256+px)/n*360-180
    lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*(y0*256+py)/n)))); return lon,lat
W,N=lonlat(0,0); E,S=lonlat(M.shape[1],M.shape[0])
print('bounds',S,W,N,E)
# hillshade
lat_c=math.radians((N+S)/2); cell=40075016*math.cos(lat_c)/(2**z*256)
Z=np.maximum(M,0)
gy,gx=np.gradient(Z,cell)
def hs(az,alt,zf=1.6):
    az=math.radians(az);alt=math.radians(alt)
    slope=np.arctan(zf*np.hypot(gx,gy)); aspect=np.arctan2(-gx,gy)
    return np.sin(alt)*np.cos(slope)+np.cos(alt)*np.sin(slope)*np.cos(az-aspect)
h=0.5*hs(315,40)+0.3*hs(270,45)+0.2*hs(350,50)
flat=math.sin(math.radians(45))
shadow=np.clip((flat-h)*1.25,0,1)        # 0 flat -> 1 deep shadow
light=np.clip((h-flat)*1.6,0,1)
land=M>0.5
shadow[~land]=0; light[~land]=0
# elevation tint (altitude as subtle darkening at high ground for depth)
elev=np.clip(Z/1500,0,1)
A=np.clip(shadow*0.85,0,1)
Image.fromarray((np.dstack([np.zeros_like(A),A])*255).astype(np.uint8),'LA').save('geo/shade.png',optimize=True)
Image.fromarray((np.dstack([np.full_like(light,1),light*0.55])*255).astype(np.uint8),'LA').save('geo/light.png',optimize=True)
# elevation as grayscale for hypsometric option
Image.fromarray((np.dstack([np.zeros_like(elev),elev*0.5*land])*255).astype(np.uint8),'LA').save('geo/elev.png',optimize=True)
json.dump({'bounds':[[S,W],[N,E]]},open('geo/relief_meta.json','w'))
np.save('dem/M.npy',M)
