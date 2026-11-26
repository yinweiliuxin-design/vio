#!/bin/sh
# usage: fpcdrc.sh <basename-without-ext> [extra args]
K=/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad/kicad/rootfs
n=$1; shift
mkdir -p $K/work/r4/drc
chroot $K sh -c "cd /work/r4/pcb && HOME=/tmp kicad-cli pcb drc --format json --severity-all $* -o /work/r4/drc/$n.drc.json $n.kicad_pcb" >/dev/null 2>&1
python3 - $K/work/r4/drc/$n.drc.json <<'PY'
import json,sys,collections
d=json.load(open(sys.argv[1]))
v=d['violations']; u=d['unconnected_items']; p=d.get('schematic_parity',[])
c=collections.Counter((x['severity'],x['type']) for x in v)
print('violations',len(v),dict(c),'unconnected',len(u),'parity',len(p))
for x in v[:12]: print('  ',x['severity'],x['type'],x['description'][:80],[ (i['description'][:50],i['pos']) for i in x['items']][:2])
for x in u[:8]: print('  U',[ (i['description'][:50],i['pos']) for i in x['items']])
PY
