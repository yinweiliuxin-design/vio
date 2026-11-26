# render.py board out.png x0 y0 x1 y1 scale(px/mm) layers(comma) [highlight nets comma]
import sys; sys.path.insert(0,'/work/scripts')
from lib import *
from PIL import Image, ImageDraw, ImageFont
b=pcbnew.LoadBoard(sys.argv[1]); out=sys.argv[2]
x0,y0,x1,y1=map(float,sys.argv[3:7]); s=float(sys.argv[7]); layers=sys.argv[8].split(',')
hl=sys.argv[9].split(',') if len(sys.argv)>9 and sys.argv[9] else []
W=int((x1-x0)*s); H=int((y1-y0)*s)
img=Image.new('RGB',(W,H),(255,255,255)); d=ImageDraw.Draw(img)
def P(x,y): return ((x-x0)*s,(y-y0)*s)
LC=[(200,60,60),(60,60,200),(60,150,60),(180,120,0),(150,0,150),(0,150,150),(100,100,100),(220,0,220)]
cols={}
for i,n in enumerate(hl): cols[n]=LC[i%len(LC)]
lids=[L(b,l) for l in layers]
def colfor(net,base):
    return cols.get(net,base)
# zones
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    for li in lids:
        if z.IsOnLayer(li):
            fp_=z.GetFilledPolysList(li)
            for k in range(fp_.OutlineCount()):
                o=fp_.Outline(k); pts=[P(mm(o.CPoint(j).x),mm(o.CPoint(j).y)) for j in range(o.PointCount())]
                if len(pts)>2: d.polygon(pts,fill=(235,235,215))
for f in b.GetFootprints():
    for p in f.Pads():
        if not any(p.IsOnLayer(li) for li in lids): continue
        li=[l for l in lids if p.IsOnLayer(l)][0]
        sh=p.GetEffectivePolygon(li,pcbnew.ERROR_INSIDE)
        c=colfor(p.GetNetname(),(150,150,150))
        for k in range(sh.OutlineCount()):
            o=sh.Outline(k); pts=[P(mm(o.CPoint(j).x),mm(o.CPoint(j).y)) for j in range(o.PointCount())]
            if len(pts)>2: d.polygon(pts,fill=tuple(min(255,v+60) for v in c),outline=(0,0,0))
        if s>=40:
            q=P(mm(p.GetPosition().x),mm(p.GetPosition().y)); d.text((q[0]-3,q[1]-5),p.GetNumber(),fill=(0,0,0))
for t in b.GetTracks():
    n=t.GetNetname(); c=colfor(n,(120,120,120))
    if t.Type()==pcbnew.PCB_VIA_T:
        x,y=P(mm(t.GetPosition().x),mm(t.GetPosition().y)); r=mm(t.GetWidth(pcbnew.F_Cu))/2*s
        d.ellipse((x-r,y-r,x+r,y+r),fill=c,outline=(0,0,0))
        if s>=60: d.text((x+r,y-r),n[:10],fill=(200,0,0))
        continue
    if t.GetLayer() not in lids: continue
    if len(lids)>1 and t.GetLayer()!=lids[0]: c=tuple(int(v*0.5+127) for v in c)
    w=max(1,int(mm(t.GetWidth())*s))
    a=P(mm(t.GetStart().x),mm(t.GetStart().y)); e=P(mm(t.GetEnd().x),mm(t.GetEnd().y))
    d.line([a,e],fill=c,width=w); r=w/2
    if s>=60 and t.GetLength()>1.5e6: d.text(((a[0]+e[0])/2,(a[1]+e[1])/2),n[:10],fill=(0,0,150))
    for q in (a,e): d.ellipse((q[0]-r,q[1]-r,q[0]+r,q[1]+r),fill=c)
# courtyards + refs
for f in b.GetFootprints():
    side='F' if f.GetLayer()==pcbnew.F_Cu else 'B'
    if not any(l.startswith(side) for l in layers): continue
    bb=f.GetCourtyard(pcbnew.F_CrtYd if side=='F' else pcbnew.B_CrtYd).BBox()
    if bb.GetWidth()>0:
        d.rectangle([P(mm(bb.GetX()),mm(bb.GetY())),P(mm(bb.GetRight()),mm(bb.GetBottom()))],outline=(0,160,0))
    c=f.GetPosition(); d.text(P(mm(c.x),mm(c.y)),f.GetReference(),fill=(0,0,0))
# grid
for gx in range(int(x0),int(x1)+1):
    if gx%1==0: d.line([P(gx,y0),P(gx,y0+0.3)],fill=(0,0,0)); d.text(P(gx,y0+0.3),str(gx),fill=(0,0,255)) if gx%2==0 else None
for gy in range(int(y0),int(y1)+1):
    d.line([P(x0,gy),P(x0+0.3,gy)],fill=(0,0,0)); d.text(P(x0+0.35,gy),str(gy),fill=(0,0,255)) if gy%2==0 else None
img.save(out)
