import json,math,numpy as np
from PIL import Image,ImageDraw,ImageFilter
from pyproj import Transformer
# NW Iberia relief "maqueta": hypsometric + hillshade texture and a height grid, both on a regular PT-TM06 (EPSG:3763) grid
FWD=Transformer.from_crs(4326,3763,always_xy=True);INV=Transformer.from_crs(3763,4326,always_xy=True)
LON0,LON1,LAT0,LAT1=-9.85,-5.55,39.85,44.0
xs,ys=FWD.transform([LON0,LON1,LON0,LON1,(LON0+LON1)/2,(LON0+LON1)/2],[LAT0,LAT0,LAT1,LAT1,LAT0,LAT1])
X0,X1,Y0,Y1=min(xs),max(xs),min(ys),max(ys)
RES=75.0;W=int((X1-X0)/RES);H=int((Y1-Y0)/RES)
print('grid',W,H,X0,X1,Y0,Y1)
# --- DEM mosaic (terrarium z10, web mercator), incl. bathymetry
gx=X0+(np.arange(W)+.5)*RES;gy=Y1-(np.arange(H)+.5)*RES
GX,GY=np.meshgrid(gx,gy)
LON,LAT=INV.transform(GX,GY)
def mosaic(z,tx0,tx1,ty0,ty1,d):
    M=np.zeros(((ty1-ty0+1)*256,(tx1-tx0+1)*256),np.float32)
    for i,x in enumerate(range(tx0,tx1+1)):
        for j,y in enumerate(range(ty0,ty1+1)):
            a=np.asarray(Image.open(f'{d}/{z}_{x}_{y}.png').convert('RGB')).astype(np.float32)
            M[j*256:(j+1)*256,i*256:(i+1)*256]=a[...,0]*256+a[...,1]+a[...,2]/256-32768
    n=2**z*256;px=(LON+180)/360*n-tx0*256-.5;py=(1-np.arcsinh(np.tan(np.radians(LAT)))/math.pi)/2*n-ty0*256-.5
    x0=np.clip(np.floor(px).astype(int),0,M.shape[1]-2);y0=np.clip(np.floor(py).astype(int),0,M.shape[0]-2);fx=(px-x0).astype(np.float32);fy=(py-y0).astype(np.float32)
    return (M[y0,x0]*(1-fx)+M[y0,x0+1]*fx)*(1-fy)+(M[y0+1,x0]*(1-fx)+M[y0+1,x0+1]*fx)*fy
Z=mosaic(11,962,995,736,779,'dem11')          # land detail (z11 has no deep-sea bathymetry)
Z10=mosaic(10,481,497,368,389,'dem10')        # bathymetry
Z=np.where(Z>0.5,Z,np.minimum(Z,Z10)).astype(np.float32);del Z10
LON=LAT=px=py=M=None
del M,LON,LAT,px,py
def T(lon,lat):
    x,y=FWD.transform(lon,lat);return ((np.asarray(x)-X0)/RES,(Y1-np.asarray(y))/RES)
def polys(f):
    g=f['geometry'];return g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
def raster(features,keep=lambda p:True):
    m=Image.new('L',(W,H),0);dr=ImageDraw.Draw(m)
    for f in features:
        if not keep(f['properties']): continue
        for poly in polys(f):
            ring=np.array(poly[0]);u,v=T(ring[:,0],ring[:,1]);dr.polygon(list(zip(u,v)),fill=255)
            for hole in poly[1:]:
                r=np.array(hole);u,v=T(r[:,0],r[:,1]);dr.polygon(list(zip(u,v)),fill=0)
    return np.asarray(m)>127
PTD=json.load(open('geo/caop_dist.json'))['features'];ESA=json.load(open('geo/geoBoundaries-ESP-ADM1_simplified.geojson'))['features'];ESP=json.load(open('geo/geoBoundaries-ESP-ADM2_simplified.geojson'))['features']
NWD={'Viana do Castelo','Braga','Porto','Vila Real','Bragança','Aveiro','Viseu','Guarda','Coimbra'}
PT=raster(PTD);ES=raster(ESA)
NW=raster(PTD,lambda p:p['dist'] in NWD)|raster(ESA,lambda p:p['shapeName']=='Galicia')
LAND=PT|ES|(Z>2)
# --- shading
Zl=np.where(LAND,np.maximum(Z,0),Z)
def blur(a,r=1):
    # box blur with edge padding (np.roll would wrap the east coast onto the open sea)
    for ax in (0,1):
        p=[(0,0),(0,0)];p[ax]=(r,r);b=np.pad(a,p,mode='edge');n=a.shape[ax]
        a=sum(np.take(b,range(k,k+n),axis=ax) for k in range(2*r+1))/(2*r+1)
    return a
Zs=blur(Zl,1)
gyy,gxx=np.gradient(Zs,RES)
def hs(az,alt,zf):
    az=math.radians(az);alt=math.radians(alt);sl=np.arctan(zf*np.hypot(gxx,gyy));asp=np.arctan2(-gxx,gyy)
    return np.sin(alt)*np.cos(sl)+np.cos(alt)*np.sin(sl)*np.cos(az-asp)
shade=.62*hs(315,35,1.5)+.23*hs(280,50,1.5)+.15*hs(0,65,1.5)
sh=np.clip((shade-.72)*1.35+1,0.45,1.18)
# soft valley darkening (large-scale relief contrast)
Zb_=Zs.copy()
for _ in range(3): Zb_=blur(Zb_,12)
sh=sh*np.clip(1+(Zs-Zb_)/900,.82,1.12)
# --- hypsometric palette (metres -> rgb)
stops=[(0,(178,190,128)),(150,(198,200,140)),(350,(218,208,150)),(600,(222,196,136)),(900,(206,168,112)),(1250,(178,136,92)),(1650,(146,108,78)),(2100,(170,150,130))]
def ramp(v,st):
    v=np.asarray(v);out=np.zeros(v.shape+(3,),np.float32)
    for (a,ca),(b,cb) in zip(st[:-1],st[1:]):
        t=np.clip((v-a)/(b-a),0,1)[...,None];m=((v>=a)&(v<b))[...,None] if b!=st[-1][0] else (v>=a)[...,None]
        out=np.where(m,np.array(ca)*(1-t)+np.array(cb)*t,out)
    out=np.where((v<st[0][0])[...,None],np.array(st[0][1]),out);out=np.where((v>=st[-1][0])[...,None],np.array(st[-1][1]),out)
    return out
land=ramp(np.maximum(Zs,0),stops)
grey=np.dot(land,[.3,.5,.2])[...,None]*np.ones(3)*.62+np.array([92,92,90])
col=np.where(NW[...,None],land,grey*.9+land*.1)
col=np.where(NW[...,None],col*sh[...,None],col*(sh[...,None]**.55))
# sea: depth-tinted with light underwater shading
Zb=np.where(LAND,0,np.minimum(Z,0)).astype(np.float32)
# offshore DEM has scan-line striping: smooth it at 1/10 resolution, then bring it back up

zs=np.asarray(Image.fromarray(Zb,'F').resize((W//10,H//10),Image.BOX));zs=blur(blur(zs,2),2)
Zb=np.asarray(Image.fromarray(zs.astype(np.float32),"F").resize((W,H),Image.BICUBIC))
Zb=np.where(LAND,0,np.minimum(Zb,-1))
dep=np.clip(-Zb,0,4000);sea=ramp(dep,[(0,(160,204,206)),(40,(118,172,186)),(150,(78,136,166)),(600,(52,102,142)),(2000,(36,78,118)),(4500,(26,58,96))])
ssh=np.ones_like(shade)
sea=sea*ssh[...,None]
img=np.where(LAND[...,None],col,sea)
# coastal glow / soft land edge
im=Image.fromarray(np.clip(img,0,255).astype(np.uint8))
# --- rivers, borders (drawn at 2x for smoothness)
K=2;big=im.resize((W*K,H*K),Image.BICUBIC);dr=ImageDraw.Draw(big,'RGBA')
def lines(geom):
    t=geom['type'];cs=geom['coordinates']
    if t=='LineString': return [cs]
    if t=='MultiLineString': return cs
    if t=='Polygon': return cs
    if t=='MultiPolygon': return [r for p in cs for r in p]
    return []
def draw(feats,color,width,dash=None,clip=None):
    for f in feats:
        for l in lines(f['geometry']):
            a=np.array(l);u,v=T(a[:,0],a[:,1]);pts=list(zip(u*K,v*K))
            if dash is None: dr.line(pts,fill=color,width=width,joint='curve');continue
            on,off=dash;acc=0;cur=[pts[0]];draw_on=True
            for p,q in zip(pts[:-1],pts[1:]):
                seg=math.hypot(q[0]-p[0],q[1]-p[1]);s=0
                while s<seg:
                    lim=(on if draw_on else off)-acc;st=min(lim,seg-s);t1=(s+st)/seg
                    pt=(p[0]+(q[0]-p[0])*t1,p[1]+(q[1]-p[1])*t1)
                    if draw_on: cur.append(pt)
                    s+=st;acc+=st
                    if acc>=(on if draw_on else off)-1e-6:
                        if draw_on and len(cur)>1: dr.line(cur,fill=color,width=width)
                        draw_on=not draw_on;acc=0;cur=[pt]
            if draw_on and len(cur)>1: dr.line(cur,fill=color,width=width)
riv=json.load(open('geo/riv_nw.json'))['features']
def chaikin(c,n=3):
    c=np.asarray(c,float)
    for _ in range(n):
        if len(c)<3: break
        q=c[:-1]*.75+c[1:]*.25;r=c[:-1]*.25+c[1:]*.75;c=np.vstack([c[:1],np.stack([q,r],1).reshape(-1,2),c[-1:]])
    return c.tolist()
for f in riv:
    g=f['geometry']
    if g['type']=='LineString': g['coordinates']=chaikin(g['coordinates'])
    elif g['type']=='MultiLineString': g['coordinates']=[chaikin(l) for l in g['coordinates']]
MUN=json.load(open('geo/caop_mun.json'))['features']
draw([f for f in MUN if f['properties']['dist'] in NWD],(40,32,24,150),3,dash=(12,9))      # concelhos: thin dashed
draw(ESP,(26,20,14,225),5)                                                                 # provinces: solid
draw(PTD,(26,20,14,235),5)                                                                 # districts: solid
for f in sorted(riv,key=lambda f:f['properties']['a']):
    a=f['properties']['a'];w=3 if a<600 else 4 if a<3000 else 6 if a<20000 else 8 if a<60000 else 11
    draw([f],(34,104,166,240),w+1)
draw(ESA,(18,14,10,245),9)                                                                 # autonomous communities
BRD=[json.load(open('app/border.json'))]
draw(BRD,(250,246,232,150),30)                                                            # light halo
draw(BRD,(10,8,6,255),18)                                                                  # national border
draw(BRD,(150,30,22,255),5)                                                                # red core line                                 # national border
out=big.resize((W,H),Image.LANCZOS)
TW,TH=(W+1)//2,(H+1)//2
for j in range(2):
    for i in range(2):
        out.crop((i*TW,j*TH,min(W,(i+1)*TW),min(H,(j+1)*TH))).save(f'app/maq-{j*2+i}.jpg',quality=84,optimize=True,progressive=True)
out.resize((W//4,H//4),Image.LANCZOS).save('maqprev2.jpg',quality=85)
# --- height grid for the mesh (one vertex every 4 px = 460 m), 16-bit in R,G: (h+500)*4
S=6;Hg=Zs[::S,::S];Hg=np.where(LAND[::S,::S],np.maximum(Hg,0),np.maximum(Hg,-480))
v=np.clip(np.round((Hg+500)*4),0,65535).astype(np.uint32)
Image.fromarray(np.stack([(v>>8)&255,v&255,np.zeros_like(v)],-1).astype(np.uint8),'RGB').save('app/maq-h.png',optimize=True)
json.dump({'x0':X0,'x1':X0+W*RES,'y0':Y1-H*RES,'y1':Y1,'w':W,'h':H,'tw':TW,'th':TH,'gw':Hg.shape[1],'gh':Hg.shape[0],'res':RES*S},open('geo/maq_meta.json','w'))

import os;print('tex',out.size,[os.path.getsize(f'app/maq-{k}.jpg') for k in range(4)],'grid',Hg.shape,os.path.getsize('app/maq-h.png'))
