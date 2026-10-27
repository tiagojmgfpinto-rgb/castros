# tileable polygonal-masonry texture (Sabroso is known for its polygonal granite facing)
import numpy as np
from PIL import Image,ImageFilter
from scipy.spatial import cKDTree
rng=np.random.default_rng(7);N=512;n=90
P=rng.random((n,2))*N;T=np.vstack([P+[dx,dy] for dx in(-N,0,N) for dy in(-N,0,N)])
yy,xx=np.mgrid[0:N,0:N];q=np.stack([xx.ravel()+.5,yy.ravel()+.5],1)
d,i=cKDTree(T).query(q,k=2);edge=(d[:,1]-d[:,0]).reshape(N,N);cell=(i[:,0]%n).reshape(N,N)
tone=rng.normal(0,1,n);base=np.array([176,168,152],float)
col=base[None,None,:]+tone[cell][...,None]*np.array([13,12,11])
noise=np.asarray(Image.fromarray((rng.random((N,N))*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)),float)/255-.5
col+=noise[...,None]*38
mort=np.clip(edge/5,0,1)[...,None];col=col*(.5+.5*mort)
lit=0
Image.fromarray(np.clip(col,0,255).astype(np.uint8)).save('blend/stone.jpg',quality=88)
th=np.asarray(Image.fromarray((rng.random((256,256))*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.6)),float)/255
st=np.sin(np.arange(256)[:,None]/256*2*np.pi*22+th*3)*.5+.5
thc=np.array([150,118,70])[None,None,:]*(.72+.38*st[...,None])+(th[...,None]-.5)*40
Image.fromarray(np.clip(thc,0,255).astype(np.uint8)).save('blend/thatch.jpg',quality=88)
