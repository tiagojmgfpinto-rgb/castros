import json,sys,numpy as np;sys.path.insert(0,'blend');import brit_plan as P
from scipy.optimize import minimize
v=json.load(open('app/t3/vol.json'))['guimaraes-citania-de-briteiros']
W0=np.array(v['r'][0]['p'],float).reshape(-1,2)/10        # OSM rampart line around the acropolis (x east, z south, m)
def dense(L,n=8):
    L=np.asarray(L,float);o=[]
    for a,b in zip(L[:-1],L[1:]):o+=[a+(b-a)*t for t in np.linspace(0,1,n,endpoint=False)]
    return np.array(o+[L[-1]])
Q=dense(W0)
R1=np.array(P.R1+[P.R1[0]],float);seg=np.stack([R1[:-1],R1[1:]],1);mean=R1[:-1].mean(0)
def T(p,x):
    tx,tz,th,k=x;q=(np.asarray(p,float)-mean)/P.SCALE_PX_PER_M*k;c,s=np.cos(th),np.sin(th);return np.stack([q[...,0]*c-q[...,1]*s,q[...,0]*s+q[...,1]*c],-1)+[tx,tz]
def cost(x):
    S=T(seg.reshape(-1,2),x).reshape(-1,2,2);a=S[:,0];ab=S[:,1]-a
    t=np.clip(((Q[:,None]-a)*ab).sum(-1)/(ab*ab).sum(-1),0,1);d=np.sqrt(((Q[:,None]-(a+t[...,None]*ab))**2).sum(-1)).min(1)
    return (np.minimum(d,30)**2).mean()
best=None
for th in np.radians(range(-80,1,5)):
  for k in [.7,.85,1,1.15]:
    r=minimize(cost,[W0[:,0].mean(),W0[:,1].mean(),th,k],method='Nelder-Mead',options={'maxiter':5000})
    if best is None or r.fun<best.fun:best=r
x=best.x;print('tx,tz',x[:2].round(1),'rot',np.degrees(x[2]).round(1),'scale',x[3].round(3),'rms m',np.sqrt(best.fun).round(1))
json.dump({'mean':mean.tolist(),'x':x.tolist(),'pxm':P.SCALE_PX_PER_M},open('blend/brit_fit.json','w'))
