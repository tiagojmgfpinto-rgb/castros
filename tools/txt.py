import re,sys,html
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
t=re.sub(r'(?s)<script.*?</script>|<style.*?</style>','',t)
t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'\s+',' ',t)
pat=sys.argv[2] if len(sys.argv)>2 else r'(?i)hor[áa]rio|encerra|telef|ingress|bilhete|opening|closed|segunda|ter[çc]a'
seen=-1
for m in re.finditer(pat,t):
    if m.start()<seen: continue
    print(t[max(0,m.start()-200):m.start()+500]); print('---'); seen=m.start()+500
