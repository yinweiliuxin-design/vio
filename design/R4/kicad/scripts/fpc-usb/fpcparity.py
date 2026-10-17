# board-vs-R4-netlist parity for multi-board system: for each footprint on board, compare fpid/value? and pad nets with netlist
import json,sys
sys.path.insert(0,'/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad')
from fpcnet import load
comps,pins=load(sys.argv[1]); brd=json.load(open(sys.argv[2])); issues=[]
for ref,d in sorted(brd.items()):
    if d.get('board_only'): continue
    if ref not in comps: issues.append(('extra_footprint',ref,d['fp'])); continue
    c=comps[ref]
    if c['fp']!=d['fp']: issues.append(('footprint_mismatch',ref,d['fp'],c['fp']))
    if (c['value'] or '')!=(d['value'] or ''): issues.append(('value_mismatch',ref,d['value'],c['value']))
    np=pins.get(ref,{})
    for pn,net in d['pads'].items():
        sn=np.get(pn,'')
        if pn not in np:
            if net: issues.append(('pad_not_in_netlist',ref,pn,net))
        elif sn!=net and not (sn.startswith('unconnected-') and net==''):
            issues.append(('net_mismatch',ref,pn,net,sn))
    for pn in np:
        if pn not in d['pads']: issues.append(('missing_pad',ref,pn,np[pn]))
req=sys.argv[3].split(',') if len(sys.argv)>3 and sys.argv[3] else []
for r in req:
    if r not in brd: issues.append(('missing_footprint',r,comps[r]['fp']))
for i in issues: print(i)
print('PARITY_ISSUES',len(issues))
