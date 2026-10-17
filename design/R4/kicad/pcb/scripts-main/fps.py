import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=pcbnew.LoadBoard(sys.argv[1]); x0,y0,x1,y1=map(float,sys.argv[2:6])
for f in sorted(b.GetFootprints(),key=lambda f:(f.IsFlipped(),f.GetReference())):
    x,y=xy(f.GetPosition())
    if x0<=x<=x1 and y0<=y<=y1:
        cy=f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd).BBox()
        print(f.GetReference(),'B' if f.IsFlipped() else 'F',(x,y),f.GetOrientationDegrees(),f.GetValue()[:20],f.GetFPID().GetUniStringLibItemName(),'cy',(round(mm(cy.GetX()),2),round(mm(cy.GetY()),2),round(mm(cy.GetRight()),2),round(mm(cy.GetBottom()),2)), ' '.join('%s:%s'%(p.GetNumber(),p.GetNetname()) for p in f.Pads())[:200])
