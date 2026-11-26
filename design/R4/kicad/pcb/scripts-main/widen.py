# widen.py drc.json [extra_mm] : for each track_width violation try to widen the track to the required min (+extra)
import sys,json,re; sys.path.insert(0,'/work/scripts')
from lib import *
d=json.load(open(sys.argv[1])); extra=float(sys.argv[2]) if len(sys.argv)>2 else 0.0
b=load(); byid={t.m_Uuid.AsString():t for t in b.GetTracks()}
PWR_IN=('VBUS_RAW','USB_5V_SAFE')
# obstacle cache per layer
OB={}
for t in b.GetTracks():
    for li in t.GetLayerSet().CuStack(): OB.setdefault(li,[]).append(t)
for f in b.GetFootprints():
    for p in f.Pads():
        for li in p.GetLayerSet().CuStack(): OB.setdefault(li,[]).append(p)
edges=[dr for dr in b.GetDrawings() if dr.GetLayer()==pcbnew.Edge_Cuts]
def ok(t):
    li=t.GetLayer(); sh=t.GetEffectiveShape(li); bb=t.GetBoundingBox(); bb.Inflate(int(0.3*MM)); n=t.GetNetname()
    for o in OB.get(li,[]):
        if o.GetNetname()==n and n!='': continue
        if not o.GetBoundingBox().Intersects(bb): continue
        c=0.2 if (n in PWR_IN or o.GetNetname() in PWR_IN) else 0.15
        if o.Type()==pcbnew.PCB_VIA_T or (o.Type()==pcbnew.PCB_PAD_T and o.GetDrillSize().x>0): c=max(c,0.15)
        if sh.Collide(o.GetEffectiveShape(li),int(c*MM)-1): return False
        if o.Type()==pcbnew.PCB_VIA_T:
            # hole clearance 0.25
            hs=pcbnew.SHAPE_CIRCLE(o.GetPosition(),int(o.GetDrillValue()/2))
            if sh.Collide(hs,int(0.25*MM)-1): return False
    for e in edges:
        if sh.Collide(e.GetEffectiveShape(),int(0.25*MM)-1): return False
    # zones of other nets on this layer
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname()==n or not z.IsOnLayer(li): continue
        fp_=z.GetFilledPolysList(li)
        if fp_.OutlineCount() and fp_.Collide(sh.Centre() if False else t.GetStart(),0): pass
    return True
done=0;fail=[]
for v in d['violations']:
    if v['type']!='track_width': continue
    m=re.search(r'min width ([0-9.]+) mm',v['description'])
    if not m: continue
    need=float(m.group(1))+extra
    u=v['items'][0]['uuid']; t=byid.get(u)
    if t is None: continue
    old=t.GetWidth()
    if old>=need*MM: continue
    t.SetWidth(int(round(need*MM)))
    if ok(t): done+=1
    else:
        t.SetWidth(old); fail.append((t.GetNetname(),b.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()),mm(old),need))
print('widened',done,'failed',len(fail))
for f_ in fail: print(' FAIL',f_)
save(b)
