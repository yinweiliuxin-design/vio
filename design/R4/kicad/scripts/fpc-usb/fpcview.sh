#!/bin/sh
K=/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad/kicad/rootfs
mkdir -p $K/work/view; rm -f $K/work/view/v.pdf $K/work/view/v.png
chroot $K sh -c "cd /work/r4/pcb && HOME=/tmp kicad-cli pcb export pdf --mode-single --scale 0 ${4:-} -l '$2' -o /work/view/v.pdf $1.kicad_pcb >/dev/null 2>&1; gs -q -dNOPAUSE -dBATCH -sDEVICE=png16m -r${5:-300} -dEPSCrop -sOutputFile=/work/view/v.png /work/view/v.pdf"
cp $K/work/view/v.png $3
