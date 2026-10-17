import pcbnew, math
FM=pcbnew.FromMM
def V(x,y): return pcbnew.VECTOR2I(FM(x),FM(y))
LAY={'F.Cu':pcbnew.F_Cu,'B.Cu':pcbnew.B_Cu,'F.Mask':pcbnew.F_Mask,'B.Mask':pcbnew.B_Mask,'F.Paste':pcbnew.F_Paste,'B.Paste':pcbnew.B_Paste,
     'Edge.Cuts':pcbnew.Edge_Cuts,'User.1':pcbnew.User_1,'User.2':pcbnew.User_2,'F.SilkS':pcbnew.F_SilkS,'B.SilkS':pcbnew.B_SilkS,
     'F.Fab':pcbnew.F_Fab,'B.Fab':pcbnew.B_Fab,'F.CrtYd':pcbnew.F_CrtYd,'B.CrtYd':pcbnew.B_CrtYd,'Dwgs.User':pcbnew.Dwgs_User,'Cmts.User':pcbnew.Cmts_User,
     'In1.Cu':pcbnew.In1_Cu,'In2.Cu':pcbnew.In2_Cu}
class B:
    pass
class B:
    def __init__(self,path,clear=True):
        self.b=pcbnew.LoadBoard(path)
        self.nets={}
    def net(self,name):
        if name is None or name=='': return None
        n=self.b.FindNet(name)
        if n is None:
            n=pcbnew.NETINFO_ITEM(self.b,name); self.b.Add(n)
        return n
    def line(self,a,b2,layer='Edge.Cuts',w=0.05):
        s=pcbnew.PCB_SHAPE(self.b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*a)); s.SetEnd(V(*b2)); s.SetLayer(LAY[layer]); s.SetWidth(FM(w)); self.b.Add(s); return s
    def poly_outline(self,pts,layer='Edge.Cuts',w=0.05):
        for i in range(len(pts)): self.line(pts[i],pts[(i+1)%len(pts)],layer,w)
    def rect(self,x0,y0,x1,y1,layer,w=0.1,fill=False):
        s=pcbnew.PCB_SHAPE(self.b); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetStart(V(x0,y0)); s.SetEnd(V(x1,y1)); s.SetLayer(LAY[layer]); s.SetWidth(FM(w)); s.SetFilled(fill); self.b.Add(s); return s
    def circle(self,c,r,layer,w=0.1):
        s=pcbnew.PCB_SHAPE(self.b); s.SetShape(pcbnew.SHAPE_T_CIRCLE); s.SetCenter(V(*c)); s.SetEnd(V(c[0]+r,c[1])); s.SetLayer(LAY[layer]); s.SetWidth(FM(w)); self.b.Add(s); return s
    def text(self,txt,at,layer,size=0.8,th=0.12,mirror=False):
        t=pcbnew.PCB_TEXT(self.b); t.SetText(txt); t.SetPosition(V(*at)); t.SetLayer(LAY[layer]); t.SetTextSize(V(size,size)); t.SetTextThickness(FM(th))
        if mirror: t.SetMirrored(True)
        self.b.Add(t); return t
    def track(self,pts,w,layer,net):
        n=self.net(net); out=[]
        for a,b2 in zip(pts[:-1],pts[1:]):
            t=pcbnew.PCB_TRACK(self.b); t.SetStart(V(*a)); t.SetEnd(V(*b2)); t.SetWidth(FM(w)); t.SetLayer(LAY[layer]); t.SetNet(n); self.b.Add(t); out.append(t)
        return out
    def via(self,at,net,size=0.35,drill=0.15,l1='F.Cu',l2='B.Cu'):
        v=pcbnew.PCB_VIA(self.b); v.SetPosition(V(*at)); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(LAY[l1],LAY[l2])
        v.SetDrill(FM(drill)); v.SetWidth(FM(size)); self.b.Add(v); v.SetNet(self.net(net)); v.SetIsFree(False) if hasattr(v,"SetIsFree") else None; return v
    def footprint(self,ref,fpid,at=(0,0),layer='F.Cu',value=''):
        f=pcbnew.FOOTPRINT(self.b); f.SetReference(ref); f.SetValue(value)
        f.SetFPID(pcbnew.LIB_ID(*fpid.split(':'))); f.SetPosition(V(*at)); self.b.Add(f)
        if layer=='B.Cu': f.Flip(V(*at),pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetAttributes(pcbnew.FP_SMD)
        return f
    def pad(self,fp,num,at,size,layers,net,shape='rect',mask_margin=None,drill=None,attr='smd',rr=None):
        p=pcbnew.PAD(fp); p.SetNumber(num)
        p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT if shape=='roundrect' else (pcbnew.PAD_SHAPE_CIRCLE if shape=='circle' else (pcbnew.PAD_SHAPE_OVAL if shape=='oval' else pcbnew.PAD_SHAPE_RECT)))
        p.SetAttribute({'smd':pcbnew.PAD_ATTRIB_SMD,'npth':pcbnew.PAD_ATTRIB_NPTH,'pth':pcbnew.PAD_ATTRIB_PTH}[attr])
        ls=pcbnew.LSET()
        for l in layers: ls.AddLayer(LAY[l])
        p.SetLayerSet(ls)
        p.SetSize(pcbnew.F_Cu,V(*size)) if hasattr(p,'SetSize') else None
        if drill: p.SetDrillSize(V(drill,drill))
        if rr: p.SetRoundRectRadiusRatio(pcbnew.F_Cu,rr)
        fp.Add(p); p.SetPosition(V(*at))
        if mask_margin is not None: p.SetLocalSolderMaskMargin(FM(mask_margin))
        if net: p.SetNet(self.net(net))
        return p
    def zone(self,pts,layers,net=None,keepout=None,clearance=0.2,minw=0.15,priority=0,thermal=(0.3,0.3),connect='solid'):
        z=pcbnew.ZONE(self.b); ls=pcbnew.LSET()
        for l in layers: ls.AddLayer(LAY[l])
        z.SetLayerSet(ls)
        o=z.Outline(); o.NewOutline()
        for x,y in pts: o.Append(FM(x),FM(y))
        if keepout is not None:
            z.SetIsRuleArea(True)
            z.SetDoNotAllowTracks('tracks' in keepout); z.SetDoNotAllowVias('vias' in keepout); z.SetDoNotAllowPads('pads' in keepout)
            z.SetDoNotAllowZoneFills('copperpour' in keepout); z.SetDoNotAllowFootprints('footprints' in keepout)
        else:
            z.SetNet(self.net(net)); z.SetLocalClearance(FM(clearance)); z.SetMinThickness(FM(minw)); z.SetAssignedPriority(priority)
            z.SetThermalReliefGap(FM(thermal[0])); z.SetThermalReliefSpokeWidth(FM(thermal[1]))
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if connect=='solid' else pcbnew.ZONE_CONNECTION_THERMAL)
        self.b.Add(z); return z
    def fill(self):
        self.b.BuildConnectivity(); f=pcbnew.ZONE_FILLER(self.b); f.Fill(self.b.Zones()); self.b.BuildConnectivity()
    def save(self,path):
        self.b.Save(path)

def _savefp(self,fp,name,lib='/work/r4/footprints/SmartVioV26.pretty'):
    import copy
    f2=pcbnew.FOOTPRINT(fp); f2.SetPosition(V(0,0)) if False else None
    f2.SetFPID(pcbnew.LIB_ID('',name))
    pcbnew.FootprintSave(lib,f2)
B.savefp=_savefp
def _arc(self,s,m,e,layer='Edge.Cuts',w=0.05):
    a=pcbnew.PCB_SHAPE(self.b); a.SetShape(pcbnew.SHAPE_T_ARC); a.SetArcGeometry(V(*s),V(*m),V(*e)); a.SetLayer(LAY[layer]); a.SetWidth(FM(w)); self.b.Add(a); return a
B.arc=_arc
def fp_rect(fp,x0,y0,x1,y1,layer,w=0.05,fill=False):
    s=pcbnew.PCB_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetStart(V(x0,y0)); s.SetEnd(V(x1,y1)); s.SetLayer(LAY[layer]); s.SetWidth(FM(w)); s.SetFilled(fill); fp.Add(s); return s
def fp_poly(fp,pts,layer,w=0.05):
    for i in range(len(pts)):
        s=pcbnew.PCB_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*pts[i])); s.SetEnd(V(*pts[(i+1)%len(pts)])); s.SetLayer(LAY[layer]); s.SetWidth(FM(w)); fp.Add(s)
def tracklen(pts):
    return sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts[:-1],pts[1:]))
