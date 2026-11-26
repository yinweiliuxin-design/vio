#ifndef SV_BOARD_PINS_H
#define SV_BOARD_PINS_H
#include <stdint.h>
#include <stdbool.h>
#include "sv_hw_rev.h"
#define SV_PE_BOOT (1u<<7)
#define SV_PE_USB_DISABLE (1u<<10)
#define SV_PE_EN1 (1u<<12)
#define SV_PE_EN2 (1u<<13)
#define SV_PE_CHARGE (1u<<14)
#define SV_PE_AUDIO_POWER (1u<<2)
#define SV_PC_AUDIO_BUS (1u<<13)
/* BSRR low16=set, high16=reset. CE gate LOW independently disables charging. */
#if SV_EN1_DEFAULT_HIGH
/* R4 E-04: EN2/EN1=0/1 (USB500) from reset; EN2 is never driven high. */
#define SV_E_BOOT_BSRR (SV_PE_BOOT|SV_PE_USB_DISABLE|SV_PE_EN1|((SV_PE_EN2|SV_PE_CHARGE|SV_PE_AUDIO_POWER)<<16))
#else
#define SV_E_BOOT_BSRR (SV_PE_BOOT|SV_PE_USB_DISABLE|((SV_PE_EN1|SV_PE_EN2|SV_PE_CHARGE|SV_PE_AUDIO_POWER)<<16))
#endif
#define SV_E_MUTE_BSRR (SV_PE_USB_DISABLE|(SV_PE_CHARGE<<16))
#define SV_E_SAFE_MODE_MASK ((3u<<4)|(3u<<14)|(3u<<20)|(3u<<24)|(3u<<26)|(3u<<28))
#define SV_E_SAFE_MODE_BITS ((1u<<4)|(1u<<14)|(1u<<20)|(1u<<24)|(1u<<26)|(1u<<28))
#define SV_RF_SETTLE_MS 5u
#define SV_RF_RESET_WAIT_MS 30u
#define SV_PC_RF (1u<<5)
#define SV_C_RF_OFF_BSRR ((SV_PC_RF|SV_PC_AUDIO_BUS)<<16)
/* Only the32 unused digital GPIOs. PC2_C/PC3_C analog pads are excluded. */
#define SV_UNUSED_A ((1u<<8)|(1u<<10)|(1u<<15))
#if SV_HAS_PWR_PB_SENSE
#define SV_UNUSED_B ((1u<<2)|(0x1fu<<3)|(0xeu<<12)) /* R4 E-11: PB12 = PWR_PB_SENSE */
#else
#define SV_UNUSED_B ((1u<<2)|(0x1fu<<3)|(0xfu<<12))
#endif
#define SV_UNUSED_C ((7u<<10)|(3u<<14))
#if SV_HAS_GROUPED_PORTS
#define SV_UNUSED_D 0xffu /* R4 E-03: PD14/PD15 drive the HP/RET PhotoMOS groups */
#else
#define SV_UNUSED_D (0xffu|(3u<<14))
#endif
#define SV_UNUSED_E 3u
static inline uint32_t sv_gpio_mode_mask(uint16_t pins){
    uint32_t mask=0;
    for(unsigned p=0;p<16;p++)if(pins&(1u<<p))mask|=3u<<(p*2);
    return mask;
}
typedef struct {bool enabled,low_tracked;uint32_t enabled_at,low_at;} sv_rf_guard;
/* Board adapter must apply returned state to PC5. Timing is not authorization. */
static inline bool sv_rf_request(sv_rf_guard *g,bool high,bool qualified,uint32_t now){
    if(!high || !qualified){
        if(g->enabled || !g->low_tracked)g->low_at=now;
        g->enabled=false;g->low_tracked=true;return false;
    }
    if(!g->enabled && (!g->low_tracked || now-g->low_at<SV_RF_RESET_WAIT_MS))return false;
    if(!g->enabled)g->enabled_at=now;
    g->enabled=true;return true;
}
static inline bool sv_rf_handshake_ready(const sv_rf_guard *g,uint32_t now){
    return g->enabled && now-g->enabled_at>=SV_RF_SETTLE_MS;
}
static inline uint32_t sv_input_mode_bsrr(bool en1,bool en2){
    return (en1?SV_PE_EN1:(SV_PE_EN1<<16))|(en2?SV_PE_EN2:(SV_PE_EN2<<16));
}
typedef struct { uint8_t applied; } sv_input_mode;
/* Reset state00 is established by the early primitive, before C initialization. */
static inline bool sv_input_mode_next(sv_input_mode *state,bool en1,bool en2,uint32_t *write){
    uint8_t next=(uint8_t)((en1?1:0)|(en2?2:0));
    if(next==state->applied)return false;
    *write=sv_input_mode_bsrr(en1,en2);state->applied=next;return true;
}
#endif
