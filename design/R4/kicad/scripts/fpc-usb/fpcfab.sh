# fpcfab.sh <basename> <fabname> <smt:yes|no> <layers>
S=/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad; K=$S/kicad/rootfs
n=$1; fn=$2; smt=$3; L=$4; O=/work/fab/$fn
chroot $K sh -c "rm -rf $O; mkdir -p $O/gerber $O/drill; cd /work/r4/pcb; export HOME=/tmp
kicad-cli pcb export gerbers -l '$L' --subtract-soldermask -o $O/gerber/ $n.kicad_pcb >/dev/null 2>&1 || echo GERBER_FAIL
kicad-cli pcb export drill --format excellon --excellon-separate-th --generate-map --map-format pdf -o $O/drill/ $n.kicad_pcb >/dev/null 2>&1 || echo DRILL_FAIL
[ $smt = yes ] && (kicad-cli pcb export pos --format csv --units mm --side both --exclude-dnp -o $O/$n-pos.csv $n.kicad_pcb >/dev/null 2>&1 || echo POS_FAIL)
kicad-cli pcb export pdf --mode-multipage -l '$L' --cl Edge.Cuts --include-border-title -o $O/$n.pdf $n.kicad_pcb >/dev/null 2>&1 || echo PDF_FAIL
kicad-cli pcb export step --subst-models --include-tracks --include-zones --force -o $O/$n.step $n.kicad_pcb >/dev/null 2>&1 || echo STEP_FAIL
cp /work/r4/drc/$n.drc.json $O/ 2>/dev/null; true"
mkdir -p /home/user/vio/design/R4/kicad/fab; rm -rf /home/user/vio/design/R4/kicad/fab/$fn; cp -r $K/work/fab/$fn /home/user/vio/design/R4/kicad/fab/
cat > /home/user/vio/design/R4/kicad/fab/$fn/README.txt <<EOT
R4 ENGINEERING SAMPLE — NOT RELEASED unless DRC/parity 0
Source: design/R4/kicad/pcb/$n.kicad_pcb (KiCad 10.0.6). DRC report: $n.drc.json in this folder.
Status, open items and supplier confirmations: design/R4/kicad/FPC-USB-CHANGES.md
EOT
ls -R /home/user/vio/design/R4/kicad/fab/$fn | head -40 | tr '\n' ' '; echo
