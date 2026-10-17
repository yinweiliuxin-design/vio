import xml.etree.ElementTree as ET,json,sys
def parse(fn):
    r=ET.parse(fn).getroot(); comps={}
    for c in r.iter('comp'):
        ref=c.get('ref'); flds={f.get('name'):(f.text or '') for f in c.iter('field')}
        props={p.get('name'):p.get('value') for p in c.findall('property')}
        sp=c.find('sheetpath'); tst=[t.text for t in c.findall('tstamps')] or [c.findtext('tstamp')]
        comps[ref]={'value':c.findtext('value'),'fp':c.findtext('footprint'),'fields':flds,'props':props,'sheet':sp.get('names') if sp is not None else '','tstamps':sp.get('tstamps') if sp is not None else '','uuid':tst,'pins':{}}
    for n in r.iter('net'):
        nm=n.get('name')
        for nd in n.iter('node'):
            if nd.get('ref') in comps: comps[nd.get('ref')]['pins'][nd.get('pin')]=nm
    return comps
