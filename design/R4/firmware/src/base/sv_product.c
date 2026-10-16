#include "sv_product.h"
#include "sv_control.h"
#include <string.h>
uint8_t sv_route_outputs(uint8_t port,uint8_t input){
#if SV_HAS_GROUPED_PORTS
    /* R4 E-03: HP -> PD14 only; AUX/RETURN -> PD15; LINE/FX SEND -> PA3. */
    uint8_t aux=input?SV_OUT_RETGRP:0; /* 0=pickup only; 1..4 use AUX/RETURN (J202) */
    if(port==SV_LINE)return SV_OUT_DAC|SV_OUT_PORTS|aux;
    if(port==SV_HP)return SV_OUT_DAC|SV_OUT_HP|SV_OUT_HPGRP|aux;
#else
    /* R3: one PORT_ENABLE (PA3) for all 7 PhotoMOS. */
    uint8_t aux=input?SV_OUT_PORTS:0;
    if(port==SV_LINE)return SV_OUT_DAC|SV_OUT_PORTS;
    if(port==SV_HP)return SV_OUT_DAC|SV_OUT_HP|SV_OUT_PORTS;
#endif
    if(port==SV_SPK)return SV_OUT_SPK|aux;
    if(port==SV_BT)return aux;
    return 0;
}
void sv_battery_init(sv_battery *b){memset(b,0,sizeof(*b));}
uint16_t sv_battery_mv(const sv_battery *b){return (uint16_t)(b->filtered_mv_x8/8u);}
void sv_battery_update(sv_battery *b,uint16_t mv,uint32_t generation,bool usb,uint32_t now){
    /* One sample per monitor frame (~4/s); implausible readings are ignored. */
    if(generation!=b->generation && mv>=2000 && mv<=4500){
        b->generation=generation;
        if(!b->valid){b->valid=true;b->filtered_mv_x8=(uint32_t)mv*8u;}
        else b->filtered_mv_x8=b->filtered_mv_x8-b->filtered_mv_x8/8u+mv; /* tau ~8 frames ~2 s */
    }
    if(!b->valid)return;
    uint16_t f=sv_battery_mv(b);
    if(!b->warn && f<SV_BAT_WARN_MV)b->warn=true;
    else if(b->warn && f>SV_BAT_WARN_CLEAR_MV)b->warn=false;
    /* Shutdown only on battery; with VBUS the charger supplies SYS (DPPM). */
    if(usb || f>=SV_BAT_OFF_MV){b->low_tracking=false;return;}
    if(!b->low_tracking){b->low_tracking=true;b->low_since=now;}
    else if(now-b->low_since>=SV_BAT_OFF_HOLD_MS)b->shutdown=true; /* latched until reboot */
}
sv_charge_out sv_charge_decide(sv_charge *c,const sv_charge_in *i,uint32_t now){
    sv_charge_out o={false,false,false,false};
    bool usb_fault=i->port_fault || i->efuse_fault;
    /* EN2=0/EN1=1: BQ24074 USB500 input limit; any USB fault falls back to USB100. */
    o.en1=!usb_fault && !i->service_image;o.en2=false;
    bool ok=i->vbus && i->frame_valid && !usb_fault && !i->system_fault && !i->service_image &&
        i->pack_mv>=SV_CHG_PACK_MIN_MV && i->pack_mv<SV_CHG_PACK_MAX_MV &&
        i->board_deci_c>=SV_CHG_TEMP_MIN_DECI_C && i->board_deci_c<=SV_CHG_TEMP_MAX_DECI_C;
    if(!ok){c->qualifying=false;return o;}
    if(!c->qualifying){c->qualifying=true;c->since=now;}
    o.qualified=now-c->since>=SV_CHG_QUALIFY_MS;
    o.allow=SV_R4_CHARGE_RELEASE && o.qualified;
    return o;
}
uint32_t sv_recover_delay(uint32_t attempts){
    uint32_t d=SV_RECOVER_FIRST_MS;
    for(uint32_t n=0;n<attempts && d<SV_RECOVER_MAX_MS;n++)d*=2u;
    return d>SV_RECOVER_MAX_MS?SV_RECOVER_MAX_MS:d;
}
uint8_t sv_hp_auto_route(uint8_t port,bool was,bool inserted){
    if(!was && inserted && port==SV_SPK)return SV_HP;
    if(was && !inserted && port==SV_HP)return SV_SPK;
    return port;
}
void sv_bt_learn_peer(sv_bt_ui *b,const uint8_t p[6]){
    unsigned any=0,ff=1;for(unsigned j=0;j<6;j++){any|=p[j];ff&=p[j]==255;}
    if(!any || ff)return; /* same rule as sv_radio_open_local on the ESP */
    memcpy(b->peer,p,6);b->have_peer=true;
}
uint8_t sv_bt_key(sv_bt_ui *b,unsigned action,uint8_t port,uint32_t now){
    if(action==1 && port==SV_BT){b->pending=false;b->window=false;return b->prev_port?b->prev_port:SV_SPK;}
    if(action!=1 && action!=2)return port;
    if(action==2 && !b->have_peer)return port; /* nothing to pair with */
    if(port!=SV_BT)b->prev_port=port;
    if(b->have_peer){b->pending=true;b->pending_at=now;}
    return SV_BT;
}
uint8_t sv_bt_led_state(const sv_bt_ui *b,bool route,bool connected,uint32_t now){
    if(!route)return SV_BT_LED_OFF;
    if(connected)return SV_BT_LED_ON;
    if(b->pending || (b->window && now-b->window_at<SV_BT_WINDOW_MS))return SV_BT_LED_BLINK;
    return SV_BT_LED_OFF;
}
static uint8_t gauge(uint16_t mv){return mv>=3900?7u:mv>=3650?3u:1u;}
uint8_t sv_led_pattern(const sv_led_in *l,uint32_t now){
    if(l->fault)return (now/125u)&1u?4u:0u;                  /* LED3 fast blink: muted/recovering */
    if(l->warn && !l->usb)return now%2000u<100u?1u:0u;        /* LED1 short flash: low battery */
    if(l->usb && l->charging){uint8_t g=gauge(l->pack_mv);     /* top gauge LED blinks 1 Hz */
        uint8_t top=g==7u?4u:g==3u?2u:1u;return (now/500u)&1u?g:(uint8_t)(g&~top);}
    if(l->usb && l->standby)return gauge(l->pack_mv);         /* charged / not charging */
    uint8_t g=(int32_t)(l->show_until-now)>0?gauge(l->pack_mv):0u;/* 5 s gauge after power-on/key */
    if(l->bt==SV_BT_LED_ON)g|=2u;                              /* BT: LED2 solid = connected */
    else if(l->bt==SV_BT_LED_BLINK)g=(uint8_t)(((now/500u)&1u)?(g|2u):(g&~2u)); /* slow blink = pairing */
    return g;
}
bool sv_power_kill(sv_power *p,bool req,uint32_t now){
    if(p->state==SV_PWR_RUN){if(!req)return false;p->state=SV_PWR_KILL;p->kill_at=now;return true;}
    if(p->state==SV_PWR_KILL){
        if(now-p->kill_at<SV_KILL_HOLD_MS)return true;
        p->state=SV_PWR_STANDBY; /* still alive: USB_WAKE keeps V3D on */
    }
    return false;
}
bool sv_power_standby_wake(const sv_power *p,bool pwr_event,bool key,bool vbus){
    if(p->state!=SV_PWR_STANDBY)return false;
    if(!vbus)return true; /* alive without USB: the LTC2954 was turned on */
#if SV_HAS_PWR_PB_SENSE
    (void)pwr_event;(void)key;return false; /* R4: the power key is read on PB12 */
#else
    return pwr_event || key;
#endif
}
bool sv_power_pb_wake(sv_power *p,bool pb_low,uint32_t now){
    if(p->state!=SV_PWR_STANDBY){p->pb_released=false;p->pb_tracking=false;return false;}
    if(!pb_low){p->pb_released=true;p->pb_tracking=false;return false;}
    if(!p->pb_released)return false; /* still the press that switched us off */
    if(!p->pb_tracking){p->pb_tracking=true;p->pb_since=now;}
    return now-p->pb_since>=SV_PB_WAKE_MS;
}
