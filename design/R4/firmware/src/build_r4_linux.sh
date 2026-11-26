#!/usr/bin/env bash
# SmartVio STM32H743 firmware: Linux rebuild of build.py (which was Windows-only:
# tcc for host tests, arm-none-eabi-gcc 14.2 for target, absolute E:/ paths).
#
#   ./build_r4_linux.sh [FIRMWARE_ROOT] [OUT_DIR]
#
# FIRMWARE_ROOT defaults to the directory of this script (it must contain base/,
# stm32/, tests/, esp32/ and vendor-source/). OUT_DIR defaults to
# FIRMWARE_ROOT/build-linux. IMAGE (env) selects the ELF base name
# (default smartvio-r4). Same target flags, linker script, vendor sources and
# object list as build.py; host tests use gcc -std=c11 -Wall -Werror instead of
# tcc (the tcc-only -D__GNUC__=9 shim is dropped: gcc defines __GNUC__ itself).
# ESP32: ESP-IDF 5.4.3 is not available here, so only a host -fsyntax-only check
# of the shared r2shared/*.c files is done. The ESP32 image must be rebuilt
# with ESP-IDF by the user.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FW="$(cd "${1:-$HERE}" && pwd)"
OUT="${2:-$FW/build-linux}"
IMAGE="${IMAGE:-smartvio-r4}"
# Extra target/host defines, e.g. EXTRA_CFLAGS="-DHP_DETECT_ACTIVE_HIGH=0" (J301 tip-contact variant)
# or EXTRA_CFLAGS="-DSV_HW_REV_R4=0" (firmware for an R3 board; see base/sv_hw_rev.h).
read -r -a EXTRA <<< "${EXTRA_CFLAGS:-}"
HOSTCC="${HOSTCC:-gcc}"
ARMCC="${ARMCC:-arm-none-eabi-gcc}"
ARMBIN="$(dirname "$(command -v "$ARMCC")")"
BASE="$FW/base"; VENDOR="$FW/vendor-source"
DSP="$VENDOR/cmsis-dsp-1.16.2"; HAL="$VENDOR/stm32h7xx-hal-driver-1.11.4"
mkdir -p "$OUT/obj" "$OUT/host"
LOG="$OUT/build.log"; : > "$LOG"
run(){ echo "+ $*" >>"$LOG"; "$@" >>"$LOG" 2>&1 || { echo "FAILED: $*" >&2; tail -40 "$LOG" >&2; exit 1; }; }

# Portable core (build.py order) + R4 portable modules when present.
CORE=()
for n in sv_control sv_telemetry sv_foundation sv_radio_core sv_factory sv_pcm1864 sv_speaker sv_ui \
         sv_audio_meter sv_input_guard sv27_charge_session sv27_charge_gate sv_product; do
  [ -f "$BASE/$n.c" ] && CORE+=("$BASE/$n.c")
done
CORE+=("$DSP/Source/FilteringFunctions/arm_biquad_cascade_df1_f32.c" "$DSP/Source/FilteringFunctions/arm_biquad_cascade_df1_init_f32.c")
# -Wno-misleading-indentation: gcc-only style warning (tcc has none) hit by one-line test macros.
HOSTW=(-Wall -Werror -Wno-misleading-indentation)
COMMON=(-std=c11 "${HOSTW[@]}" "${EXTRA[@]}" -D__GNUC_PYTHON__ "-I$BASE" "-I$DSP/Include" "-I$FW/stm32" "-I$FW/esp32/main")

# ---------------------------------------------------------------- host tests
echo "== host tests ($($HOSTCC --version | head -1))"
RESULTS="$OUT/host-tests.txt"; : > "$RESULTS"
host(){ # name exe -- compile args...
  local name="$1" exe="$OUT/host/$1"; shift
  run "$HOSTCC" "$@" -o "$exe" -lm
  local o; o="$("$exe" 2>&1)" || { echo "TEST FAILED: $name" >&2; echo "$o" >&2; exit 1; }
  printf '%s: %s\n' "$name" "$(echo "$o" | tr '\n' ' ' | cut -c1-400)" | tee -a "$RESULTS"
}
for n in legacy_telemetry test_foundation test_radio_core test_diagnostics test_audio_contract test_ui; do
  case "$n" in
    # These suites assert R3 board constants (2.65 divider, EN1 low at boot, 30 unused pins):
    # run them against the R3 board configuration (R4 constants are covered by test_r4_product).
    legacy_telemetry|test_foundation|test_diagnostics) R3HW=(-DSV_HW_REV_R4=0);;
    *) R3HW=();;
  esac
  host "$n" "${COMMON[@]}" "${R3HW[@]}" "${CORE[@]}" "$BASE/tests/$n.c"
done
for f in "$FW"/tests/test_*.c; do
  n="$(basename "$f" .c)"
  case "$n" in test_service_clear) continue;; esac
  host "$n" "${COMMON[@]}" "${CORE[@]}" "$f"
done
for e in 0 1; do
  host "test_service_clear_$e" "${COMMON[@]}" "-DSV_DIAGNOSTIC_SERVICE_CLEAR=$e" "$FW/tests/test_service_clear.c"
done
# i2c-model-device.h: Linux port of generate-i2c-test-header.ps1 (official ST CMSIS types).
cat > "$OUT/gen_i2c_header.py" <<'PY'
import re, sys, hashlib, json, pathlib
src = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
out = pathlib.Path(sys.argv[2])
lines = ['/* GENERATED from pinned official ST CMSIS; host RAM, not hardware. */',
         '#ifndef SV_I2C_MODEL_DEVICE_H', '#define SV_I2C_MODEL_DEVICE_H', '#include <stdint.h>',
         '#define __IO volatile', '#define __I volatile const', '#define __O volatile']
for t in ('I2C_TypeDef', 'GPIO_TypeDef', 'RCC_TypeDef'):
    m = re.search(r'(?si)typedef struct\s*\{(?:(?!typedef struct).)*?\}\s*' + t + r'\s*;', src)
    if not m: raise SystemExit('Missing official type ' + t)
    lines.append(m.group(0))
for l in src.splitlines():
    # PowerShell -match is case-insensitive: _Pos/_Msk helpers are included too.
    if re.match(r'^#define\s+(RCC|I2C)_[A-Z0-9_]+\s+', l, re.I): lines.append(l)
lines += ['extern I2C_TypeDef sv_fake_i2c;', 'extern GPIO_TypeDef sv_fake_gpiob;', 'extern RCC_TypeDef sv_fake_rcc;',
          '#define I2C1 (&sv_fake_i2c)', '#define GPIOB (&sv_fake_gpiob)', '#define RCC (&sv_fake_rcc)',
          'uint32_t sv_i2c_model_status(void);', '#endif']
out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
PY
run python3 -I "$OUT/gen_i2c_header.py" "$VENDOR/st/stm32h743xx.h" "$OUT/i2c-model-device.h"
H=(-std=c11 "${HOSTW[@]}" "${EXTRA[@]}" "-I$BASE" "-I$OUT" "-I$BASE/stm32")
host test_i2c_probe "${H[@]}" -DSV_I2C_REGISTER_MODEL "$BASE/stm32/i2c_probe.c" "$BASE/tests/test_i2c_probe.c"
host test_esp_pcm "${H[@]}" "-I$BASE/tests/esp_model" "$BASE/tests/test_esp_pcm.c"
host test_safety_inputs "${H[@]}" -DSV_SAFETY_REGISTER_MODEL "-I$BASE/tests" "$BASE/sv_input_guard.c" "$BASE/stm32/safety_inputs.c" "$BASE/tests/test_safety_inputs.c"
host test_r2_charge_enabled_HOST_ONLY "${COMMON[@]}" -DSV27_HOST_MODEL_ENABLE "${CORE[@]}" "$FW/tests/test_r2_charge.c"
if [ -f "$BASE/sv_product.c" ]; then
  # R4: J301 detect with the other polarity (DECISIONS Q7, HP_DETECT_ACTIVE_HIGH=0).
  host test_safety_inputs_active_low "${H[@]}" -DHP_DETECT_ACTIVE_HIGH=0 -DSV_SAFETY_REGISTER_MODEL "-I$BASE/tests" \
       "$BASE/sv_input_guard.c" "$BASE/stm32/safety_inputs.c" "$BASE/tests/test_safety_inputs.c"
  # R4 firmware built for an R3 board (SV_HW_REV_R4=0): routes/wake/detect still correct.
  # Charge-release logic with the gate opened (the default image keeps CHARGE_ALLOW low).
  host test_r4_product_charge_release "${COMMON[@]}" -DSV_R4_CHARGE_RELEASE=1 "${CORE[@]}" "$FW/tests/test_r4_product.c"
  host test_r4_product_r3board "${COMMON[@]}" -DSV_HW_REV_R4=0 "${CORE[@]}" "$FW/tests/test_r4_product.c"
  host test_safety_inputs_r3board "${H[@]}" -DSV_HW_REV_R4=0 -DSV_SAFETY_REGISTER_MODEL "-I$BASE/tests" \
       "$BASE/sv_input_guard.c" "$BASE/stm32/safety_inputs.c" "$BASE/tests/test_safety_inputs.c"
fi

# ------------------------------------------------- ESP32 shared code (syntax only)
echo "== ESP32 shared sources: host gcc -fsyntax-only (ESP-IDF not installed)"
for f in "$FW"/esp32/main/r2shared/*.c; do
  run "$HOSTCC" -std=gnu11 -Wall -Werror -fsyntax-only "-I$FW/esp32/main/r2shared" "-I$FW/esp32/main" "-I$BASE/tests/esp_model" "$f"
  echo "syntax OK: esp32/main/r2shared/$(basename "$f")" | tee -a "$RESULTS"
done

# ---------------------------------------------------------------- STM32 target
echo "== target ($($ARMCC --version | head -1))"
FLAGS=(-std=c11 -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard -Os -g3 -ffunction-sections -fdata-sections
       -fno-common -Wall -Wextra -Werror -DSTM32H743xx -DHSE_VALUE=24576000 -DUSE_HAL_DRIVER "${EXTRA[@]}"
       "-I$FW/stm32" "-I$BASE" "-I$BASE/stm32" "-I$VENDOR/st" "-I$VENDOR/cmsis" "-I$HAL/Inc" "-I$DSP/Include")
SRCS=("${CORE[@]}" "$FW/stm32/main.c" "$FW/stm32/fault_store.c")
for n in i2c_probe.c audio_hw.c syscalls.c startup_stm32h743xx.s pot_adc.c safety_inputs.c; do SRCS+=("$BASE/stm32/$n"); done
SRCS+=("$VENDOR/st/system_stm32h7xx.c")
for n in hal hal_rcc hal_rcc_ex hal_gpio hal_dma hal_dma_ex hal_sai hal_sai_ex hal_cortex hal_pwr hal_pwr_ex hal_flash hal_flash_ex hal_iwdg hal_adc hal_adc_ex; do
  SRCS+=("$HAL/Src/stm32h7xx_$n.c")
done
OBJS=()
for s in "${SRCS[@]}"; do
  b="$(basename "$s")"; o="$OUT/obj/${b%.*}.o"
  run "$ARMCC" "${FLAGS[@]}" -c "$s" -o "$o"; OBJS+=("$o")
done
LD="$BASE/stm32/stm32h743vi.ld"
link(){ # elf objs...
  local elf="$1"; shift
  run "$ARMCC" "${FLAGS[@]}" -nostartfiles --specs=nano.specs --specs=nosys.specs "-T$LD" -Wl,--gc-sections \
      "-Wl,-Map=${elf%.elf}.map" "$@" -Wl,--start-group -lc -lm -lgcc -Wl,--end-group -o "$elf"
  run "$ARMBIN/arm-none-eabi-objcopy" -O binary "$elf" "${elf%.elf}.bin"
  run "$ARMBIN/arm-none-eabi-objcopy" -O ihex "$elf" "${elf%.elf}.hex"
  "$ARMBIN/arm-none-eabi-nm" -n "$elf" > "${elf%.elf}.symbols.txt"
  (cd "$(dirname "$elf")" && "$ARMBIN/arm-none-eabi-size" "$(basename "$elf")") | tee -a "$RESULTS"
}
link "$OUT/$IMAGE.elf" "${OBJS[@]}"
# SERVICE variant (SV_DIAGNOSTIC_SERVICE_CLEAR=1 for main.c and fault_store.c), as build.py.
SOBJS=()
for o in "${OBJS[@]}"; do case "$(basename "$o")" in main.o|fault_store.o) ;; *) SOBJS+=("$o");; esac; done
for s in "$FW/stm32/main.c" "$FW/stm32/fault_store.c"; do
  b="$(basename "$s" .c)"; o="$OUT/obj/$b-service.o"
  run "$ARMCC" "${FLAGS[@]}" -DSV_DIAGNOSTIC_SERVICE_CLEAR=1 -c "$s" -o "$o"; SOBJS+=("$o")
done
link "$OUT/$IMAGE-SERVICE.elf" "${SOBJS[@]}"
# CHARGE-TEST variant (SV_R4_CHARGE_RELEASE=1): only for test stage CHARGE after the pack
# NTC curve and B00-B12 are signed off. The default image never drives CHARGE_ALLOW high.
if [ -f "$BASE/sv_product.c" ]; then
  COBJS=()
  for o in "${OBJS[@]}"; do case "$(basename "$o")" in main.o|sv_product.o) ;; *) COBJS+=("$o");; esac; done
  for s in "$FW/stm32/main.c" "$BASE/sv_product.c"; do
    b="$(basename "$s" .c)"; o="$OUT/obj/$b-charge.o"
    run "$ARMCC" "${FLAGS[@]}" -DSV_R4_CHARGE_RELEASE=1 -c "$s" -o "$o"; COBJS+=("$o")
  done
  link "$OUT/$IMAGE-CHARGE-TEST.elf" "${COBJS[@]}"
fi
# Compile check of the board-revision dependent target sources for an R3 board
# (SV_HW_REV_R4=0) and for the SV_PRODUCT_MODE=0 bench flow (objects discarded).
if [ -f "$BASE/sv_hw_rev.h" ]; then
  for d in "-DSV_HW_REV_R4=0" "-DSV_PRODUCT_MODE=0" "-DSV_CPU_FAST_MHZ=200" "-DHP_DETECT_ACTIVE_HIGH=0"; do
    for s in "$FW/stm32/main.c" "$BASE/stm32/safety_inputs.c" "$BASE/stm32/audio_hw.c" "$BASE/sv_telemetry.c" "$BASE/sv_product.c" "$BASE/sv_input_guard.c"; do
      run "$ARMCC" "${FLAGS[@]}" $d -c "$s" -o "$OUT/obj/variant.o"
    done
    echo "target compile OK with $d" | tee -a "$RESULTS"
  done
  rm -f "$OUT/obj/variant.o"
fi
echo "== DONE: host tests + target ELF in $OUT (hardware tests: 0)"
