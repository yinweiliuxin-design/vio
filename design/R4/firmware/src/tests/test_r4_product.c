/* R4 host tests for the review fixes (portable code only; hardware tests: 0). */
#include "sv_control.h"
#include "sv_factory.h"
#include "sv_product.h"
#include "sv_pcm1864.h"
#include "sv_telemetry.h"
#include "stm32/board_pins.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,groups;
#define C(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL r4 line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
static unsigned feed(sv_parser *p,const uint8_t *b,size_t n,sv_frame *out,uint8_t *types){
    unsigned k=0;sv_frame f;for(size_t i=0;i<n;i++)if(sv_parser_byte(p,b[i],0,&f)){if(out)*out=f;if(types)types[k]=f.type;k++;}return k;
}
int main(void){
    /* FW-PARSER-WHITELIST: every type used by stm32/main.c and smartvio_rf.c round-trips. */
    groups++;
    static const uint8_t used[]={1,2,3,4,5,6,0x20,0x21,0x22,0x30,0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,0x39,0x3a,0x3b,0x3c,
                                 0x40,0x41,0x42,0x43,0x80,0xa0,0xa1,0xb0};
    for(unsigned i=0;i<sizeof(used);i++){
        sv_parser p;sv_parser_reset(&p);sv_frame in={.type=used[i],.seq=(uint16_t)(0x1234+i),.session_id=0x53562601u+i,.length=(uint16_t)(i%10)},out;
        for(unsigned k=0;k<in.length;k++)in.payload[k]=(uint8_t)(k*7+i);
        uint8_t b[270];size_t n=sv_frame_encode(&in,b,sizeof(b));C(n==in.length+14u);
        C(feed(&p,b,n,&out,NULL)==1);C(out.type==in.type && out.seq==in.seq && out.session_id==in.session_id && out.length==in.length);
        C(!memcmp(out.payload,in.payload,in.length));
        b[n-1]^=1;sv_parser_reset(&p);C(feed(&p,b,n,NULL,NULL)==0);
    }
    for(unsigned t=0;t<256;t++){
        bool known=false;for(unsigned i=0;i<sizeof(used);i++)if(used[i]==t)known=true;
        C(sv_frame_type_known((uint8_t)t)==known);
        if(!known){sv_parser p;sv_parser_reset(&p);sv_frame in={.type=(uint8_t)t,.seq=1,.session_id=2};uint8_t b[32];
            size_t n=sv_frame_encode(&in,b,sizeof(b));C(feed(&p,b,n,NULL,NULL)==0);}
    }
    /* stm32/main.c startup_core(): 0x30 self-test frame (17 bytes) now parses (BRINGUP never armed in R3). */
    {sv_parser p;sv_parser_reset(&p);sv_frame in={.type=0x30,.seq=0x1234,.session_id=0x53562601,.length=3,.payload={0,0x53,0x56}},out;
     uint8_t b[270];size_t n=sv_frame_encode(&in,b,sizeof(b));C(n==17);C(feed(&p,b,n,&out,NULL)==1 && out.type==0x30 && !memcmp(out.payload,in.payload,3));}
    /* Realistic MCU<->ESP byte stream with line noise between frames. */
    {uint8_t s[1200];size_t n=0;const uint8_t seq[]={0x40,0xa0,0x41,0xa0,0x22,0xa1,0x30,0xb0,0x43,0xa0};
     for(unsigned i=0;i<sizeof(seq);i++){sv_frame f={.type=seq[i],.seq=(uint16_t)i,.session_id=77,.length=(uint16_t)(seq[i]==0xa1?32:seq[i]==0xa0?9:seq[i]==0x40?6:0)};
        s[n++]=0x00;s[n++]=0x53;s[n++]=0xff; /* noise incl. a lone magic byte */
        n+=sv_frame_encode(&f,s+n,sizeof(s)-n);}
     sv_parser p;sv_parser_reset(&p);uint8_t got[16];C(feed(&p,s,n,NULL,got)==sizeof(seq));C(!memcmp(got,seq,sizeof(seq)));}

    /* FW-PORT-ENABLE-HP: route masks (PA0 DAC, PA1 HP, PA2 SPK, PA3 PORT_ENABLE). */
    groups++;
#if SV_HAS_GROUPED_PORTS
    /* R4 E-03: HP group PD14 only; RET group PD15 only with AUX/RETURN; PA3 only LINE/FX SEND. */
    C(sv_route_outputs(SV_HP,0)==(SV_OUT_DAC|SV_OUT_HP|SV_OUT_HPGRP));
    C(sv_route_outputs(SV_LINE,0)==(SV_OUT_DAC|SV_OUT_PORTS));
    for(uint8_t in=1;in<=4;in++){C(sv_route_outputs(SV_SPK,in)==(SV_OUT_SPK|SV_OUT_RETGRP));C(sv_route_outputs(SV_BT,in)==SV_OUT_RETGRP);
        C(sv_route_outputs(SV_HP,in)==(SV_OUT_DAC|SV_OUT_HP|SV_OUT_HPGRP|SV_OUT_RETGRP));C(sv_route_outputs(SV_LINE,in)==(SV_OUT_DAC|SV_OUT_PORTS|SV_OUT_RETGRP));}
    for(uint8_t in=0;in<5;in++)C(!(sv_route_outputs(SV_HP,in)&SV_OUT_PORTS) && !(sv_route_outputs(SV_SPK,in)&(SV_OUT_PORTS|SV_OUT_HPGRP)));
#else
    /* R3 board: HP route must include PA3 PORT_ENABLE (the R3 HP-silent bug). */
    C(sv_route_outputs(SV_HP,0)==(SV_OUT_DAC|SV_OUT_HP|SV_OUT_PORTS));C(sv_route_outputs(SV_HP,0)==11);
    C(sv_route_outputs(SV_LINE,0)==(SV_OUT_DAC|SV_OUT_PORTS));
    for(uint8_t in=1;in<=4;in++){C(sv_route_outputs(SV_SPK,in)==(SV_OUT_SPK|SV_OUT_PORTS));C(sv_route_outputs(SV_BT,in)==SV_OUT_PORTS);
        C(sv_route_outputs(SV_HP,in)&SV_OUT_PORTS);}
#endif
    C(sv_route_outputs(SV_SPK,0)==SV_OUT_SPK);
    C(sv_route_outputs(SV_BT,0)==0);C(sv_route_outputs(0,1)==0);
    for(uint8_t port=0;port<16;port++)for(uint8_t in=0;in<5;in++){uint8_t m=sv_route_outputs(port,in);C(!((m&SV_OUT_HP) && (m&SV_OUT_SPK)));}

    /* Q7 auto routing on debounced edges. */
    groups++;
    C(sv_hp_auto_route(SV_SPK,false,true)==SV_HP);C(sv_hp_auto_route(SV_HP,true,false)==SV_SPK);
    C(sv_hp_auto_route(SV_LINE,false,true)==SV_LINE);C(sv_hp_auto_route(SV_BT,true,false)==SV_BT);
    C(sv_hp_auto_route(0,false,true)==0);C(sv_hp_auto_route(SV_HP,true,true)==SV_HP);

    /* FW-FAULT-LATCH: product arm, no 2 s/60 s timeout, faults cleared by re-arm. */
    groups++;
    {sv_factory d;sv_factory_init(&d,0);sv_factory_product_arm(&d,SV_SPK,100);
     C(d.armed && d.product && d.mode==2 && d.port==SV_SPK && !d.faults && d.session.authorized);
     C((d.grants&(SV_D_POWER|SV_D_ADC|SV_D_LINE|SV_D_HP|SV_D_SPK|SV_D_RF))==63);
     for(uint32_t t=100;t<=600100;t+=50)sv_factory_tick(&d,false,true,true,t);C(d.armed && d.port==SV_SPK);
     sv_factory_fault(&d,SV_D_FAULT_CODEC);C(!d.armed && d.faults==SV_D_FAULT_CODEC);
     sv_factory_product_arm(&d,SV_HP,700000);C(d.armed && !d.faults && d.port==SV_HP);
     sv_factory b;sv_factory_init(&b,0);b.armed=true;b.armed_at=b.last_command=0;sv_factory_tick(&b,false,true,true,2000);C(!b.armed);}
    C(sv_recover_delay(0)==1000 && sv_recover_delay(1)==2000 && sv_recover_delay(2)==4000 && sv_recover_delay(4)==16000);
    C(sv_recover_delay(5)==30000 && sv_recover_delay(100)==30000 && sv_recover_delay(0xffffffffu)==30000);

    /* FW-NO-UVLO / task 3: PACK filtered, warn 3.45 V (clear 3.55 V), off < 3.30 V for 3 s on battery. */
    groups++;
    {sv_battery b;sv_battery_init(&b);uint32_t g=0,t=0;
     for(int k=0;k<40;k++){sv_battery_update(&b,3700,++g,false,t+=250);}C(b.valid && sv_battery_mv(&b)==3700 && !b.warn && !b.shutdown);
     sv_battery_update(&b,3000,++g,false,t+=250);C(!b.warn && !b.shutdown && sv_battery_mv(&b)>3600); /* one load dip filtered */
     for(int k=0;k<4;k++)sv_battery_update(&b,1500,++g,false,t+=250);C(sv_battery_mv(&b)>3600);      /* implausible ignored */
     for(int k=0;k<40;k++)sv_battery_update(&b,3440,++g,false,t+=250);C(b.warn && !b.shutdown);
     for(int k=0;k<40;k++)sv_battery_update(&b,3520,++g,false,t+=250);C(b.warn);       /* hysteresis */
     for(int k=0;k<40;k++)sv_battery_update(&b,3560,++g,false,t+=250);C(!b.warn);
     for(int k=0;k<60;k++)sv_battery_update(&b,3250,++g,true,t+=250);C(b.warn && !b.shutdown); /* USB: never off */
     uint32_t start=t;bool off=false;
     for(int k=0;k<40 && !off;k++){sv_battery_update(&b,3250,++g,false,t+=250);off=b.shutdown;}
     C(off);
     sv_battery_init(&b);g=0;t=0;for(int k=0;k<20;k++)sv_battery_update(&b,3290,++g,false,t+=250);
     uint32_t first_low=0;sv_battery_init(&b);g=0;t=0;
     for(int k=0;k<100;k++){sv_battery_update(&b,3290,++g,false,t+=250);if(!first_low && b.low_tracking)first_low=t;if(b.shutdown)break;}
     C(b.shutdown && t-first_low>=SV_BAT_OFF_HOLD_MS && t-first_low<SV_BAT_OFF_HOLD_MS+300);
     /* recovery above 3.30 V before the hold time cancels */
     sv_battery_init(&b);g=0;t=0;for(int k=0;k<8;k++)sv_battery_update(&b,3290,++g,false,t+=250);
     for(int k=0;k<20;k++)sv_battery_update(&b,3400,++g,false,t+=250);C(!b.shutdown && !b.low_tracking);(void)start;}

    /* FW-NO-CHARGE-PATH: USB500 default, charge only with VBUS/no fault/plausible pack/board temp. */
    groups++;
    {sv_charge c={0};sv_charge_in i={.vbus=true,.frame_valid=true,.pack_mv=3800,.board_deci_c=250};
     sv_charge_out o=sv_charge_decide(&c,&i,0);C(o.allow==(SV_R4_CHARGE_RELEASE && o.qualified));C(o.en1 && !o.en2 && !o.qualified);
     o=sv_charge_decide(&c,&i,1999);C(!o.qualified);o=sv_charge_decide(&c,&i,2000);C(o.qualified && o.en1 && !o.en2);
     sv_charge_in j=i;j.port_fault=true;o=sv_charge_decide(&c,&j,2001);C(!o.qualified && !o.en1 && !o.en2);
     o=sv_charge_decide(&c,&i,2002);C(!o.qualified); /* re-qualify 2 s after any veto */
     o=sv_charge_decide(&c,&i,4002);C(o.qualified);C(o.allow==(SV_R4_CHARGE_RELEASE!=0)); /* locked unless released */
     for(unsigned k=0;k<8;k++){sv_charge cc={0};sv_charge_in x=i;
        switch(k){case 0:x.vbus=false;break;case 1:x.frame_valid=false;break;case 2:x.efuse_fault=true;break;case 3:x.system_fault=true;break;
                  case 4:x.pack_mv=4250;break;case 5:x.pack_mv=2400;break;case 6:x.board_deci_c=451;break;case 7:x.board_deci_c=-1;break;}
        for(uint32_t t=0;t<5000;t+=10)C(!sv_charge_decide(&cc,&x,t).qualified);}
     sv_charge cc={0};sv_charge_in s=i;s.service_image=true;o=sv_charge_decide(&cc,&s,9000);C(!o.qualified && !o.allow && !o.en1 && !o.en2);}

    /* FW-USB-SHUTDOWN-LATCH: KILL 1.5 s, then (still alive => USB) standby with KILL released; wake. */
    groups++;
    {sv_power p={0};C(!sv_power_kill(&p,false,0));C(sv_power_kill(&p,true,10));C(sv_power_kill(&p,true,1509));
     C(!sv_power_kill(&p,true,1510) && p.state==SV_PWR_STANDBY);C(!sv_power_kill(&p,true,99999));
     C(!sv_power_standby_wake(&p,false,false,true));
     C(sv_power_standby_wake(&p,false,false,false)); /* VBUS gone but alive */
#if SV_HAS_PWR_PB_SENSE
     C(!sv_power_standby_wake(&p,true,true,true)); /* R4: INT/keys do not wake, PB12 does */
     /* E-11: the key that caused the shutdown is still held -> no wake until released. */
     C(!sv_power_pb_wake(&p,true,2000));C(!sv_power_pb_wake(&p,true,3000));
     C(!sv_power_pb_wake(&p,false,3001));C(!sv_power_pb_wake(&p,true,3002));C(!sv_power_pb_wake(&p,true,3051));
     C(sv_power_pb_wake(&p,true,3052));
     C(!sv_power_pb_wake(&p,false,3060));C(!sv_power_pb_wake(&p,true,3061));C(!sv_power_pb_wake(&p,false,3100)); /* 40 ms bounce */
#else
     C(sv_power_standby_wake(&p,true,false,true));C(sv_power_standby_wake(&p,false,true,true));
#endif
     sv_power r={0};C(!sv_power_standby_wake(&r,true,true,false));C(!sv_power_pb_wake(&r,true,0));}

    /* E-02 / E-04 board constants. */
    groups++;
    C(sv_mon_divider_x1000(SV_MON_USB)==2650 && sv_mon_divider_x1000(SV_MON_ISET)==1000);
#if SV_HW_REV_R4
    C(sv_mon_divider_x1000(SV_MON_BAT)==2687 && sv_mon_divider_x1000(SV_MON_SYS)==2687 && SV_MON_SETTLE_MS>=100);
    {uint32_t uv=(uint32_t)((9826ull*2687u*1000000u+4000000u)/8000000u);C(uv/1000==3300);} /* 3.30 V pack code */
    C((SV_E_BOOT_BSRR&SV_PE_EN1) && (SV_E_BOOT_BSRR&(SV_PE_EN2<<16)) && (SV_E_BOOT_BSRR&(SV_PE_CHARGE<<16)));
    C(!(SV_UNUSED_B&(1u<<12)) && !(SV_UNUSED_D&(3u<<14)));
#else
    C(sv_mon_divider_x1000(SV_MON_BAT)==2650 && (SV_E_BOOT_BSRR&(SV_PE_EN1<<16)));
#endif
    C(!(SV_E_BOOT_BSRR&SV_PE_EN2)); /* EN2 never high: ILIM (1.03 A) mode never selected */

    /* LEDs (FW-UNUSED-STATUS-IO part). */
    groups++;
    {sv_led_in l={.pack_mv=4000,.show_until=5000};C(sv_led_pattern(&l,0)==7);C(sv_led_pattern(&l,5000)==0);
     l.pack_mv=3700;C(sv_led_pattern(&l,0)==3);l.pack_mv=3500;C(sv_led_pattern(&l,0)==1);
     l.warn=true;C(sv_led_pattern(&l,50)==1 && sv_led_pattern(&l,500)==0);
     l.fault=true;C(sv_led_pattern(&l,0)==0 && sv_led_pattern(&l,125)==4);
     sv_led_in u={.usb=true,.charging=true,.pack_mv=3700};C(sv_led_pattern(&u,0)==1 && sv_led_pattern(&u,500)==3);}

    /* R4 product BT key: short = BT route on/off, long >= 2 s = pairing window (existing 0x36 -> 0x40). */
    groups++;
    {sv_factory d;sv_factory_init(&d,0);sv_factory_product_arm(&d,SV_SPK,0);sv_ui_enable(&d.ui,true);
     uint32_t t=10;unsigned short_a=0,long_a=0;for(unsigned n=0;n<50;n++)C(!sv_factory_buttons(&d,0,t++)); /* key seen released first */
     for(unsigned n=0;n<100;n++){unsigned a=sv_factory_buttons(&d,8,t++);if(a==1)short_a++;if(a==2)long_a++;}
     for(unsigned n=0;n<100;n++){unsigned a=sv_factory_buttons(&d,0,t++);if(a==1)short_a++;if(a==2)long_a++;}
     C(short_a==1 && long_a==0); /* short press in SPK route still reported (R3 needed port==BT) */
     unsigned at=0;for(unsigned n=0;n<2100 && !long_a;n++){unsigned a=sv_factory_buttons(&d,8,t);if(a==2){long_a++;at=n;}t++;}
     C(long_a==1 && at>=2000 && at<2040);for(unsigned n=0;n<100;n++)C(sv_factory_buttons(&d,0,t++)!=1); /* release after long: no short */
     sv_factory b;sv_factory_init(&b,0);b.armed=true;b.grants=63;b.port=SV_SPK;sv_ui_enable(&b.ui,true);t=10;unsigned any=0;for(unsigned n=0;n<50;n++)any|=sv_factory_buttons(&b,0,t++);
     for(unsigned n=0;n<100;n++)any|=sv_factory_buttons(&b,8,t++);for(unsigned n=0;n<100;n++)any|=sv_factory_buttons(&b,0,t++);
     C(!any);} /* bench (non-product) keeps the R3 rule */
    {sv_bt_ui b={0};const uint8_t zero[6]={0},ff[6]={255,255,255,255,255,255},peer[6]={0x11,0x22,0x33,0x44,0x55,0x66};
     C(sv_bt_key(&b,2,SV_SPK,0)==SV_SPK && !b.pending);            /* long press without a known peer: no change */
     C(sv_bt_key(&b,1,SV_HP,0)==SV_BT && b.prev_port==SV_HP && !b.pending); /* BT on, nothing to (re)connect */
     C(sv_bt_key(&b,1,SV_BT,5)==SV_HP);                              /* BT off: previous route back */
     sv_bt_learn_peer(&b,zero);sv_bt_learn_peer(&b,ff);C(!b.have_peer);
     sv_bt_learn_peer(&b,peer);C(b.have_peer && !memcmp(b.peer,peer,6));
     C(sv_bt_key(&b,2,SV_LINE,100)==SV_BT && b.pending && b.pending_at==100 && b.prev_port==SV_LINE);
     C(sv_bt_led_state(&b,true,false,200)==SV_BT_LED_BLINK);C(sv_bt_led_state(&b,true,true,200)==SV_BT_LED_ON);
     C(sv_bt_led_state(&b,false,true,200)==SV_BT_LED_OFF);
     b.pending=false;b.window=true;b.window_at=300;C(sv_bt_led_state(&b,true,false,300+SV_BT_WINDOW_MS-1)==SV_BT_LED_BLINK);
     C(sv_bt_led_state(&b,true,false,300+SV_BT_WINDOW_MS)==SV_BT_LED_OFF);
     C(sv_bt_key(&b,1,SV_BT,400)==SV_LINE && !b.pending && !b.window);
     C(sv_bt_key(&b,1,0,500)==SV_BT && b.pending);C(sv_bt_key(&b,1,SV_BT,600)==SV_SPK); /* from "off": back to SPK */
     sv_led_in l={.pack_mv=4000,.bt=SV_BT_LED_ON};C(sv_led_pattern(&l,10000)==2);
     l.bt=SV_BT_LED_BLINK;C(sv_led_pattern(&l,10000)==0 && sv_led_pattern(&l,10500)==2);
     l.show_until=20000;C(sv_led_pattern(&l,10000)==5 && sv_led_pattern(&l,10500)==7);}

    /* PCM-01 pickup PGA constant: +12 dB = 0x18 (0.5 dB steps). */
    groups++;C(SV_PCM_PICKUP_PGA_REG==(SV_PCM_PICKUP_PGA_DB*2));
#if SV_PCM_PICKUP_PGA_DB==12
    C(SV_PCM_PICKUP_PGA_REG==0x18);
#endif
    printf("{\"suite\":\"r4_product\",\"groups\":%u,\"assertions\":%u,\"hw_rev_r4\":%d,\"charge_release\":%d,\"hardware_tests\":0}\n",groups,checks,SV_HW_REV_R4,SV_R4_CHARGE_RELEASE);
    return 0;
}
