import json,sys
d=json.load(open('data.json')); o=json.load(open('openaire.json'))
cand={}
for l in open('wikicand.log'):
    if ' | ' in l: k,v=l.rstrip('\n').split(' | ',1); cand[k]=v
a,b=int(sys.argv[1]),int(sys.argv[2])
for s in d['sites'][a:b]:
    print('='*8,s['id'],'|',s['name'],'|',s['municipio'],'|',s['kind'])
    print('WIKI:',cand.get(s['id'],'(pending)'))
    import re,unicodedata
    nn=lambda x:unicodedata.normalize('NFKD',x.lower()).encode('ascii','ignore').decode()
    core=nn(re.sub(r'^(Castro|Povoado Fortificado|Povoado|Citânia|Cividade|Museu|Centro Interpretativo|Núcleo Interpretativo)\s+(de |do |da |dos |das )?','',s['name']))
    for p in [p for p in o.get(s['id'],[]) if core in nn(p['title'])]: print('PAPER:',p['year'],p['title'][:140],'|',', '.join(x for x in p['authors'] if x)[:80],'|',p['url'],'\n   ',p['abstract'][:350])
    print('TEXT:',' '.join(s['text'])[:2200])
