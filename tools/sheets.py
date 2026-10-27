import cv2,numpy as np,json
# contact sheets of the central 256 m of each site's 25 cm orthophoto, for visual triage
d=json.load(open('data.json'))
done={'viana-do-castelo-citania-de-santa-luzia','penafiel-castro-de-monte-mozinho','povoa-de-varzim-cividade-de-terroso','guimaraes-citania-de-briteiros','pacos-de-ferreira-citania-de-sanfins'}
ids=[s['id'] for s in d['sites'] if s.get('t3') and s['id'] not in done]
json.dump(ids,open('dig/triage_ids.json','w'))
T=300
for k in range(0,len(ids),12):
    tiles=[]
    for j,i in enumerate(ids[k:k+12]):
        im=cv2.imread(f'app/t3/{i}-c.jpg')[512:1536,512:1536]
        im=cv2.resize(im,(T,T),interpolation=cv2.INTER_AREA)
        cv2.rectangle(im,(0,0),(T,18),(0,0,0),-1);cv2.putText(im,f'{k+j} {i[:38]}',(3,13),cv2.FONT_HERSHEY_SIMPLEX,.36,(255,255,255),1)
        tiles.append(im)
    while len(tiles)%4: tiles.append(np.zeros((T,T,3),np.uint8))
    cv2.imwrite(f'dig/sheet_{k//12}.jpg',np.vstack([np.hstack(tiles[r:r+4]) for r in range(0,len(tiles),4)]),[cv2.IMWRITE_JPEG_QUALITY,82])
print(len(ids))
