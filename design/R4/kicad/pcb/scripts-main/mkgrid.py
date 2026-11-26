# mkgrid.py board net x0 y0 x1 y1 res width viadia layers(comma) outprefix [extra_ignore_ids_file]
# writes outprefix_<layer>.png (track mask) and outprefix_via.png (via mask); 255 = blocked
import sys,json; sys.path.insert(0,'/work/scripts')
from lib import *
from PIL import Image, ImageDraw
b=pcbnew.LoadBoard(sys.argv[1]); net=sys.argv[2]
x0,y0,x1,y1,res,w,vd=map(float,sys.argv[3:10]); layers=sys.argv[10].split(','); pref=sys.argv[11]
ign=set()
if len(sys.argv)>12:
    ign=set(json.load(open(sys.argv[12])))
W=int(round((x1-x0)/res))+1; H=int(round((y1-y0)/res))+1
PWR_IN=('VBUS_RAW','USB_5V_SAFE')
def clr(other):
    return (0.2 if (net in PWR_IN or other in PWR_IN) else 0.15)+0.03
def P(x,y): return ((x-x0)/res,(y-y0)/res)
def drawpoly(d,ps):
    for k in range(ps.OutlineCount()):
        o=ps.Outline(k); pts=[P(mm(o.CPoint(j).x),mm(o.CPoint(j).y)) for j in range(o.PointCount())]
        if len(pts)>2: d.polygon(pts,fill=255)
        for h in range(ps.HoleCount(k)):
            pass
masks={}
def inflated(item,layer,dist):
    ps=pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps,layer,int(dist*MM),int(0.005*MM),pcbnew.ERROR_OUTSIDE)
    return ps
lids={l:L(b,l) for l in layers}
allcu=[L(b,n) for n in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','In5.Cu','In6.Cu','B.Cu']]
win=pcbnew.BOX2I(pt(x0-2,y0-2),pcbnew.VECTOR2I(int((x1-x0+4)*MM),int((y1-y0+4)*MM)))
items=[]
for t in b.GetTracks():
    if t.GetNetname()==net or str(t.m_Uuid.AsString()) in ign: continue
    if not t.GetBoundingBox().Intersects(win): continue
    items.append(t)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname()==net and net!='': continue
        if not p.GetBoundingBox().Intersects(win): continue
        items.append(p)
zones=[z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname()!=net]
viamask=Image.new('L',(W,H),0); dv=ImageDraw.Draw(viamask)
for ln,li in lids.items():
    im=Image.new('L',(W,H),0); d=ImageDraw.Draw(im)
    for it in items:
        if not it.IsOnLayer(li): continue
        c=clr(it.GetNetname())
        drawpoly(d,inflated(it,li,c+w/2))
    for z in zones:
        if z.IsOnLayer(li):
            ps=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(li)); ps.Inflate(int((0.18+w/2)*MM),pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,int(0.005*MM)) if hasattr(pcbnew,'CORNER_STRATEGY_ROUND_ALL_CORNERS') else ps.Inflate(int((0.18+w/2)*MM),16)
            drawpoly(d,ps)
    masks[ln]=im
# via mask: all copper layers (through via) + holes
for it in items:
    for li in allcu:
        if it.IsOnLayer(li):
            if it.Type()==pcbnew.PCB_ZONE_T: continue
            drawpoly(dv,inflated(it,li,clr(it.GetNetname())+vd/2))
    # hole clearance 0.25
    if it.Type()==pcbnew.PCB_VIA_T or (it.Type()==pcbnew.PCB_PAD_T and it.GetDrillSize().x>0):
        pos=it.GetPosition(); r=(it.GetDrillValue() if it.Type()==pcbnew.PCB_VIA_T else it.GetDrillSize().x)/2/MM
        for (m,rr) in [(dv,r+0.28+vd/2)]+[(ImageDraw.Draw(masks[ln]),r+0.28+w/2) for ln in masks]:
            cx,cy=P(mm(pos.x),mm(pos.y)); R=rr/res; m.ellipse((cx-R,cy-R,cx+R,cy+R),fill=255)
# zones on In1/In6 for via: GND zones get cut by via (antipad) so not blocking.
# board edge
ed=[]
for dr in b.GetDrawings():
    if dr.GetLayer()==pcbnew.Edge_Cuts:
        ed.append(dr)
for dr in ed:
    for (m,rr) in [(dv,0.28+vd/2)]+[(ImageDraw.Draw(masks[ln]),0.28+w/2) for ln in masks]:
        ps=pcbnew.SHAPE_POLY_SET(); dr.TransformShapeToPolygon(ps,pcbnew.Edge_Cuts,int(rr*MM),int(0.005*MM),pcbnew.ERROR_OUTSIDE)
        dd=m
        for k in range(ps.OutlineCount()):
            o=ps.Outline(k); pts=[P(mm(o.CPoint(j).x),mm(o.CPoint(j).y)) for j in range(o.PointCount())]
            if len(pts)>2: dd.polygon(pts,fill=255)
for ln,im in masks.items(): im.save('%s_%s.png'%(pref,ln))
viamask.save('%s_via.png'%pref)
vs=Image.new('L',(W,H),0); dvs=ImageDraw.Draw(vs)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname()==net and p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD and p.GetBoundingBox().Intersects(win):
            for li in (pcbnew.F_Cu,pcbnew.B_Cu):
                if p.IsOnLayer(li): drawpoly(dvs,inflated(p,li,vd/2+0.05))
vs.save('%s_viasame.png'%pref)
# same-net targets: list same-net pads/tracks/vias in window
tg=[]
for t in b.GetTracks():
    if t.GetNetname()==net and t.GetBoundingBox().Intersects(win):
        if t.Type()==pcbnew.PCB_VIA_T: tg.append(['via','*',xy(t.GetPosition()),mm(t.GetWidth(pcbnew.F_Cu))])
        else: tg.append(['trk',b.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()),mm(t.GetWidth())])
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname()==net and p.GetBoundingBox().Intersects(win):
            tg.append(['pad',[b.GetLayerName(l) for l in p.GetLayerSet().CuStack()],xy(p.GetPosition()),f.GetReference()+'.'+p.GetNumber()])
json.dump({'x0':x0,'y0':y0,'res':res,'W':W,'H':H,'layers':layers,'targets':tg},open(pref+'_meta.json','w'))
print('ok',W,H)
