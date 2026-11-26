# rip.py board drc.json types  -> remove tracks/vias referenced by violations of given types; lock remaining tracks
import pcbnew,sys,json
b=pcbnew.LoadBoard(sys.argv[1]); d=json.load(open(sys.argv[2])); types=sys.argv[3].split(',')
ids=set()
for v in d['violations']:
    if v['type'] in types:
        for i in v['items']:
            if i['description'].startswith(('Track','Via','Arc')): ids.add(i['uuid'])
dead=[t for t in b.GetTracks() if t.m_Uuid.AsString() in ids]
for t in dead: b.Remove(t)
for t in b.GetTracks(): t.SetLocked(True)
b.BuildConnectivity(); f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones()); b.Save(sys.argv[1]); print('ripped',len(dead))
