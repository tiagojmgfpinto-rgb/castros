import numpy as np, math, json
from PIL import Image, ImageDraw, ImageFilter
z=10; x0,x1,y0,y1=481,497,368,389
nx,ny=x1-x0+1,y1-y0+1
M=np.zeros((ny*256,nx*256),dtype=np.float32)
for i,x in enumerate(range(x0,x1+1)):
    for j,y in enumerate(range(y0,y1+1)):
        a=np.asarray(Image.open(f'dem10/{z}_{x}_{y}.png').convert('RGB')).astype(np.float32)
        M[j*256:(j+1)*256,i*256:(i+1)*256]=a[...,0]*256+a[...,1]+a[...,2]/256-32768
n=2**z*256
def px(lon,lat): return ((lon+180)/360*n-x0*256, (1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n-y0*256)
def ll(X,Y): return (X+x0*256)/n*360-180, math.degrees(math.atan(math.sinh(math.pi*(1-2*(Y+y0*256)/n))))
W,N=ll(0,0); E,S=ll(M.shape[1],M.shape[0])
H,Wd=M.shape
# Portugal mask from the same polygons the map draws
mask=Image.new('L',(Wd,H),0); dr=ImageDraw.Draw(mask)
for f in json.load(open('geo/caop_dist.json'))['features']:
    g=f['geometry']; polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
    for poly in polys:
        dr.polygon([px(*p) for p in poly[0]],fill=255)
        for hole in poly[1:]: dr.polygon([px(*p) for p in hole],fill=0)
PT=np.asarray(mask)>127
LAND=(M>0.5)|PT
ES=LAND&~PT
# smooth DEM slightly (separable box blur x2 ~ gaussian)
Z=np.maximum(M,0)
def blur(a,r=1):
    for ax in (0,1):
        a=sum(np.roll(a,k,axis=ax) for k in range(-r,r+1))/(2*r+1)
    return a
Zs=blur(blur(Z))
cell=40075016*math.cos(math.radians((N+S)/2))/n
gy,gx=np.gradient(Zs,cell)
def hs(az,alt,zf):
    az=math.radians(az);alt=math.radians(alt)
    slope=np.arctan(zf*np.hypot(gx,gy)); aspect=np.arctan2(-gx,gy)
    return np.sin(alt)*np.cos(slope)+np.cos(alt)*np.sin(slope)*np.cos(az-aspect)
h=0.55*hs(315,42,1.3)+0.25*hs(275,45,1.3)+0.2*hs(355,55,1.3)
v=(h-math.sin(math.radians(45)))   # ~[-0.7,0.3]
alt=np.clip(Zs/1500,0,1)
def hexrgb(s): return np.array([int(s[i:i+2],16) for i in (1,3,5)],np.float32)
def render(name,sea,land,spain,kdark,klight,altk):
    base=np.empty((H,Wd,3),np.float32); base[:]=hexrgb(sea)
    base[PT]=hexrgb(land); base[ES]=hexrgb(spain)
    f=1+np.where(v<0,v*kdark,v*klight)-alt*altk
    f[~LAND]=1
    out=np.clip(base*f[...,None],0,255).astype(np.uint8)
    im=Image.fromarray(out); im=im.resize((int(Wd*.62),int(H*.62)),Image.LANCZOS)
    im.save(f'app/relief-wide-{name}.jpg','JPEG',quality=74,optimize=True,progressive=True)
render('light','#C3CFCB','#E7E4DA','#D9D8D1',1.15,0.4,0.12)
render('dark','#11181B','#2D322D','#222523',1.05,1.9,-0.4)
json.dump({'bounds':[[S,W],[N,E]]},open('geo/relief_wide_meta.json','w'))
print([[S,W],[N,E]])
