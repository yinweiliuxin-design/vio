# cleanup.py board drc.json -> delete dangling tracks/vias (iterate externally)
import pcbnew,sys,json
b=pcbnew.LoadBoard(sys.argv[1]); d=json.load(open(sys.argv[2])); ids=set()
for v in d['violations']:
    if v['type'] in ('track_dangling','via_dangling'):
        ids.add(v['items'][0]['uuid'])
dead=[t for t in b.GetTracks() if t.m_Uuid.AsString() in ids]
for t in dead: b.Remove(t)
b.BuildConnectivity(); f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones()); b.Save(sys.argv[1]); print('cleaned',len(dead))
