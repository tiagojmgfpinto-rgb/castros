import json,numpy as np
from scipy.optimize import minimize
v=json.load(open('app/t3/vol.json'))['guimaraes-castro-de-sabroso']['r'][0]['p']
P=np.array(v,float).reshape(-1,2)/10  # metres, x east, z south
keep=np.r_[True,(np.abs(np.diff(P,axis=0)).sum(1)>0)];P=P[keep]
seg=np.stack([P,np.roll(P,-1,0)],1)
def dist(q):
    a=seg[:,0];b=seg[:,1];ab=b-a;t=np.clip(((q[:,None,:]-a)*ab).sum(-1)/(ab*ab).sum(-1),0,1)
    c=a+np.nan_to_num(t)[...,None]*ab;return np.sqrt(((q[:,None,:]-c)**2).sum(-1)).min(1)
# 1929 protection-zone markers read off the 1930 plan (px; x right=east, y down=south)
M=np.array([[580,573],[617,404],[709,296],[977,168],[1108,416],[1151,509],[1390,783],[1402,982],[1322,1288],[1166,1369],[985,1410],[835,1446],[822,1300],[822,1150]],float)
K=1/4.6
def tr(p,x):
    tx,tz,th,k=x;c,s=np.cos(th),np.sin(th);q=(M-M.mean(0))*K*k
    return np.stack([q[:,0]*c-q[:,1]*s,q[:,0]*s+q[:,1]*c],1)+[tx,tz]
best=None
for th0 in np.radians([-10,-5,0,5,10]):
  for k0 in [.9,1,1.1]:
    r=minimize(lambda x:(dist(tr(M,x))**2).mean(),[P[:,0].mean(),P[:,1].mean(),th0,k0],method='Nelder-Mead',options={'maxiter':4000,'xatol':1e-4,'fatol':1e-6})
    if best is None or r.fun<best.fun:best=r
print(best.x,np.degrees(best.x[2]),'rms',np.sqrt(best.fun));print(np.round(dist(tr(M,best.x)),1))
json.dump({'mean':M.mean(0).tolist(),'K':K,'x':best.x.tolist()},open('blend/sab_fit.json','w'))
