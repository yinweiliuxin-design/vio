# fpcfix.sh board : rip violating tracks, edge-KO, route, remove KO, cleanup danglers, DRC
S=/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad; K=$S/kicad/rootfs; n=$1; P=/work/r4/pcb/$n.kicad_pcb
$S/fpcdrc.sh $n >/dev/null 2>&1
chroot $K sh -c "HOME=/tmp python3 /work/scripts/fpc/rip.py $P /work/r4/drc/$n.drc.json items_not_allowed,hole_clearance,shorting_items,solder_mask_bridge,clearance,copper_edge_clearance,tracks_crossing; HOME=/tmp python3 /work/scripts/fpc/edgeko.py $P $P" 2>&1 | grep -v leak
$S/fpcroute.sh $n 40
chroot $K sh -c "HOME=/tmp python3 /work/scripts/fpc/rmtmp.py $P" 2>&1 | grep -v leak
for i in 1 2 3 4; do $S/fpcdrc.sh $n >/dev/null 2>&1; chroot $K sh -c "HOME=/tmp python3 /work/scripts/fpc/cleanup.py $P /work/r4/drc/$n.drc.json" 2>&1 | grep -v leak | grep -v "cleaned 0"; done
$S/fpcdrc.sh $n 2>/dev/null | head -8
