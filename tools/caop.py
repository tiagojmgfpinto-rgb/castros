import sqlite3,json
from shapely import wkb
from shapely.ops import transform
from shapely.geometry import mapping
from pyproj import Transformer
T=Transformer.from_crs(3763,4326,always_xy=True)
c=sqlite3.connect('caop/Continente_CAOP2024.gpkg')
def geom(b):
    flags=b[3]; env={0:0,1:32,2:48,3:48,4:64}[(flags>>1)&7]
    return transform(T.transform,wkb.loads(bytes(b[8+env:])))
def dump(sql,props,out):
    fs=[]
    for row in c.execute(sql):
        g=geom(row[0]); fs.append({'type':'Feature','properties':dict(zip(props,row[1:])),'geometry':mapping(g)})
    json.dump({'type':'FeatureCollection','features':fs},open(out,'w'),ensure_ascii=False)
    print(out,len(fs))
dump('select geom,municipio,distrito_ilha from cont_municipios',['mun','dist'],'geo/caop_mun.json')
dump('select geom,distrito from cont_distritos',['dist'],'geo/caop_dist.json')
