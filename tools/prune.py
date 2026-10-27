import json,glob,os,numpy as np
# drop isolated short wall fragments (likely shadows, stones or path edges): < 3 m and nothing else within 2 m
tot=[0,0]
for f in glob.glob('dig/*-walls.json'):
    d=json.load(open(f));V=d.get('vlines') or []
    if not V: continue
    if 'vlines_raw' not in d: d['vlines_raw']=V
    V=d['vlines_raw'];A=[np.array(l,float) for l in V]
    Ls=[np.hypot(*np.diff(a,axis=0).T).sum()*.25 for a in A]
    keep=[]
    for i,a in enumerate(A):
        if Ls[i]>=3: keep.append(V[i]);continue
        near=False
        for j,b in enumerate(A):
            if j==i: continue
            dd=np.min(np.hypot(a[:,None,0]-b[None,:,0],a[:,None,1]-b[None,:,1]))*.25
            if dd<2: near=True;break
        if near and Ls[i]>=1.5: keep.append(V[i])
    d['vlines']=keep;json.dump(d,open(f,'w'));tot[0]+=len(V);tot[1]+=len(keep)
    print(os.path.basename(f)[:40],len(V),'->',len(keep))
print(tot)
