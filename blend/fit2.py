import json,sys,numpy as np;sys.path.insert(0,'blend');from sab_plan import *
from scipy.optimize import minimize
# dark wall line traced on the 25 cm orthophoto (px of the -c.jpg; 4 px/m, centre 1024)
O=np.array([(947,919),(1010,922),(1054,934),(1091,981),(1116,1019),(1141,1062),(1160,1094),(1172,1137),(1210,1156),(1260,1169),(1304,1194),(1354,1225),(1391,1250)],float)
O=(O-1024)/4
def res(L,n=6):
    out=[]
    for a,b in zip(L[:-1],L[1:]):
        for t in np.linspace(0,1,n,endpoint=False):out.append(np.array(a)*(1-t)+np.array(b)*t)
    return np.array(out+[L[-1]],float)
Q=np.vstack([res(W_EAST_INNER),res(W_EAST_OUTER[:4])])
seg=np.stack([O[:-1],O[1:]],1)
def dist(q):
    a=seg[:,0];ab=seg[:,1]-a;t=np.clip(((q[:,None,:]-a)*ab).sum(-1)/(ab*ab).sum(-1),0,1);c=a+t[...,None]*ab
    return np.sqrt(((q[:,None,:]-c)**2).sum(-1)).min(1)
mean=Q.mean(0);K=1/4.6
def T(p,x):
    tx,tz,th,k=x;q=(np.array(p,float)-mean)*K*k;c,s=np.cos(th),np.sin(th);return np.stack([q[...,0]*c-q[...,1]*s,q[...,0]*s+q[...,1]*c],-1)+[tx,tz]
# keep only plan points that should lie on the traced line (both ends inside its extent)
def cost(x):
    d=dist(T(Q,x));return (np.minimum(d,12)**2).mean()+ (0 if .7<x[3]<1.3 else 100)
best=None
for th in np.radians(range(-30,31,5)):
  for k in [.8,.9,1,1.1]:
    r=minimize(cost,[O[:,0].mean(),O[:,1].mean(),th,k],method='Nelder-Mead',options={'maxiter':6000})
    if best is None or r.fun<best.fun:best=r
x=best.x;print(x,np.degrees(x[2]),np.sqrt(best.fun))
json.dump({'mean':mean.tolist(),'K':K,'x':x.tolist()},open('blend/sab_fit.json','w'))
