import xml.etree.ElementTree as ET,sys,collections
def load(p):
    r=ET.parse(p).getroot(); comps={}; pins=collections.defaultdict(dict)
    for c in r.find('components'):
        ref=c.get('ref'); fp=c.findtext('footprint'); props={p.get('name'):p.get('value') for p in c.findall('property')}
        comps[ref]=dict(fp=fp,value=c.findtext('value'),props=props)
    for n in r.find('nets'):
        for nd in n.findall('node'): pins[nd.get('ref')][nd.get('pin')]=n.get('name').lstrip('/')
    return comps,pins
if __name__=='__main__':
    comps,pins=load(sys.argv[1])
    for ref in sys.argv[2:]:
        c=comps.get(ref); print(ref, c and c['fp'], c and c['value'], c and {k:v for k,v in c['props'].items() if k in('Board','Endpoint_ID','PCB','Sheetfile','board')})
        print('   ',sorted(pins[ref].items(),key=lambda x:(len(x[0]),x[0])))
