# settext.py board REF x y [REF x y ...]
import pcbnew,sys
FM=pcbnew.FromMM
b=pcbnew.LoadBoard(sys.argv[1]); a=sys.argv[2:]
for i in range(0,len(a),3):
    f=b.FindFootprintByReference(a[i]); r=f.Reference(); r.SetPosition(pcbnew.VECTOR2I(FM(float(a[i+1])),FM(float(a[i+2])))); r.SetTextAngleDegrees(0); r.SetTextSize(pcbnew.VECTOR2I(FM(0.8),FM(0.8))); r.SetTextThickness(FM(0.12))
b.Save(sys.argv[1])
