# split track copper of an old net whose pads now carry several nets: delete the inter-group path(s), relabel parts
import sys; sys.path.insert(0,'/work/scripts')
from lib import *
def relabel(b,oldnets,verbose=True,extra_pad_nets=()):
    trk=[t for t in b.GetTracks() if t.GetNetname() in oldnets]
    def key(v): return (round(v.x/1000),round(v.y/1000))
    # nodes: (pos,layer) for track ends; via node per via; pad node per pad
    edges=[]  # (u,v,track)
    vias={}
    for t in trk:
        if t.Type()==pcbnew.PCB_VIA_T: vias[key(t.GetPosition())]=t
    nodeset=set()
    for t in trk:
        if t.Type()==pcbnew.PCB_VIA_T: continue
        a=(key(t.GetStart()),t.GetLayer()); c=(key(t.GetEnd()),t.GetLayer()); edges.append((a,c,t)); nodeset|={a,c}
    for n in list(nodeset):
        if n[0] in vias: edges.append((n,('V',n[0]),vias[n[0]]))
    for k,v in vias.items():
        nodeset.add(('V',k))
    pads=[p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()]
    padnode={}
    for n in nodeset:
        if n[0]=='V':
            pos=pcbnew.VECTOR2I(n[1][0]*1000,n[1][1]*1000); lays=None
        else: pos=pcbnew.VECTOR2I(n[0][0]*1000,n[0][1]*1000); lays=[n[1]]
        for p in pads:
            if not p.GetBoundingBox().Contains(pos): continue
            if lays and not p.IsOnLayer(lays[0]): continue
            if p.HitTest(pos):
                padnode.setdefault(n,set()).add(p.GetNetname())
                if verbose and p.GetNetname() not in oldnets: print('    padnode',n,p.GetParentFootprint().GetReference(),p.GetNumber(),p.GetNetname())
    import heapq
    adj={}
    for i,(u,v,t) in enumerate(edges):
        l=t.GetLength() if t.Type()!=pcbnew.PCB_VIA_T else 0
        adj.setdefault(u,[]).append((v,i,l)); adj.setdefault(v,[]).append((u,i,l))
    def dij(s):
        dist={s:0};pe={};pq=[(0,id(s),s)]
        while pq:
            d,_,x=heapq.heappop(pq)
            if d>dist[x]: continue
            for y,i,l in adj.get(x,[]):
                if d+l<dist.get(y,1e30): dist[y]=d+l;pe[y]=(x,i);heapq.heappush(pq,(d+l,id(y),y))
        return dist,pe
    groups={}
    for n,ns in padnode.items():
        for nn in ns: groups.setdefault(nn,[]).append(n)
    use={}
    for g,pn in groups.items():
        pn=list(set(pn))
        if len(pn)<2: continue
        D={p:dij(p) for p in pn}
        intree={pn[0]};rest=set(pn[1:])
        while rest:
            best=None
            for a in intree:
                for c in rest:
                    d=D[a][0].get(c)
                    if d is not None and (best is None or d<best[0]): best=(d,a,c)
            if best is None: break
            d,a,c=best; x=c
            while x!=a:
                px,i=D[a][1][x]; use.setdefault(i,set()).add(g); x=px
            intree.add(c); rest.discard(c)
    dl=[];orph=[];nchg=0
    for i,(u,v,t) in enumerate(edges):
        gs=use.get(i,set())
        if len(gs)==1:
            g=next(iter(gs))
            if t.GetNetname()!=g: t.SetNet(net(b,g)); nchg+=1
        elif len(gs)>1:
            keep=[g for g in gs if g in oldnets]
            if keep:
                if t.GetNetname()!=keep[0]: t.SetNet(net(b,keep[0])); nchg+=1
            else: dl.append(t)
        else:
            # unused by any group tree: keep if touching only one group's pads else orphan
            ns=padnode.get(u,set())|padnode.get(v,set())
            if len(ns)==1:
                g=next(iter(ns))
                if t.GetNetname()!=g: t.SetNet(net(b,g)); nchg+=1
            else: orph.append(t)
    # junction conflict cleanup: drop edges whose end node touches a different-net edge/pad
    dead=set(t.m_Uuid.AsString() for t in dl+orph)
    while True:
        lab={}
        for i,(u,v,t) in enumerate(edges):
            if t.m_Uuid.AsString() in dead: continue
            for n in (u,v): lab.setdefault(n,set()).add(t.GetNetname())
        bad=[]
        for i,(u,v,t) in enumerate(edges):
            if t.m_Uuid.AsString() in dead: continue
            if t.GetNetname() in oldnets: continue
            for n in (u,v):
                if len(lab[n])>1 or (padnode.get(n) and t.GetNetname() not in padnode[n]): bad.append(t);break
        if not bad: break
        for t in bad: dead.add(t.m_Uuid.AsString()); dl.append(t)
    uu={t.m_Uuid.AsString():t for t in dl+orph}
    if verbose:
        print('split',oldnets,'relabelled',nchg,'deleted',len(set(t.m_Uuid.AsString() for t in dl)),'orphan',len(orph))
        for t in dl: print('   del',b.GetLayerName(t.GetLayer()) if t.Type()!=pcbnew.PCB_VIA_T else 'via',xy(t.GetStart()),xy(t.GetEnd()))
    for t in uu.values(): b.Delete(t)
