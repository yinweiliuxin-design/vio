#ifndef SV_INPUT_GUARD_H
#define SV_INPUT_GUARD_H
#include <stdbool.h>
#include <stdint.h>
#include "sv_hw_rev.h"
/* R4 DECISIONS Q7: J301 headphone-detect polarity on PA4 (HP_DETECT_GPIO).
 *   1 (default) = plug inserted reads HIGH: R323 0R fitted, J301 pins 5-6 are a
 *                 separate normally-closed switch that opens on insertion.
 *   0           = plug inserted reads LOW: R323 not fitted, pin 5 touches the
 *                 tip and is pulled low through the headphone coil.
 * Flip with -DHP_DETECT_ACTIVE_HIGH=0 (build_r4_linux.sh: EXTRA_CFLAGS) or edit
 * the default below, after the one-minute multimeter check on the first sample. */
#ifndef HP_DETECT_ACTIVE_HIGH
#define HP_DETECT_ACTIVE_HIGH 1
#endif
static inline bool sv_hp_inserted_from_pin(bool pin_high){return HP_DETECT_ACTIVE_HIGH?pin_high:!pin_high;}
/* Q7: 200 ms debounce on both edges. Speaker is still cut on the first raw
 * insertion edge; headphone/speaker route changes follow the debounced state. */
enum {SV_PWR_STARTUP_IGNORE_MS=1000,SV_PWR_INT_MIN_MS=26,
      SV_SAFETY_SAMPLE_MS=1,SV_PWR_LEVEL_FILTER_MS=2,
      SV_HP_INSERT_DEBOUNCE_MS=200,SV_HP_RELEASE_GUARD_MS=200};
typedef char sv_assert_int_filter_fits[
    (SV_PWR_LEVEL_FILTER_MS+SV_SAFETY_SAMPLE_MS<SV_PWR_INT_MIN_MS)?1:-1];
/* IRQ writers have the same preemption priority; main reads volatile fields.
 * Final GPIO commit masks IRQs and rechecks raw input as well as these flags. */
typedef struct {
    volatile uint32_t boot_at,hp_changed,power_low_at,power_edges,ignored_edges;
    volatile bool armed,shutdown,hp_seen,hp_raw,hp_inserted,hp_clear,power_tracking;
} sv_input_guard;
void sv_input_guard_init(sv_input_guard *,uint32_t boot_at);
void sv_input_power_edge(sv_input_guard *,uint32_t now);
void sv_input_observe_hp(sv_input_guard *,bool hp_raw_inserted,uint32_t now);
void sv_input_guard_tick(sv_input_guard *,bool hp_raw_inserted,bool power_low,uint32_t now);
bool sv_input_speaker_allowed(const sv_input_guard *,bool hp_raw_inserted);
bool sv_input_headphone_allowed(const sv_input_guard *,bool hp_raw_inserted);
uint8_t sv_input_output_mask(const sv_input_guard *,uint8_t desired,bool hp_raw_inserted);
void sv_input_guard_rearm(sv_input_guard *,uint32_t now);
#endif
