import json,re,sys
f=sys.argv[1]; d=json.load(open(f))
R=[('MN','Monumento Nacional',r'Monumento Nacional'),
   ('IP','Imóvel de Interesse Público',r'Im[óo]vel de Interesse P[úu]blico'),
   ('IP','Sítio de Interesse Público',r'S[íi]tio de Interesse P[úu]blico'),
   ('IP','Monumento de Interesse Público',r'Monumento de Interesse P[úu]blico'),
   ('IP','Conjunto de Interesse Público',r'Conjunto de Interesse P[úu]blico'),
   ('IM','Interesse Municipal',r'(?:Im[óo]vel|Monumento|S[íi]tio|Bem|Conjunto)? ?de Interesse Municipal'),
   ('NC','Sem classificação legal',r'n[ãa]o (?:est[áa]|esteja) classificad|n[ãa]o (?:tem|possui|possua) (?:qualquer )?classifica|sem classifica|n[ãa]o est[áa] sob nenhuma classifica|n[ãa]o possua sequer uma classifica'),
   ('VC','Em vias de classificação',r'vias de classifica')]
FIX={ # revistos à mão
 'mondim-de-basto-castro-do-crastoeiro':('IP','Sítio de Interesse Público'),
 'santa-maria-da-feira-castro-de-romariz':('IP','Imóvel de Interesse Público'),
 'viana-do-castelo-cividade-de-ancora-afife':('VC','Em vias de classificação (como Monumento Nacional)'),
 'vila-nova-de-famalicao-castro-de-sao-miguel-o-anjo':('IP','Imóvel de Interesse Público'),
 'vieira-do-minho-castro-de-vieira':('NC','Sem classificação legal (proposta de classificação preparada)'),
 'viana-do-castelo-castro-de-vieito':('NC','Sem classificação legal'),
 'melgaco-povoado-a-sudeste-do-castelo-de-castro-laboreiro':('ZP','Em zona de proteção (Castelo de Castro Laboreiro, Monumento Nacional)'),
 'lousada-castro-de-sao-domingos':('VC','Em vias de classificação'),
 'barcelos-citania-de-roriz':('ND','Classificação não indicada nas fontes'),
 'moncao-castro-de-nossa-senhora-da-graca':('ND','Classificação não indicada nas fontes'),
 'barcelos-castro-de-carmona':('VC','Em vias de classificação (processo caducado em 2012)'),
}
from collections import Counter;c=Counter()
for s in d['sites']:
    s.pop('cls',None)
    if s['kind']=='museu': continue
    t=' '.join(s.get('text',[])+s.get('hist',{}).get('p',[]))
    hit=None
    if s['id'] in FIX: hit=FIX[s['id']]
    else:
        for code,lab,p in R:
            if re.search(p,t,re.I): hit=(code,lab); break
    if not hit: c['?']+=1; continue
    code,lab=hit
    m=re.search(re.escape(lab.split(' (')[0])+r'[^.]{0,40}?(?:desde|em|de) (\d{4})',t,re.I) or re.search(r'(?:classificad[oa]|classifica[çc][ãa]o)[^.]{0,80}?(?:desde|em|de) (\d{4})',t,re.I)
    yr=m.group(1) if m and code in('MN','IP','IM','VC') and s['id']!='barcelos-castro-de-carmona' else None
    s['cls']={'c':code,'l':lab}
    if yr: s['cls']['y']=yr
    if re.search(r'Zona Especial de Prote',t,re.I): s['cls']['zep']=1
    c[code]+=1
json.dump(d,open(f,'w'),ensure_ascii=False,separators=(',',':'))
print(dict(c)); print([s['id'] for s in d['sites'] if s['kind']!='museu' and 'cls' not in s])
