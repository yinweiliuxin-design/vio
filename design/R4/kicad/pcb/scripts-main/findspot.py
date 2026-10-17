# findspot.py REF SIDE(F|B) cx cy radius step rots(comma) [nmax] [clearance_extra]
import sys,math; sys.path.insert(0,'/work/scripts')
from lib import *
b=load(); ref=sys.argv[1]; side=sys.argv[2]; cx,cy,R,st=map(float,sys.argv[3:7]); rots=[float(r) for r in sys.argv[7].split(',')]
nmax=int(sys.argv[8]) if len(sys.argv)>8 else 8
ext=float(sys.argv[9]) if len(sys.argv)>9 else 0.0
f=fp(b,ref)
if (side=='B')!=f.IsFlipped(): f.Flip(f.GetPosition(),pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
CY=pcbnew.B_CrtYd if side=='B' else pcbnew.F_CrtYd
win=pcbnew.BOX2I(pt(cx-R-5,cy-R-5),pcbnew.VECTOR2I(int((2*R+10)*MM),int((2*R+10)*MM)))
obs=[t for t in b.GetTracks() if t.GetBoundingBox().Intersects(win)]
obs+=[p for g in b.GetFootprints() if g.GetReference()!=ref for p in g.Pads() if p.GetBoundingBox().Intersects(win)]
PWR_IN=('VBUS_RAW','USB_5V_SAFE')
OB={}
for o in obs:
    for li in (pcbnew.F_Cu,pcbnew.B_Cu):
        if o.IsOnLayer(li):
            bb=o.GetBoundingBox(); OB.setdefault(li,[]).append((bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom(),o.GetEffectiveShape(li),o.GetNetname()))
cysb=[]
for g in b.GetFootprints():
    if g.GetReference()!=ref and g.IsFlipped()==(side=='B') and g.GetBoundingBox().Intersects(win):
        c=g.GetCourtyard(CY)
        if c.OutlineCount(): cysb.append((pcbnew.SHAPE_POLY_SET(c),c.BBox()))
ra=[z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowFootprints()]
padnets=[(p.GetNumber(),p.GetNetname()) for p in f.Pads()]
res=[]
n=int(R/st)
for i in range(-n,n+1):
    for j in range(-n,n+1):
        x=cx+i*st; y=cy+j*st
        d=math.hypot(x-cx,y-cy)
        if d>R: continue
        for r in rots:
            f.SetPosition(pt(x,y)); f.SetOrientationDegrees(r)
            mc=f.GetCourtyard(CY); bb=mc.BBox()
            if bb.GetX()<0.3e6 or bb.GetY()<0.3e6 or bb.GetRight()>74.3e6 or bb.GetBottom()>42.3e6: continue
            if any(z.IsOnLayer(f.GetLayer()) and z.Outline().Collide(pcbnew.VECTOR2I(int(x*MM),int(y*MM))) for z in ra): continue
            bad=False
            for c,cb in cysb:
                if not cb.Intersects(bb): continue
                a=pcbnew.SHAPE_POLY_SET(mc); a.BooleanIntersection(c)
                if a.Area()>1000: bad=True;break
            if bad: continue
            for p in f.Pads():
                li=pcbnew.B_Cu if side=='B' else pcbnew.F_Cu
                if not p.IsOnLayer(li): continue
                sh=p.GetEffectiveShape(li); pb=p.GetBoundingBox(); pb.Inflate(int(0.6*MM))
                px0,py0,px1,py1=pb.GetX(),pb.GetY(),pb.GetRight(),pb.GetBottom(); pn=p.GetNetname()
                for (ox0,oy0,ox1,oy1,osh,on) in OB.get(li,[]):
                    if ox1<px0 or ox0>px1 or oy1<py0 or oy0>py1: continue
                    if on==pn and pn!='': continue
                    c_=0.2 if (pn in PWR_IN or on in PWR_IN) else 0.15
                    if sh.Collide(osh,int((c_+ext)*MM)): bad=True;break
                if bad: break
            if not bad: res.append((d,x,y,r))
res.sort()
for r_ in res[:nmax]: print('OK %.2f  %.3f %.3f rot %g'%r_)
if not res: print('none')
