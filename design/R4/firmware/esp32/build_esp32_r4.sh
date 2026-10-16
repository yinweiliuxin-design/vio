#!/bin/bash
# SmartVio R4 ESP32 build (ESP-IDF v5.4.3, official espressif/idf:v5.4.3 image rootfs run by chroot).
#
#   ./build_esp32_r4.sh                 build this directory -> ../build/esp32/
#   ./build_esp32_r4.sh --r3 R3_ESP32   rebuild a pristine R3 esp32/ dir with the R3 option set
#                                       (sdkconfig.defaults without the "R4 only" block) and
#                                       compare against R3_ARTIFACTS if given as 3rd arg
#   ./build_esp32_r4.sh --test          host test only (gcc): tests/test_pair.c
#
# Env: IDF_ROOT  rootfs of the extracted image (default: the session scratchpad idf/rootfs)
#      OUT_DIR   output dir (default: ../build/esp32 next to this script)
# Needs root (chroot). /proc and /dev are mounted into the rootfs when missing.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDF_ROOT="${IDF_ROOT:-/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad/idf/rootfs}"
OUT_DIR="${OUT_DIR:-$HERE/../build/esp32}"
MODE="${1:-r4}"

host_test(){
  local t; t="$(mktemp -d)"
  gcc -std=c11 -O2 -Wall -Wextra -Werror -I"$HERE/main" -I"$HERE/main/r2shared" "$HERE/tests/test_pair.c" \
      "$HERE/main/r2shared/sv_radio_core.c" "$HERE/main/r2shared/sv_control.c" -o "$t/test_pair"
  "$t/test_pair"; rm -rf "$t"
}
[ "$MODE" = "--test" ] && { host_test; exit 0; }

[ -x "$IDF_ROOT/opt/esp/idf/tools/idf.py" ] || { echo "ESP-IDF rootfs not found: $IDF_ROOT" >&2; exit 1; }
[ -e "$IDF_ROOT/proc/self" ] || mount -t proc proc "$IDF_ROOT/proc"
[ -e "$IDF_ROOT/dev/null" ]  || mount --bind /dev "$IDF_ROOT/dev"

idf_build(){ # $1 = project dir inside the rootfs (e.g. /work/r4build/esp32)
  chroot "$IDF_ROOT" bash -c "export IDF_PATH=/opt/esp/idf IDF_TOOLS_PATH=/opt/esp
    . /opt/esp/idf/export.sh >/dev/null 2>&1
    cd '$1' && rm -rf build sdkconfig && idf.py -DSV_V26_FW='$1/main/r2shared' build"
}

if [ "$MODE" = "--r3" ]; then
  SRC="${2:?R3 esp32 directory}"; ART="${3:-}"
  W="$IDF_ROOT/work/r3repro"; rm -rf "$W"; mkdir -p "$W"; cp -r "$SRC" "$W/esp32"
  sed '/^# --- R4 only/,/^# --- Kept/{/^CONFIG_/d}' "$HERE/sdkconfig.defaults" > "$W/esp32/sdkconfig.defaults"
  idf_build /work/r3repro/esp32
  B="$W/esp32/build"; ls -l "$B/bootloader/bootloader.bin" "$B/partition_table/partition-table.bin" "$B/smartvio_rf_diag.bin"
  if [ -n "$ART" ]; then
    python3 -I - "$ART" "$B" <<'PY'
import sys,hashlib,os
a,b=sys.argv[1],sys.argv[2]
def rd(p): return open(p,'rb').read()
for rel,mask in (('partition_table/partition-table.bin',[]),
                 ('bootloader/bootloader.bin',[(0x28,0x70)]),        # bootloader desc: idf ver + date/time
                 ('smartvio_rf_diag.bin',[(0x70,0x100)])):          # app desc: time,date,idf ver,elf sha
    x,y=rd(os.path.join(a,rel)),rd(os.path.join(b,rel))
    print(rel,len(x),len(y),'sha256',hashlib.sha256(x).hexdigest()[:16],hashlib.sha256(y).hexdigest()[:16])
    if len(x)!=len(y): print('  SIZE DIFFERS'); continue
    tail=0 if rel.startswith('partition') else 33   # image checksum byte + appended SHA-256
    def m(d):
        d=bytearray(d[:len(d)-tail])
        for s,e in mask: d[s:e]=bytes(e-s)
        return bytes(d)
    n=sum(1 for i,j in zip(x,y) if i!=j)
    print('  bytes differing:',n,'| identical after masking build metadata:',m(x)==m(y))
PY
  fi
  rm -rf "$B/esp-idf" "$B/bootloader/esp-idf"   # keep images, drop ~200 MB of objects
  exit 0
fi

host_test
W="$IDF_ROOT/work/r4build"; rm -rf "$W"; mkdir -p "$W/esp32"
cp -r "$HERE/CMakeLists.txt" "$HERE/sdkconfig.defaults" "$HERE/main" "$W/esp32/"
idf_build /work/r4build/esp32 2>&1 | tee "$W/build.log" | grep -E "warning:|error:|binary size|Project build complete" || true
B="$W/esp32/build"; [ -f "$B/smartvio_rf_diag.bin" ] || { echo "build failed, see $W/build.log" >&2; exit 1; }
mkdir -p "$OUT_DIR"
cp "$B/bootloader/bootloader.bin" "$B/partition_table/partition-table.bin" "$B/smartvio_rf_diag.bin" \
   "$B/smartvio_rf_diag.elf" "$B/smartvio_rf_diag.map" "$W/esp32/sdkconfig" "$OUT_DIR/"
cp "$W/build.log" "$OUT_DIR/esp-build.log"
# flash_args with flat file names (offsets from build/flasher_args.json)
python3 -I - "$B/flasher_args.json" "$OUT_DIR/flash_args" <<'PY'
import json,sys,os
j=json.load(open(sys.argv[1]))
lines=[' '.join(j['write_flash_args'])]
for off,f in sorted(j['flash_files'].items(),key=lambda kv:int(kv[0],16)): lines.append(f'{off} {os.path.basename(f)}')
open(sys.argv[2],'w').write('\n'.join(lines)+'\n')
PY
chroot "$IDF_ROOT" bash -c "export IDF_PATH=/opt/esp/idf IDF_TOOLS_PATH=/opt/esp; . /opt/esp/idf/export.sh >/dev/null 2>&1; xtensa-esp32-elf-size /work/r4build/esp32/build/smartvio_rf_diag.elf" > "$OUT_DIR/size.txt" 2>/dev/null || true
( cd "$OUT_DIR" && sha256sum bootloader.bin partition-table.bin smartvio_rf_diag.bin smartvio_rf_diag.elf > SHA256SUMS )
rm -rf "$B/esp-idf" "$B/bootloader/esp-idf"
echo "== flash (from $OUT_DIR): python -m esptool --chip esp32 -b 460800 write_flash @flash_args"
cat "$OUT_DIR/flash_args" "$OUT_DIR/size.txt" "$OUT_DIR/SHA256SUMS"
