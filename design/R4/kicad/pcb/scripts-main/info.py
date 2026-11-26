import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1])
print("fps",len(b.GetFootprints()),"tracks",len(b.GetTracks()),"zones",b.GetAreaCount(),"nets",b.GetNetCount())
ds=b.GetDesignSettings()
print("bbox",b.GetBoardEdgesBoundingBox().GetOrigin(),b.GetBoardEdgesBoundingBox().GetEnd())
ncs=ds.m_NetSettings
for name,nc in ncs.GetNetclasses().items():
    print("NC",name,nc.GetTrackWidth(),nc.GetClearance(),nc.GetViaDiameter(),nc.GetViaDrill())
for z in b.Zones():
    print("Z",z.GetNetname(),[b.GetLayerName(l) for l in z.GetLayerSet().Seq()],z.GetIsRuleArea(),z.GetBoundingBox().GetOrigin(),z.GetBoundingBox().GetEnd())
