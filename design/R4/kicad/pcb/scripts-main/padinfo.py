import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=pcbnew.LoadBoard(sys.argv[1])
for ref in sys.argv[2].split(','):
    f=fp(b,ref)
    for p in f.Pads():
        bb=p.GetBoundingBox()
        print(ref,p.GetNumber(),p.GetNetname(),xy(p.GetPosition()),'bbox',(round(mm(bb.GetX()),3),round(mm(bb.GetY()),3),round(mm(bb.GetRight()),3),round(mm(bb.GetBottom()),3)),p.GetShape(),'mask',mm(p.GetLocalSolderMaskMargin() or 0) if p.GetLocalSolderMaskMargin() is not None else None)
