# host-side A* router on masks produced by mkgrid.py
# usage: router.py prefix spec.json out.json
# spec: {"start":[[x,y,"F.Cu"|"*",r]...], "goal":[...], "layers":[..], "via_cost":mm, "layer_cost":{"In2.Cu":1.2}, "width":w, "via":0.35}
import sys,json,heapq,math
import numpy as np
from PIL import Image
pref,specf,outf=sys.argv[1:4]
meta=json.load(open(pref+'_meta.json')); spec=json.load(open(specf))
x0,y0,res,W,H=meta['x0'],meta['y0'],meta['res'],meta['W'],meta['H']
layers=spec.get('layers',meta['layers'])
M=np.stack([np.array(Image.open('%s_%s.png'%(pref,l)))>127 for l in layers])  # blocked
V=np.array(Image.open(pref+'_via.png'))>127
import os
if os.path.exists(pref+'_viasame.png') and not spec.get('allow_via_in_pad'): V|=np.array(Image.open(pref+'_viasame.png'))>127
NL=len(layers)
def cell(x,y): return (int(round((y-y0)/res)),int(round((x-x0)/res)))
def mmxy(r,c): return (round(x0+c*res,4),round(y0+r*res,4))
def mark(lst):
    S=set()
    for it in lst:
        x,y,l,rad=it
        r0,c0=cell(x,y); R=int(math.ceil(rad/res))
        ls=range(NL) if l=='*' else [layers.index(l)]
        for li in ls:
            for dr in range(-R,R+1):
                for dc in range(-R,R+1):
                    if dr*dr+dc*dc<=R*R:
                        r,c=r0+dr,c0+dc
                        if 0<=r<H and 0<=c<W:
                            M[li,r,c]=False; S.add((li,r,c))
            if l=='*' or it[2]=='*':
                pass
    return S
# allow via at start/goal disc if requested via '*'
starts=mark(spec['start'])
if spec.get('goal_layer'):
    gli=layers.index(spec['goal_layer']); rr,cc=np.nonzero(~M[gli]); goals=set((gli,int(a),int(c)) for a,c in zip(rr,cc))
else: goals=mark(spec['goal'])
for it in spec['start']+spec.get('goal',[]):
    if it[2]=='*':
        r0,c0=cell(it[0],it[1]); R=int(math.ceil(it[3]/res))
        V[max(0,r0-R):r0+R+1,max(0,c0-R):c0+R+1]=False
for b in spec.get('block',[]):  # [x0,y0,x1,y1,layer|'*']
    (ra,ca),(rb,cb)=cell(b[0],b[1]),cell(b[2],b[3])
    ls=range(NL) if b[4]=='*' else [layers.index(b[4])]
    for li in ls: M[li,ra:rb+1,ca:cb+1]=True
    if b[4]=='*': V[ra:rb+1,ca:cb+1]=True
vc=spec.get('via_cost',1.5)/res
lc=[spec.get('layer_cost',{}).get(l,1.0) for l in layers]
gl=np.array([g for g in goals]) if not spec.get('goal_layer') else np.array([[0,0,0]]); 
gr=gl[:,1]; gc=gl[:,2]
grc=np.stack([gr,gc],1)
cen=grc.mean(0)
ZEROH=bool(spec.get('goal_layer'))
def h(r,c):
    if ZEROH: return 0.0
    # octile distance to goal centroid-ish (admissible-ish lower bound via min over sample)
    dr=np.abs(grc[:,0]-r); dc=np.abs(grc[:,1]-c)
    d=np.max(dr,dc) if False else (np.maximum(dr,dc)+0.41421356*np.minimum(dr,dc))
    return d.min()*min(lc)
# subsample goal set for heuristic speed
if len(grc)>200: grc=grc[::max(1,len(grc)//200)]
DIRS=[(0,1,1),(1,0,1),(0,-1,1),(-1,0,1),(1,1,1.41421356),(1,-1,1.41421356),(-1,1,1.41421356),(-1,-1,1.41421356)]
turn=spec.get('turn_cost',0.5)
dist={}; prev={}
pq=[]
for s in starts:
    for di in range(8):
        k=(s[0],s[1],s[2],di); dist[k]=0; heapq.heappush(pq,(h(s[1],s[2]),0,k))
goalset=goals; found=None; n=0
maxn=spec.get('maxn',3000000)
while pq:
    f,g,k=heapq.heappop(pq)
    if dist.get(k,1e18)<g: continue
    li,r,c,di=k
    if (li,r,c) in goalset: found=k; break
    n+=1
    if n>maxn: break
    for ndi,(dr,dc,cost) in enumerate(DIRS):
        nr,nc=r+dr,c+dc
        if not(0<=nr<H and 0<=nc<W) or M[li,nr,nc]: continue
        ng=g+cost*lc[li]+(turn if ndi!=di else 0)
        nk=(li,nr,nc,ndi)
        if ng<dist.get(nk,1e18):
            dist[nk]=ng; prev[nk]=k; heapq.heappush(pq,(ng+h(nr,nc),ng,nk))
    if not V[r,c]:
        for nl in range(NL):
            if nl==li or M[nl,r,c]: continue
            ng=g+vc; nk=(nl,r,c,di)
            if ng<dist.get(nk,1e18):
                dist[nk]=ng; prev[nk]=k; heapq.heappush(pq,(ng+h(r,c),ng,nk))
if not found:
    print('NO ROUTE expanded',n); json.dump({'ok':False},open(outf,'w')); sys.exit(1)
path=[]; k=found
while k in prev: path.append(k); k=prev[k]
path.append(k); path.reverse()
# compress to segments
segs=[]; vias=[]
cur=[path[0]]
for a,b2 in zip(path,path[1:]):
    if a[0]!=b2[0]:
        vias.append(mmxy(a[1],a[2])); 
        segs.append((layers[a[0]],cur)); cur=[b2]; continue
    cur.append(b2)
segs.append((layers[cur[0][0]],cur))
out=[]
st=None;gt=None
for it in spec['start']:
    if (layers.index(it[2]) if it[2]!='*' else path[0][0])==path[0][0] and abs(it[0]-mmxy(path[0][1],path[0][2])[0])<=it[3]+res and abs(it[1]-mmxy(path[0][1],path[0][2])[1])<=it[3]+res: st=(it[0],it[1])
for it in spec.get('goal',[]):
    if abs(it[0]-mmxy(path[-1][1],path[-1][2])[0])<=it[3]+res and abs(it[1]-mmxy(path[-1][1],path[-1][2])[1])<=it[3]+res: gt=(it[0],it[1])
for l,pts in segs:
    if len(pts)<2: continue
    poly=[pts[0]]
    for i in range(1,len(pts)-1):
        d1=(pts[i][1]-pts[i-1][1],pts[i][2]-pts[i-1][2]); d2=(pts[i+1][1]-pts[i][1],pts[i+1][2]-pts[i][2])
        if d1!=d2: poly.append(pts[i])
    poly.append(pts[-1])
    out.append({'layer':l,'pts':[mmxy(p[1],p[2]) for p in poly]})
if out and st and spec.get('exact',True): out[0]['pts'].insert(0,st)
if out and gt and spec.get('exact',True): out[-1]['pts'].append(gt)
if not out and vias: pass
json.dump({'ok':True,'segs':out,'vias':vias,'cost':dist[found]*res,'expanded':n},open(outf,'w'),indent=1)
print('ok cost %.2fmm vias %d segs %d expanded %d'%(dist[found]*res,len(vias),len(out),n))
