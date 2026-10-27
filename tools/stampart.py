import json,math,numpy as np
from PIL import Image
# per-site stamp art in a 120x120 stamp, drawn inside the inner circle (centre 60,60, r 37):
#  "plan": ruins plan (vol.json) within ~R m of the site point, as line art
#  "hill": real E–W terrain profile through the site (DEM), with ramparts on the summit
d=json.load(open('data.json'));V=json.load(open('app/t3/vol.json'))
def f(v): return f"{v:.1f}".rstrip('0').rstrip('.')
def plan(v):
    # all structures within 150 m; requires a real settlement plan (>= 8 round houses), framed on the houses
    items=[]
    for r in v['r']:
        if r['k']=='arch': continue
        P=np.array(r['p'],float).reshape(-1,2)/10
        if len(P)>=2 and np.hypot(*P.mean(0))<150: items.append((r,P))
    H=[P.mean(0) for r,P in items if r.get('h')]
    if len(H)<8: return None
    H=np.array(H);c0=np.median(H,0);rad=np.percentile(np.hypot(*(H-c0).T),85)+8
    k=33/max(rad,25);out=[]
    for r,P in items:
        Q=(P-c0)*k+60
        if r.get('h'):
            c=Q.mean(0);rr=np.mean(np.hypot(*(Q-c).T))
            if np.hypot(*(c-60))>34 or rr<.5: continue
            out.append(f"M{f(c[0]-rr)} {f(c[1])}a{f(rr)} {f(rr)} 0 1 0 {f(2*rr)} 0a{f(rr)} {f(rr)} 0 1 0 {f(-2*rr)} 0")
        else:
            Q=Q[(np.hypot(*(Q-60).T)<36)]
            if len(Q)<2: continue
            out.append("M"+"L".join(f"{f(x)} {f(y)}" for x,y in Q))
    return {"t":"plan","d":"".join(out),"w":round(max(.8,min(1.5,k*2.2)),2)}
def hill(s):
    try: a=np.asarray(Image.open(f"app/t3/{s['id']}.png").convert('RGB')).astype(float)
    except FileNotFoundError: return None
    H=(a[...,0]*256+a[...,1])/10-100;N=H.shape[0];c=N//2
    # pick the direction with most relief through the centre
    span=40;prof=None
    for row in (H[c,c-span:c+span+1],H[c-span:c+span+1,c],np.array([H[c-i,c+i] for i in range(-span,span+1)]),np.array([H[c+i,c+i] for i in range(-span,span+1)])):
        if prof is None or np.ptp(row)>np.ptp(prof): prof=row
    p=np.convolve(prof,np.ones(3)/3,mode='same');p[0],p[-1]=prof[0],prof[-1]
    lo,hi=p.min(),p.max();rel=max(hi-lo,25)
    xs=np.linspace(23,97,len(p));ys=76-(p-lo)/rel*36
    top=int(np.argmax(p[span-8:span+9]))+span-8
    line="M"+"L".join(f"{f(x)} {f(y)}" for x,y in zip(xs,ys))
    fill=line+"L97 98L23 98Z"
    tx,ty=xs[top],ys[top]
    # two ramparts as short arcs on the summit and a hut
    ram="".join(f"M{f(tx-w)} {f(ty+dy)}Q{f(tx)} {f(ty+dy-3)} {f(tx+w)} {f(ty+dy)}" for w,dy in ((15,7),(9,3.5)))
    hut=f"M{f(tx-3.2)} {f(ty-1)}h6.4v-3.2h-6.4zM{f(tx-4.2)} {f(ty-4.2)}L{f(tx)} {f(ty-9)}L{f(tx+4.2)} {f(ty-4.2)}z"
    return {"t":"hill","d":fill,"r":ram,"u":hut}
n={'plan':0,'hill':0,'none':0}
for s in d['sites']:
    s.pop('sa',None)
    if s['kind']=='museu': continue
    a=plan(V[s['id']]) if s['id'] in V else None
    a=a or hill(s)
    if a: s['sa']=a;n[a['t']]+=1
    else: n['none']+=1
json.dump(d,open('data.json','w'),ensure_ascii=False,separators=(',',':'))
print(n)
