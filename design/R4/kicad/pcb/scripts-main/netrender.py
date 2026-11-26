# netrender.py out.png x0 y0 x1 y1 scale nets
import sys; sys.path.insert(0,'/work/scripts')
from lib import *
from PIL import Image, ImageDraw
b=load(); out=sys.argv[1]; x0,y0,x1,y1,s=map(float,sys.argv[2:7]); nets=sys.argv[7].split(',')
W=int((x1-x0)*s); H=int((y1-y0)*s); img=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(img)
P=lambda x,y:((x-x0)*s,(y-y0)*s)
LCOL={'F.Cu':(220,30,30),'In2.Cu':(30,160,30),'In3.Cu':(200,140,0),'In4.Cu':(0,150,200),'In5.Cu':(160,0,200),'B.Cu':(30,30,220),'In1.Cu':(100,100,100),'In6.Cu':(100,100,100)}
for f in b.GetFootprints():
    for p in f.Pads():
        bb=p.GetBoundingBox(); c=(255,180,180) if not f.IsFlipped() else (180,180,255)
        if p.GetNetname() in nets: c=(255,230,0)
        d.rectangle([P(mm(bb.GetX()),mm(bb.GetY())),P(mm(bb.GetRight()),mm(bb.GetBottom()))],outline=(150,150,150),fill=c if p.GetNetname() in nets else None)
        if p.GetNetname() in nets: d.text(P(mm(p.GetPosition().x),mm(p.GetPosition().y)),f.GetReference()+'.'+p.GetNumber(),fill=(0,0,0))
for t in b.GetTracks():
    if t.GetNetname() not in nets: continue
    if t.Type()==pcbnew.PCB_VIA_T:
        x,y=P(*xy(t.GetPosition())); r=0.2*s; d.ellipse((x-r,y-r,x+r,y+r),outline=(0,0,0),fill=(0,0,0)); continue
    c=LCOL[b.GetLayerName(t.GetLayer())]; d.line([P(*xy(t.GetStart())),P(*xy(t.GetEnd()))],fill=c,width=max(2,int(mm(t.GetWidth())*s)))
    if t.GetLength()>3e6: m=xy(t.GetStart()); e=xy(t.GetEnd()); d.text(P((m[0]+e[0])/2,(m[1]+e[1])/2),t.GetNetname()[:12]+'/'+b.GetLayerName(t.GetLayer())[:3],fill=c)
img.save(out)
