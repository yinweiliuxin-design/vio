import sys,json; sys.path.insert(0,'/work/scripts')
from lib import *
b=load(sys.argv[1] if len(sys.argv)>2 else BOARD)
out={}
for f in b.GetFootprints():
    out[f.GetReference()]={'fpid':f.GetFPID().GetUniStringLibId(),'value':f.GetValue(),'side':'B' if f.IsFlipped() else 'F','pos':xy(f.GetPosition()),'rot':f.GetOrientationDegrees(),
      'pads':{p.GetNumber():p.GetNetname() for p in f.Pads() if p.GetNumber()},'path':f.GetPath().AsString(),'sheet':f.GetSheetname() if hasattr(f,'GetSheetname') else '',
      'fields':{fl.GetName():fl.GetText() for fl in f.GetFields()},'dnp':f.IsDNP(),'nobom':f.IsExcludedFromBOM(),'nopos':f.IsExcludedFromPosFiles()}
json.dump(out,open(sys.argv[-1],'w'),indent=0)
