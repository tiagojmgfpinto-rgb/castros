#!/bin/bash
# usage: g.sh name url [regex]
D=./hours_dl1
curl -sL -m 40 -A "Mozilla/5.0" "$2" -o "$D/$1.html"; echo "size $(wc -c < $D/$1.html)"
python3 -I -c "
import re,sys,html
t=open(sys.argv[1],errors='ignore').read()
t=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',t)
t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'\s+',' ',t)
seen=-1000
for m in re.finditer(sys.argv[2],t):
  if m.start()-seen<400: continue
  seen=m.start(); print(t[max(0,m.start()-200):m.start()+400]);print('--')
" "$D/$1.html" "${3:-(?i)(hor[áa]rio|encerra)}" | head -c 5000
