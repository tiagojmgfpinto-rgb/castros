import math,sys,os,subprocess
z=int(sys.argv[1]); W,S,E,N=-9.1,40.35,-6.85,42.2
def t(lon,lat):
    n=2**z; x=(lon+180)/360*n; y=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n; return int(x),int(y)
x0,y0=t(W,N); x1,y1=t(E,S)
print(x0,x1,y0,y1)
jobs=[]
for x in range(x0,x1+1):
    for y in range(y0,y1+1):
        f=f'dem/{z}_{x}_{y}.png'
        if not os.path.exists(f): jobs.append(f'curl -s -o {f} https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png')
open('dem/jobs.sh','w').write('\n'.join(jobs))
