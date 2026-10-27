import sys,numpy as np
from PIL import Image
src,dst=sys.argv[1:3];b=open(src,'rb').read();n=len(b)
data=np.frombuffer(n.to_bytes(4,'little')+b,np.uint8);W=4096;H=-(-len(data)//(W*3))
pad=np.zeros(W*H*3,np.uint8);pad[:len(data)]=data
Image.fromarray(pad.reshape(H,W,3),'RGB').save(dst,optimize=True,compress_level=9)
import os;print(n,os.path.getsize(dst))
