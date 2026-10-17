import sys,json; sys.path.insert(0,'/work/scripts')
from lib import *
from nl import parse
from netsplit import relabel
r4=parse('/work/r4/r4-netlist.xml')
b=load(); print("loaded",flush=True)
LIB='/work/r4/footprints/%s.pretty'
def loadfp(fpid):
    lib,name=fpid.split(':'); f=pcbnew.FootprintLoad(LIB%lib,name)
    f.SetFPID(pcbnew.LIB_ID(lib,name)); return f
REN={'H_AUDIO_1_M':'J3401','H_AUDIO_2_M':'J3403','H_COVER_1_M':'J3405','H_COVER_2_M':'J3407','H_COVER_3_M':'J3409'}
for o,n in REN.items(): fp(b,o).SetReference(n)
# remove obsolete
for ref in ['H_USB_1_M','H_USB_2_M','J1801']:
    b.Delete(fp(b,ref))
def swap(ref,fpid,padmove=None):
    old=fp(b,ref); f=loadfp(fpid); b.Add(f)
    if old.IsFlipped(): f.Flip(f.GetPosition(),pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    f.SetPosition(old.GetPosition()); f.SetOrientation(old.GetOrientation()); f.SetReference(ref)
    b.Delete(old); return f
swap('C1707','SmartVioV25:C_0603_1608Metric'); swap('C320','Passive_V26_ManufacturerLand:CC0603KRX7R7BB104')
# J3403: 4-pad landing, pads 1-3 at R3 positions, pad 4 (GND) east at (46.8,21.3) per ECO L-13
old=fp(b,'J3403'); f=loadfp('SmartVioV25:WirePads_4_P1.5'); f.SetReference('J3403')
b.Add(f); f.SetOrientationDegrees(180)
pos={'1':(45.3,21.3),'2':(43.8,21.3),'3':(42.3,21.3)}
# align pad1..3 by placing footprint so pad2 at 43.8 (pads in local coords)
f.SetPosition(pt(0,0)); loc={p.GetNumber():xy(p.GetPosition()) for p in f.Pads()}
print('wp4 local',loc)
dx=43.8-(loc['1'][0]+loc['2'][0]+loc['3'][0])/3*0  # recompute below
# choose offset so that pad '2' lands at 43.8
f.SetPosition(pt(43.8-loc['2'][0],21.3-loc['2'][1]))
for p in f.Pads():
    if p.GetNumber()=='4': p.SetPosition(pt(46.8,21.3))
print('J3403 pads',{p.GetNumber():xy(p.GetPosition()) for p in f.Pads()})
b.Delete(old)
# new footprints (provisional placement; refined in later steps)
NEWP={'J3411':(36.75,1.25,0,'F'),'U1801':(16.0,5.5,0,'B'),'C1801':(19.0,2.5,0,'B'),'_':0,
 'C1004':(68.3,6.0,90,'F'),'C1109':(64.0,21.5,0,'F'),'D1303':(72.0,26.0,0,'B'),
 'Q1202':(55.0,25.0,0,'B'),'R1212':(53.0,24.0,0,'B'),'R1213':(53.0,25.5,0,'B'),
 'Q1203':(50.0,25.0,0,'B'),'R1214':(48.0,24.0,0,'B'),'R1215':(48.0,25.5,0,'B'),
 'R324':(22.0,20.0,0,'B'),'R704':(14.0,20.0,0,'B')}
OFF=[k for k in NEWP if k not in('J3411','U1801','C1801','_')]
for i_,k in enumerate(OFF): NEWP[k]=(80+ (i_%4)*3, 5+(i_//4)*3, 0, NEWP[k][3])
del NEWP['_']
for ref,(x,y,r,side) in NEWP.items():
    f=loadfp(r4[ref]['fp']); f.SetReference(ref); b.Add(f)
    if side=='B': f.Flip(f.GetPosition(),pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    f.SetPosition(pt(x,y)); f.SetOrientationDegrees(r)
# sync all board footprints with netlist
SKIPF=('Footprint','Datasheet','Description')
changed=set()
for f in b.GetFootprints():
    ref=f.GetReference()
    if ref not in r4: print('NOT IN NETLIST',ref); continue
    c=r4[ref]
    f.SetValue(c['value'])
    for k,v in c['fields'].items():
        if k in SKIPF: continue
        new_=not f.HasField(k)
        f.SetField(k,v)
        if new_:
            fl=f.GetField(k); fl.SetVisible(False); fl.SetLayer(pcbnew.B_Fab if f.IsFlipped() else pcbnew.F_Fab)
    f.SetPath(pcbnew.KIID_PATH(c['tstamps']+c['uuid'][0]))
    if 'Sheetname' in c['props']: f.SetSheetname(c['props']['Sheetname']); f.SetSheetfile(c['props'].get('Sheetfile',''))
    f.SetExcludedFromBOM('exclude_from_bom' in c['props'])
    f.SetDNP('dnp' in c['props'])
    for p in f.Pads():
        num=p.GetNumber()
        if not num: continue
        want=c['pins'].get(num,'')
        if p.GetNetname()!=want:
            changed.add(p.GetNetname()); p.SetNet(net(b,want))
print('nets changed from',sorted(x for x in changed if not x.startswith('unconnected')))
for n in ['SSR_SINK','V3LOAD','DAC_UNMUTE','HP_EN_VALIDATED','SYS']:
    relabel(b,[n])
save(b,fill=False)
