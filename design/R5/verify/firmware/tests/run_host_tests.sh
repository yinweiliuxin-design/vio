#!/usr/bin/env bash
# Build and run the host-side unit tests for the r5dsp library (no ESP-IDF).
# Usage: tests/run_host_tests.sh        (from anywhere)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DSP="$ROOT/components/r5dsp"
OUT="${TMPDIR:-/tmp}/r5_host_tests.$$"
mkdir -p "$OUT"
trap 'rm -rf "$OUT"' EXIT
CC="${CC:-gcc}"
CFLAGS="-std=gnu11 -O2 -g -Wall -Wextra -Werror -Wno-unused-parameter -fno-fast-math"
echo "== compiling with $($CC --version | head -1)"
$CC $CFLAGS -I"$DSP/include" "$DSP"/src/*.c "$HERE/test_host.c" -lm -o "$OUT/test_host"
echo "== running"
"$OUT/test_host"
