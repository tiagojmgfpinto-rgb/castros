# Blender export app/dio/<id>.glb -> terrain simplified (~60k triangles, vertical error printed), textures <= 2048 px,
# weld + quantize -> app/dio/<id>.glb.png; then Draco -> app/dio/<id>.drc.glb.png (what the viewer loads first; the plain
# .glb.png stays as the fallback if the Draco decoder cannot run). Needs once: npm ci --prefix tools/gltf
F=app/dio/$1
[ -d tools/gltf/node_modules ] || npm ci --prefix tools/gltf >/dev/null
node tools/gltf/lighten.mjs $F.glb /tmp/_l.glb --report tools/gltf/reports/$1.json | grep -v "quantize: Skipping" && mv /tmp/_l.glb $F.glb
python3 mkpng.py $F.glb $F.glb.png
node tools/gltf/draco.mjs $F.glb /tmp/_d.glb | grep -v "Skipping Draco" && python3 mkpng.py /tmp/_d.glb $F.drc.glb.png && rm /tmp/_d.glb
