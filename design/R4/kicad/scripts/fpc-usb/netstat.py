import pcbnew,sys,collections
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
L=collections.defaultdict(float); Vc=collections.Counter(); W=collections.defaultdict(set)
for t in b.GetTracks():
    n=t.GetNetname()
    if t.GetClass()=='PCB_VIA': Vc[n]+=1
    else: L[(n,b.GetLayerName(t.GetLayer()))]+=mm(t.GetLength()); W[n].add(round(mm(t.GetWidth()),3))
nets=sorted(set(k[0] for k in L)|set(Vc))
for n in nets:
    if len(sys.argv)>2 and not any(x in n for x in sys.argv[2].split(',')): continue
    print(n, {k[1]:round(v,2) for k,v in L.items() if k[0]==n}, 'vias',Vc[n],'widths',sorted(W[n]))
