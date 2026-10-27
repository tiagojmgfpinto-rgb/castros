
G=${GLTF_TRANSFORM:-npx -y @gltf-transform/cli@4.1.1}; F=app/dio/$1
$G weld $F.glb /tmp/_w.glb >/dev/null && $G quantize /tmp/_w.glb $F.glb --quantize-position 14 --quantize-normal 8 --quantize-texcoord 12 >/dev/null
python3 mkpng.py $F.glb $F.glb.png
