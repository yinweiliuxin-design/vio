#include "sv_input_guard.h"
#include <string.h>
#include <limits.h>
static void arm_after_startup(sv_input_guard *g,uint32_t now){
    if(!g->armed && now-g->boot_at>=SV_PWR_STARTUP_IGNORE_MS)g->armed=true;
}
static void count(volatile uint32_t *n){if(*n!=UINT32_MAX)(*n)++;}
void sv_input_guard_init(sv_input_guard *g,uint32_t boot_at){memset(g,0,sizeof(*g));g->boot_at=boot_at;}
void sv_input_power_edge(sv_input_guard *g,uint32_t now){
    arm_after_startup(g,now);
    if(!g->armed){count(&g->ignored_edges);return;}
    count(&g->power_edges);g->shutdown=true;
}
void sv_input_observe_hp(sv_input_guard *g,bool hp,uint32_t now){
    if(!g->hp_seen || hp!=g->hp_raw){g->hp_seen=true;g->hp_raw=hp;g->hp_changed=now;}
    /* R4: hp_inserted is the debounced state; it only changes after the raw
     * level has been stable for the debounce time (glitches on the tip-contact
     * variant cannot drop the headphone route). */
    if(hp && now-g->hp_changed>=SV_HP_INSERT_DEBOUNCE_MS)g->hp_inserted=true;
    if(!hp && now-g->hp_changed>=SV_HP_RELEASE_GUARD_MS)g->hp_inserted=false;
    g->hp_clear=!hp && !g->hp_inserted && now-g->hp_changed>=SV_HP_RELEASE_GUARD_MS;
}
void sv_input_guard_tick(sv_input_guard *g,bool hp,bool power_low,uint32_t now){
    sv_input_observe_hp(g,hp,now);
    arm_after_startup(g,now);
    /* Level fallback handles INT already LOW at arming. The primary path is
     * EXTI falling-edge latch, so a pulse need not survive main-loop polling. */
    if(!g->armed || !power_low)g->power_tracking=false;
    else if(!g->power_tracking){g->power_tracking=true;g->power_low_at=now;}
    else if(now-g->power_low_at>=SV_PWR_LEVEL_FILTER_MS)g->shutdown=true;
}
bool sv_input_speaker_allowed(const sv_input_guard *g,bool hp){return !g->shutdown && g->hp_seen && g->hp_clear && !g->hp_raw && !g->hp_inserted && !hp;}
bool sv_input_headphone_allowed(const sv_input_guard *g,bool hp){(void)hp;return !g->shutdown && g->hp_seen && g->hp_inserted;}
uint8_t sv_input_output_mask(const sv_input_guard *g,uint8_t desired,bool hp){
    if(g->shutdown)return 0;
    /* bits0-3 PA0..PA3; R4 E-03: bit4 PD14 HP group, bit5 PD15 RET group. */
    desired&=SV_HAS_GROUPED_PORTS?63u:15u;
    if(!sv_input_headphone_allowed(g,hp))desired&=(uint8_t)~16u;
    if(!sv_input_speaker_allowed(g,hp))desired&=(uint8_t)~4u;
    if((desired&2u) && !sv_input_headphone_allowed(g,hp))desired&=(uint8_t)~3u;
    return desired;
}
void sv_input_guard_rearm(sv_input_guard *g,uint32_t now){
    /* R4 FW-USB-SHUTDOWN-LATCH: USB keeps the MCU alive after KILL; clear the
     * PWR latch so the next PWR/INT event is seen (1 s ignore window again). */
    g->shutdown=false;g->armed=false;g->power_tracking=false;g->boot_at=now;
}
