# fpccopy.sh <basename>... : copy native files + DRC json into repo
S=/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad; K=$S/kicad/rootfs; R=/home/user/vio/design/R4/kicad
mkdir -p $R/pcb $R/drc $R/footprints/SmartVioV26.pretty $R/scripts/fpc-usb
for n in "$@"; do
  for e in kicad_pcb kicad_pro kicad_dru kicad_prl; do [ -f $K/work/r4/pcb/$n.$e ] && cp $K/work/r4/pcb/$n.$e $R/pcb/; done
  [ -f $K/work/r4/drc/$n.drc.json ] && cp $K/work/r4/drc/$n.drc.json $R/drc/
done
for f in NPTH_D4.0_KO5.0 FPC_KEYS6_R4 FPC_USB16 FPC_AUDIO4 FPC_USB16_HotBar_Main_P0.70 NPTH_D1.8_KO4.4 KEEPOUT_D4.4_F NPTH_D1.8 NPTH_D1.5 SLOT_2.5x1.5; do [ -f $K/work/r4/footprints/SmartVioV26.pretty/$f.kicad_mod ] && cp $K/work/r4/footprints/SmartVioV26.pretty/$f.kicad_mod $R/footprints/SmartVioV26.pretty/; done
cp $K/work/scripts/fpc/*.py $K/work/scripts/fpc/*.json $R/scripts/fpc-usb/ 2>/dev/null; cp $S/fpc*.py $S/fpc*.sh $R/scripts/fpc-usb/ 2>/dev/null
ls $R/pcb | wc -l
