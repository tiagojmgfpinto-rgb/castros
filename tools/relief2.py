import numpy as np, math, heapq, json
from PIL import Image
M=np.load('dem/M.npy'); z=10
meta=json.load(open('geo/relief_meta.json')); (S,W),(N,E)=meta['bounds']
lat_c=math.radians((N+S)/2); cell=40075016*math.cos(lat_c)/(2**z*256)
Z=np.maximum(M,0); land=M>0.5
gy,gx=np.gradient(Z,cell)
def hs(az,alt,zf=1.8):
    az=math.radians(az);alt=math.radians(alt)
    slope=np.arctan(zf*np.hypot(gx,gy)); aspect=np.arctan2(-gx,gy)
    return np.sin(alt)*np.cos(slope)+np.cos(alt)*np.sin(slope)*np.cos(az-aspect)
h=0.5*hs(315,40)+0.3*hs(270,45)+0.2*hs(350,50)
v=(h-math.sin(math.radians(45)))*1.5 - np.clip(Z/1600,0,1)*0.22   # neg=shadow, pos=light
v[~land]=0
A=np.clip(np.where(v<0,-v*0.95,v*0.6),0,1)
C=np.where(v<0,0,255).astype(np.uint8)
img=np.dstack([C,C,C,(A*255).astype(np.uint8)])
Image.fromarray(img,'RGBA').save('geo/relief.webp','WEBP',quality=62,method=6)
# ---------- rivers (D8 on 2x downsample) ----------
D=M.reshape(M.shape[0]//2,2,M.shape[1]//2,2).mean(axis=(1,3))
H,Wd=D.shape; L=D>0.5
filled=D.copy(); seen=np.zeros_like(L); pq=[]
for r in range(H):
    for c in range(Wd):
        if not L[r,c] or r in(0,H-1) or c in(0,Wd-1) or not L[max(r-1,0):r+2,max(c-1,0):c+2].all():
            if L[r,c] or True:
                pass
# seeds: sea cells and border cells
seed=(~L)|np.pad(np.zeros((H-2,Wd-2),bool),1,constant_values=True)
rs,cs=np.nonzero(seed)
for r,c in zip(rs,cs): heapq.heappush(pq,(float(D[r,c]),int(r),int(c))); seen[r,c]=True
nb=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
down=np.full((H,Wd),-1,np.int64); order=[]
while pq:
    e,r,c=heapq.heappop(pq); order.append(r*Wd+c)
    for dr,dc in nb:
        rr,cc=r+dr,c+dc
        if 0<=rr<H and 0<=cc<Wd and not seen[rr,cc]:
            seen[rr,cc]=True; ne=max(float(D[rr,cc]),e+1e-3); filled[rr,cc]=ne
            down[rr,cc]=r*Wd+c; heapq.heappush(pq,(ne,rr,cc))
acc=np.ones(H*Wd); dflat=down.ravel(); Lf=L.ravel()
for i in reversed(order):
    d=dflat[i]
    if d>=0: acc[d]+=acc[i]
cellkm2=(cell*2/1000)**2
T=180/cellkm2  # >=180 km2 catchment
riv=(acc>=T)&Lf
def ll(i):
    r,c=divmod(i,Wd); n=2**z*256
    x0p=(W+180)/360*n; y0p=(1-math.asinh(math.tan(math.radians(N)))/math.pi)/2*n
    px=x0p+c*2+1; py=y0p+r*2+1
    return [round(px/n*360-180,4), round(math.degrees(math.atan(math.sinh(math.pi*(1-2*py/n)))),4)]
up=np.zeros(H*Wd,int)
for i in np.nonzero(riv)[0]:
    d=dflat[i]
    if d>=0 and riv[d]: up[d]+=1
lines=[];done=np.zeros(H*Wd,bool)
heads=[i for i in np.nonzero(riv)[0] if up[i]==0]
heads.sort(key=lambda i:-acc[i])
# trace from heads; stop at junction already done (include it)
for hd in heads:
    i=hd; seg=[ll(i)]; a0=acc[i]
    while True:
        done[i]=True; d=dflat[i]
        if d<0 or not riv[d]:
            if d>=0: seg.append(ll(d))
            break
        seg.append(ll(d))
        if done[d]: break
        i=d
    lines.append({'type':'Feature','properties':{'a':round(float(acc[i]*cellkm2))},'geometry':{'type':'LineString','coordinates':seg}})
json.dump({'type':'FeatureCollection','features':lines},open('geo/rivers.json','w'))
print(len(lines),'river segs', max(f['properties']['a'] for f in lines))
