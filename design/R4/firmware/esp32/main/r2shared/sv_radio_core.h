#ifndef SV_RADIO_CORE_H
#define SV_RADIO_CORE_H
#include "sv_control.h"
typedef struct {
    bool local_window,profile_ready,connected,classic_authenticated,encrypted;
    uint8_t peer[6];
    uint32_t opened_at,faults;
} sv_radio_core;
void sv_radio_init(sv_radio_core *);
/* Trusted local adapter only. Not reachable through UART or BLE. */
bool sv_radio_open_local(sv_radio_core *,const uint8_t peer[6],bool power_qualified,
                         bool physical_window,uint32_t now);
bool sv_radio_window(const sv_radio_core *,uint32_t now);
bool sv_radio_peer(const sv_radio_core *,const uint8_t peer[6]);
void sv_radio_quiesce(sv_radio_core *);
void sv_radio_tick(sv_radio_core *,uint32_t now);
sv_result sv_radio_command(sv_radio_core *,const sv_frame *,uint32_t now);
/* A2DP callback foundation has no I2S capture yet: bounded silence only. */
int32_t sv_radio_silence(uint8_t *,int32_t length);
#endif
