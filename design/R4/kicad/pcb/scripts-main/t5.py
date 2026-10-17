import pcbnew
f=pcbnew.FOOTPRINT(None)
print([m for m in dir(f) if 'ield' in m or 'DNP' in m or 'BOM' in m or 'Sheet' in m or 'Path' in m])
print([m for m in dir(pcbnew.PCB_FIELD) if not m.startswith('_')][:20])
import inspect
print(pcbnew.PCB_FIELD.__init__.__doc__)
