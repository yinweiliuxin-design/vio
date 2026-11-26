import pcbnew, math
MM=1e6
def mm(v): return v/MM
def pt(x,y): return pcbnew.VECTOR2I(int(round(x*MM)),int(round(y*MM)))
def L(b,name): return b.GetLayerID(name)
def fp(b,ref): return b.FindFootprintByReference(ref)
def pad(b,ref,num):
    f=fp(b,ref)
    for p in f.Pads():
        if p.GetNumber()==str(num): return p
def xy(v): return (round(v.x/MM,3),round(v.y/MM,3))

BOARD='/work/r4/pcb/SmartVio-main-r3-linked.kicad_pcb'
def load(path=BOARD): return pcbnew.LoadBoard(path)
def save(b,path=BOARD,fill=True):
    if fill:
        f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
    b.Save(path)
def net(b,name):
    n=b.FindNet(name)
    if n is None or n.GetNetCode()<=0 and name!='':
        n=pcbnew.NETINFO_ITEM(b,name); b.Add(n)
    return n
def add_track(b,netname,layer,w,pts):
    out=[]
    for a,c in zip(pts,pts[1:]):
        t=pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(int(round(w*MM)))
        t.SetLayer(L(b,layer) if isinstance(layer,str) else layer); t.SetNet(net(b,netname)); b.Add(t); out.append(t)
    return out
def add_via(b,netname,p,d=0.35,drill=0.15):
    v=pcbnew.PCB_VIA(b); v.SetPosition(pt(*p)); v.SetWidth(int(round(d*MM))); v.SetDrill(int(round(drill*MM)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(net(b,netname)); b.Add(v); return v
def tracks(b,netname=None,layer=None,bbox=None,vias=None):
    out=[]
    for t in b.GetTracks():
        if netname is not None and t.GetNetname()!=netname: continue
        isv=t.Type()==pcbnew.PCB_VIA_T
        if vias is True and not isv: continue
        if vias is False and isv: continue
        if layer is not None and (isv or b.GetLayerName(t.GetLayer())!=layer): continue
        if bbox is not None:
            x0,y0,x1,y1=bbox
            if isv:
                x,y=xy(t.GetPosition())
                if not(x0<=x<=x1 and y0<=y<=y1): continue
            else:
                s,e=xy(t.GetStart()),xy(t.GetEnd())
                if not(x0<=s[0]<=x1 and y0<=s[1]<=y1 and x0<=e[0]<=x1 and y0<=e[1]<=y1): continue
        out.append(t)
    return out
def remove(b,items):
    for t in items: b.Delete(t)
def add_zone(b,netname,layer,poly,prio=1,clear=0.15,minw=0.2,thermal='solid',name=''):
    z=pcbnew.ZONE(b); z.SetLayer(L(b,layer)); z.SetNet(net(b,netname))
    o=z.Outline(); o.NewOutline()
    for x,y in poly: o.Append(int(round(x*MM)),int(round(y*MM)))
    z.SetAssignedPriority(prio); z.SetLocalClearance(int(clear*MM)); z.SetMinThickness(int(minw*MM))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if thermal=='solid' else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    if name: z.SetZoneName(name)
    b.Add(z); return z
def collide_report(b,items,margin=0.0):
    """exact pcbnew collision check of new items vs other-net copper; returns list of strings"""
    res=[]
    PWR_IN=('VBUS_RAW','USB_5V_SAFE')
    others=[t for t in b.GetTracks()]+[p for f in b.GetFootprints() for p in f.Pads()]
    for it in items:
        n=it.GetNetname(); bb=it.GetBoundingBox(); bb.Inflate(int(0.5*MM))
        for li in it.GetLayerSet().CuStack():
            sh=it.GetEffectiveShape(li)
            for o in others:
                if o.m_Uuid.AsString()==it.m_Uuid.AsString() or (o.GetNetname()==n and n!=""): continue
                if not o.IsOnLayer(li): continue
                if not o.GetBoundingBox().Intersects(bb): continue
                c=0.2 if (n in PWR_IN or o.GetNetname() in PWR_IN) else 0.15
                if sh.Collide(o.GetEffectiveShape(li),int((c+margin)*MM)-1):
                    res.append('%s %s vs %s %s'%(n,b.GetLayerName(li),o.GetNetname(),o.GetParentFootprint().GetReference()+'.'+o.GetNumber() if o.Type()==pcbnew.PCB_PAD_T else (xy(o.GetStart()) if o.Type()!=pcbnew.PCB_VIA_T else 'via'+str(xy(o.GetPosition())))))
    return res

def move_fp(b,ref,x,y,rot=None,flip=None):
    f=fp(b,ref)
    if flip is not None and f.IsFlipped()!=flip:
        f.Flip(f.GetPosition(),pcbnew.FLIP_DIRECTION_LEFT_RIGHT if hasattr(pcbnew,'FLIP_DIRECTION_LEFT_RIGHT') else False)
    f.SetPosition(pt(x,y))
    if rot is not None: f.SetOrientationDegrees(rot)
    return f
def place_check(b,f,ignore_tracks_of=()):
    """courtyard overlap + pad copper collisions; returns list"""
    res=[]
    side=pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd
    cy=f.GetCourtyard(side)
    for g in b.GetFootprints():
        if g.GetReference()==f.GetReference() or g.IsFlipped()!=f.IsFlipped(): continue
        cg=g.GetCourtyard(side)
        if cy.OutlineCount() and cg.OutlineCount():
            a=pcbnew.SHAPE_POLY_SET(cy); a.BooleanIntersection(cg)
            if a.Area()>1000: res.append('courtyard '+g.GetReference())
    pads=list(f.Pads())
    res+=collide_report(b,pads)
    return res

LIBDIR='/work/r4/footprints/%s.pretty'
def reload_fp(b,ref,fpid=None):
    old=fp(b,ref); fpid=fpid or old.GetFPID().GetUniStringLibId()
    lib,name=fpid.split(':'); f=pcbnew.FootprintLoad(LIBDIR%lib,name); f.SetFPID(pcbnew.LIB_ID(lib,name))
    b.Add(f)
    if old.IsFlipped(): f.Flip(f.GetPosition(),pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    f.SetPosition(old.GetPosition()); f.SetOrientation(old.GetOrientation())
    f.SetReference(ref); f.SetValue(old.GetValue())
    for fl in old.GetFields():
        n=fl.GetName()
        if n in ('Reference','Value','Footprint','Datasheet','Description'): continue
        new_=not f.HasField(n); f.SetField(n,fl.GetText())
        if new_: f.GetField(n).SetVisible(False); f.GetField(n).SetLayer(pcbnew.B_Fab if f.IsFlipped() else pcbnew.F_Fab)
    f.SetPath(old.GetPath()); f.SetSheetname(old.GetSheetname()); f.SetSheetfile(old.GetSheetfile())
    f.SetExcludedFromBOM(old.IsExcludedFromBOM()); f.SetDNP(old.IsDNP())
    nets={p.GetNumber():p.GetNetname() for p in old.Pads()}
    for p in f.Pads():
        if p.GetNumber() in nets: p.SetNet(net(b,nets[p.GetNumber()]))
    b.Delete(old); return f
