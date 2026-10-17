set -e
S=/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad; K=$S/kicad/rootfs
chroot $K sh -c "HOME=/tmp python3 /work/scripts/fpc/build_usb_place.py >/dev/null 2>&1; HOME=/tmp python3 /work/scripts/fpc/build_usb_pre.py; HOME=/tmp python3 /work/scripts/fpc/dsn.py /work/r4/pcb/SmartVio-usb-r4.kicad_pcb /work/view/usb.dsn" 2>&1 | grep -v leak || true
python3 $S/fpcdsn.py $K/work/view/usb.dsn USB_DM_CMC,USB_DM_CONN,USB_DM_MCU,USB_DM_OVP_IN,USB_DM_SYS,USB_DP_CMC,USB_DP_CONN,USB_DP_MCU,USB_DP_OVP_IN,USB_DP_SYS
cp $K/work/view/usb.dsn $S/fpcfr/usb.dsn; cd $S/fpcfr; rm -f usb.ses
timeout 900 java -jar freerouting-2.1.0.jar -de usb.dsn -do usb.ses -mp 40 --gui.enabled=false 2>&1 | grep -E "clearance|total_count|incomplete|unrouted" | head -8
cp usb.ses $K/work/view/usb.ses
chroot $K sh -c "HOME=/tmp python3 /work/scripts/fpc/ses.py /work/r4/pcb/SmartVio-usb-r4.kicad_pcb /work/view/usb.ses" 2>&1 | grep -v leak
