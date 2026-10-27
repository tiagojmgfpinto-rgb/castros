import json,math,cv2,numpy as np
# rectangular houses into vol.json: digitised rooms (dig/<id>-walls.json "rooms") + non-circular OSM ruin footprints
V=json.load(open('app/t3/vol.json'));d=json.load(open('data.json'))
ROMAN={'marco-de-canaveses-castro-do-freixo','santo-tirso-castro-de-monte-padrao','trofa-castro-de-alvarelhos'}
L=lambda px,py:(px/2048*512-256,py/2048*512-256)
def entry(cx,cz,w,l,a,id,src):
    r={'k':'ruin','c':1,'src':src,'q':[round(cx,2),round(cz,2),round(w,2),round(l,2),round(a,4)]}
    if id in ROMAN: r['rf']='t'
    ca,sa=math.cos(a),math.sin(a);pts=[]
    for u,v in((-w/2,-l/2),(w/2,-l/2),(w/2,l/2),(-w/2,l/2),(-w/2,-l/2)):
        pts+= [int(round((cx+u*ca-v*sa)*10)),int(round((cz+u*sa+v*ca)*10))]
    r['p']=pts;return r
tot={}
for id,v in V.items():
    v['r']=[r for r in v['r'] if not r.get('q')]
    n=0
    # OSM ruins that are not round: fit the minimum-area rectangle
    for r in list(v['r']):
        if r['k']!='ruin' or r.get('h') or r.get('src') or not r['c'] or len(r['p'])<8: continue
        P=np.array(r['p'],np.float32).reshape(-1,2)/10
        (cx,cz),(w,l),a=cv2.minAreaRect(P);A=cv2.contourArea(P)
        if 8<=w*l<=160 and A/(w*l)>0.72 and max(w,l)/min(w,l)<3.5:
            v['r'].append(entry(cx,cz,w,l,math.radians(a),id,'osm-rect'));n+=1
    try: rooms=json.load(open(f'dig/{id}-walls.json')).get('rooms',[])
    except FileNotFoundError: rooms=[]
    for cx,cy,w,h,a in rooms:
        x,z=L(cx,cy);v['r'].append(entry(x,z,w*.25,h*.25,math.radians(a),id,'dig'));n+=1
    if n: tot[id]=n
json.dump(V,open('app/t3/vol.json','w'),separators=(',',':'))
for s in d['sites']:
    if s['id'] in V and any(r.get('h') or r.get('q') for r in V[s['id']]['r']): s['t3v']=3
json.dump(d,open('data.json','w'),ensure_ascii=False,separators=(',',':'))
import shutil;shutil.copy('data.json','app/data.json')
print(tot,sum(tot.values()))
