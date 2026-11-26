# fpcroute.sh <board-basename> [passes]
S=/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad; K=$S/kicad/rootfs; n=$1; mp=${2:-30}
chroot $K sh -c "HOME=/tmp python3 /work/scripts/fpc/dsn.py /work/r4/pcb/$n.kicad_pcb /work/view/$n.dsn" 2>&1 | grep -v leak
cp $K/work/view/$n.dsn $S/fpcfr/$n.dsn; cd $S/fpcfr; rm -f $n.ses
timeout 900 java -jar freerouting-2.1.0.jar -de $n.dsn -do $n.ses -mp $mp --gui.enabled=false 2>&1 | grep -E "unrouted" | tail -1
cp $n.ses $K/work/view/$n.ses
chroot $K sh -c "HOME=/tmp python3 /work/scripts/fpc/ses.py /work/r4/pcb/$n.kicad_pcb /work/view/$n.ses" 2>&1 | grep -v leak
