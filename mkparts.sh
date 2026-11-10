# Blender export app/dio/<id>.glb -> terrain simplified (~60k triangles, vertical error printed), textures <= 2048 px,
# weld + quantize (no Draco) -> app/dio/<id>.glb.png. Needs once: npm ci --prefix tools/gltf
F=app/dio/$1
[ -d tools/gltf/node_modules ] || npm ci --prefix tools/gltf >/dev/null
node tools/gltf/lighten.mjs $F.glb /tmp/_l.glb --report tools/gltf/reports/$1.json | grep -v "quantize: Skipping" && mv /tmp/_l.glb $F.glb
python3 mkpng.py $F.glb $F.glb.png
