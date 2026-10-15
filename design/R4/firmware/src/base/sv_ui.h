#ifndef SV_UI_H
#define SV_UI_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
enum { SV_UI_FX, SV_UI_MODE, SV_UI_MIX, SV_UI_BT };
typedef struct { bool raw,down,released,long_sent; uint32_t changed,pressed; } sv_button;
typedef struct {
    sv_button buttons[4];
    uint16_t pots[3]; uint32_t sampled,generation,events;
    bool enabled,fresh,picked_up,muted,fx,chord_lock,auto_pickup;
    uint8_t rate;
    float gain,tone,depth,filter[2][4]; uint32_t phase;
} sv_ui;
void sv_ui_init(sv_ui *);
void sv_ui_enable(sv_ui *,bool);
bool sv_ui_pots(sv_ui *,const uint32_t raw[3],uint32_t now);
uint32_t sv_ui_tick(sv_ui *,uint8_t pressed,bool authorized,uint32_t now);
bool sv_ui_audible(const sv_ui *);
bool sv_ui_process(sv_ui *,int32_t *left,int32_t *right);
/* Each ADC transfer is a complete, normal-mode three-rank DMA sequence. */
typedef struct { bool (*start)(void *); int (*poll)(void *,uint32_t[3]); void (*stop)(void *); void *ctx; } sv_pot_bus;
typedef struct { sv_pot_bus bus; bool pending,fault,valid; uint32_t at,next,sampled,generation,raw[3]; } sv_pot_scan;
void sv_pot_init(sv_pot_scan *,sv_pot_bus,uint32_t now);
void sv_pot_tick(sv_pot_scan *,uint32_t now);
#endif
