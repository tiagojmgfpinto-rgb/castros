# Inverse of mkpng.py: app/dio/<id>.glb.png -> <id>.glb (4-byte little-endian length, then the GLB bytes in the RGB pixels).
import sys,numpy as np
from PIL import Image
src,dst=sys.argv[1:3];a=np.asarray(Image.open(src).convert('RGB')).tobytes();n=int.from_bytes(a[:4],'little')
open(dst,'wb').write(a[4:4+n]);print(n)
