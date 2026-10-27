import osmium,json,math,sys,collections
# per site (2 km block, local metres x east / z south): water polygons, waterway & road lines, for keeping trees off them
D=json.load(open('data.json'));R=6378137
S=[s for s in D['sites'] if s.get('t3')]
for s in S:
    lat,lon=s['coords'];s['_c']=(math.radians(lon)*R,math.log(math.tan(math.pi/4+math.radians(lat)/2))*R);s['_k']=1/math.cos(math.radians(lat))
G=collections.defaultdict(list)
for s in S:
    lat,lon=s['coords']
    for a in range(-1,2):
        for b in range(-1,2): G[(round(lat*40)+a,round(lon*40)+b)].append(s)
OUT={s['id']:{'wp':[],'wl':[],'rl':[]} for s in S};SEEN=set()
def loc(s,lon,lat):
    mx=math.radians(lon)*R;my=math.log(math.tan(math.pi/4+math.radians(lat)/2))*R
    return round((mx-s['_c'][0])/s['_k'],1), round(-(my-s['_c'][1])/s['_k'],1)
RW={'motorway':14,'trunk':12,'primary':10,'secondary':9,'tertiary':8,'unclassified':6,'residential':6,'service':4,'track':3,'living_street':5,'road':6}
WW={'river':18,'canal':10,'stream':4,'ditch':2,'drain':2}
class H(osmium.SimpleHandler):
    def way(self,w):
        if w.id in SEEN: return
        t={k:v for k,v in w.tags}
        kind=None
        if t.get('natural')=='water' or t.get('waterway')=='riverbank' or t.get('landuse') in('reservoir','basin'): kind='wp'
        elif t.get('waterway') in WW: kind='wl';wd=WW[t['waterway']]
        elif t.get('highway') in RW: kind='rl';wd=RW[t['highway']]
        if not kind: return
        try: pts=[(n.lon,n.lat) for n in w.nodes]
        except Exception: return
        if len(pts)<2: return
        SEEN.add(w.id)
        done=set()
        for p in pts[::max(1,len(pts)//8)]:
            for s in G.get((round(p[1]*40),round(p[0]*40)),[]):
                if s['id'] in done: continue
                L=[loc(s,*q) for q in pts]
                if not any(abs(x)<1100 and abs(z)<1100 for x,z in L): continue
                done.add(s['id'])
                o=OUT[s['id']]
                if kind=='wp':
                    if w.is_closed(): o['wp'].append([v for q in L for v in q])
                else: o[kind].append([wd]+[v for q in L for v in q])
for f in sys.argv[1:]: H().apply_file(f,locations=True)
json.dump(OUT,open('osm/mask_sites.json','w'),separators=(',',':'))
for s in S[:5]: o=OUT[s['id']];print(s['id'],len(o['wp']),len(o['wl']),len(o['rl']))
