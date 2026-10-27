import osmium,json,math,sys,collections
D=json.load(open('data.json'));R=6378137
S=[s for s in D['sites'] if s.get('t3')]
for s in S:
    lat,lon=s['coords'];s['_c']=(math.radians(lon)*R,math.log(math.tan(math.pi/4+math.radians(lat)/2))*R);s['_k']=1/math.cos(math.radians(lat))
G=collections.defaultdict(list)
for s in S:
    lat,lon=s['coords']
    for a in range(-1,2):
        for b in range(-1,2): G[(round(lat*40)+a,round(lon*40)+b)].append(s)
OUT={s['id']:{'b':[],'r':[]} for s in S};SEEN=set()
def loc(s,lon,lat):
    mx=math.radians(lon)*R;my=math.log(math.tan(math.pi/4+math.radians(lat)/2))*R
    return (mx-s['_c'][0])/(1000*s['_k'])*1000, -(my-s['_c'][1])/(1000*s['_k'])*1000
def bh(t):
    try:
        if 'height' in t: return max(2.5,min(60,float(t['height'].split()[0].replace(',','.'))))
    except: pass
    try:
        if 'building:levels' in t: return max(1,min(15,float(t['building:levels'])))*3+1
    except: pass
    return {'garage':3,'garages':3,'shed':3,'hut':3,'roof':4,'church':13,'chapel':8,'industrial':9,'warehouse':9,'apartments':13,'commercial':8,'retail':6,'school':8,'ruins':2}.get(t.get('building'),6)
RU=lambda t:(t.get('historic') in('archaeological_site','ruins','citywalls','castle','fort') or t.get('ruins')=='yes' or t.get('building')=='ruins' or t.get('barrier') in('wall','retaining_wall','city_wall') or t.get('archaeological_site') is not None or t.get('historic:civilization') is not None)
class H(osmium.SimpleHandler):
    def way(self,w):
        t={k:v for k,v in w.tags}
        isb='building' in t and t['building']!='no' and t.get('building')!='ruins'
        isr=RU(t)
        if not(isb or isr): return
        try: pts=[(n.lon,n.lat) for n in w.nodes]
        except Exception: return
        if len(pts)<2 or w.id in SEEN: return
        SEEN.add(w.id)
        clat=sum(p[1] for p in pts)/len(pts);clon=sum(p[0] for p in pts)/len(pts)
        for s in G.get((round(clat*40),round(clon*40)),[]):
            L=[loc(s,*p) for p in pts]
            cx=sum(p[0] for p in L)/len(L);cz=sum(p[1] for p in L)/len(L)
            if isb and abs(cx)<990 and abs(cz)<990 and len(L)>=4 and w.is_closed():
                OUT[s['id']]['b'].append([round(bh(t),1)]+[round(v,1) for p in L[:-1] for v in p])
            if isr and abs(cx)<600 and abs(cz)<600:
                kind=t.get('historic') or t.get('barrier') or ('ruins' if t.get('building')=='ruins' or t.get('ruins')=='yes' else 'arch')
                OUT[s['id']]['r'].append({'k':kind,'c':int(w.is_closed()),'n':t.get('name',''),'p':[round(v,1) for p in L for v in p]})
for f in sys.argv[1:]:
    H().apply_file(f,locations=True);print('done',f,file=sys.stderr)
json.dump(OUT,open('osm/osm_sites.json','w'),separators=(',',':'))
for s in S:
    o=OUT[s['id']]; print(s['id'][:50],len(o['b']),len(o['r']),collections.Counter(r['k'] for r in o['r']).most_common(4))
