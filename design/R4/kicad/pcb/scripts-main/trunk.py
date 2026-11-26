# trunk.py : classify power-net tracks into trunk / branch ; --areas creates R4_SL_BRANCH rule areas for branches
import sys,heapq,json; sys.path.insert(0,'/work/scripts')
from lib import *
TRUNK={'VBUS_RAW':['J3411.13','J3411.14','J3411.15','J3411.16','U1001.5'],
 'USB_5V_SAFE':['U1001.6','U501.13','C501.1','C1003.1'],
 'SYS':['U501.10','U501.11','C502.1','C1102.1','C1103.1','U1101.12','U1101.13','U902.7','U902.8'],
 'PACK_PLUS':['J501.1','U501.2','U501.3','C503.1']}
b=load()
def key(v): return (round(v.x/1000),round(v.y/1000))
res={}
for netn,tp in TRUNK.items():
    trk=[t for t in b.GetTracks() if t.GetNetname()==netn]
    adj={};E=[]
    def addE(a,c,l,t):
        E.append(t); adj.setdefault(a,[]).append((c,l,t)); adj.setdefault(c,[]).append((a,l,t))
    vias={key(t.GetPosition()):t for t in trk if t.Type()==pcbnew.PCB_VIA_T}
    nodes=set()
    for t in trk:
        if t.Type()==pcbnew.PCB_VIA_T: continue
        a=(key(t.GetStart()),t.GetLayer()); c=(key(t.GetEnd()),t.GetLayer()); addE(a,c,t.GetLength(),t); nodes|={a,c}
    for n in list(nodes):
        if n[0] in vias: addE(n,('V',n[0]),0,vias[n[0]])
    # pad nodes
    pn={}
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname()!=netn: continue
            nm=f.GetReference()+'.'+p.GetNumber(); P=('P',nm)
            for n in [q for q in adj.keys() if q[0]!="P"]:
                pos=pcbnew.VECTOR2I(n[1][0]*1000,n[1][1]*1000) if n[0]=='V' else pcbnew.VECTOR2I(n[0][0]*1000,n[0][1]*1000)
                if (n[0]=='V' or p.IsOnLayer(n[1])) and p.HitTest(pos): adj.setdefault(P,[]).append((n,0,None)); adj[n].append((P,0,None))
            pn[nm]=P
    def dij(s):
        dist={s:0};pe={};pq=[(0,0,s)];c=0
        while pq:
            d_,_,x=heapq.heappop(pq)
            if d_>dist[x]: continue
            for y,l,t in adj.get(x,[]):
                if d_+l<dist.get(y,1e30): dist[y]=d_+l;pe[y]=(x,t);c+=1;heapq.heappush(pq,(d_+l,c,y))
        return dist,pe
    tps=[pn[x] for x in tp if x in pn]
    used=set(); missing=[]
    if tps:
        intree={tps[0]}; rest=set(tps[1:]); D={p:dij(p) for p in tps}
        while rest:
            best=None
            for a in intree:
                for c in rest:
                    dd=D[a][0].get(c)
                    if dd is not None and (best is None or dd<best[0]): best=(dd,a,c)
            if not best: missing=[x[1] for x in rest]; break
            _,a,c=best; x=c
            while x!=a:
                px,t=D[a][1][x]
                if t is not None: used.add(t.m_Uuid.AsString())
                x=px
            intree.add(c); rest.discard(c)
    res[netn]={'trunk':[u for u in used],'missing':missing,'branch':[t.m_Uuid.AsString() for t in trk if t.m_Uuid.AsString() not in used]}
    print(netn,'trunk segs',len(used),'branch',len(res[netn]['branch']),'unreached trunk pads',missing)
json.dump(res,open('/work/out/trunk.json','w'))
if '--areas' in sys.argv:
    # delete old areas
    for z in list(b.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName()=='R4_SL_BRANCH': b.Delete(z)
    byid={t.m_Uuid.AsString():t for t in b.GetTracks()}
    n=0
    for netn,r in res.items():
        for u in r['branch']:
            t=byid[u]; bb=t.GetBoundingBox(); bb.Inflate(int(0.05*MM))
            z=pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName('R4_SL_BRANCH')
            z.SetLayerSet(pcbnew.LSET.AllCuMask() if t.Type()==pcbnew.PCB_VIA_T else pcbnew.LSET(t.GetLayer()) if False else pcbnew.LSET.AllCuMask())
            for fn in ('SetDoNotAllowTracks','SetDoNotAllowVias','SetDoNotAllowPads','SetDoNotAllowZoneFills','SetDoNotAllowFootprints'): getattr(z,fn)(False)
            o=z.Outline(); o.NewOutline()
            for x,y in [(bb.GetX(),bb.GetY()),(bb.GetRight(),bb.GetY()),(bb.GetRight(),bb.GetBottom()),(bb.GetX(),bb.GetBottom())]: o.Append(int(x),int(y))
            b.Add(z); n+=1
    print('areas',n); save(b,fill=False)
