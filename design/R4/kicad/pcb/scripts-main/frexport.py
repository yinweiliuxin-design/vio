import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
for t in b.GetTracks(): t.SetLocked(True)
print(pcbnew.ExportSpecctraDSN(b,'/work/out/fr/main.dsn'))
