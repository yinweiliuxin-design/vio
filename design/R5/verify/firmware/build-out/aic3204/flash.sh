#!/bin/sh
# Flash the R5 bench firmware (aic3204 default codec). Usage: ./flash.sh [PORT]
# Needs esptool (pip install esptool). Port of the DevKitC-1 "USB" connector.
cd "$(dirname "$0")"
PORT=${1:-/dev/ttyACM0}
python -m esptool --chip esp32s3 -p "$PORT" -b 460800 --before default_reset --after hard_reset \
  write_flash --flash_mode dio --flash_size 8MB --flash_freq 80m \
  0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 r5_bench.bin
