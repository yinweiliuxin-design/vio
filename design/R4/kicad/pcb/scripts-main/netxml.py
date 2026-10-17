import xml.etree.ElementTree as ET
def load(path):
    t = ET.parse(path).getroot()
    comps = {}
    for c in t.find('components'):
        d = dict(ref=c.get('ref'), value=(c.findtext('value') or ''), footprint=(c.findtext('footprint') or ''))
        d['fields'] = {f.get('name'): (f.text or '') for f in c.iter('field')}
        d['props'] = {p.get('name'): p.get('value') for p in c.findall('property')}
        sp = c.find('sheetpath'); d['sheet'] = sp.get('names') if sp is not None else ''
        d['libsource'] = (c.find('libsource').get('part') if c.find('libsource') is not None else '')
        comps[d['ref']] = d
    nets = {}; pin2net = {}
    for n in t.find('nets'):
        name = n.get('name'); nodes = []
        for nd in n.findall('node'):
            nodes.append((nd.get('ref'), nd.get('pin'), nd.get('pintype') or ''))
            pin2net[(nd.get('ref'), nd.get('pin'))] = name
        nets[name] = nodes
    return comps, nets, pin2net
