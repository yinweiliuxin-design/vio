#ifndef SV_SAFETY_INPUTS_H
#define SV_SAFETY_INPUTS_H
#include "sv_input_guard.h"
void sv_safety_inputs_init(uint32_t boot_at);
void sv_safety_inputs_tick(uint32_t now);
bool sv_safety_shutdown_requested(void);
bool sv_safety_hp_inserted(void);
void sv_safety_rearm(uint32_t now);
bool sv_safety_speaker_permitted(void);
bool sv_safety_headphone_permitted(void);
uint8_t sv_safety_apply_outputs(uint8_t desired);
#endif
