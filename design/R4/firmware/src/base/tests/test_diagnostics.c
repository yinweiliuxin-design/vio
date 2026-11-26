#include "sv_factory.h"
#include "sv_pcm1864.h"
#include "stm32/board_pins.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,groups;
#define C(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL diagnostics line%d\n",__LINE__);exit(1);}}while(0)
typedef struct {uint8_t page,r[2][256],coeff[24][3];unsigned ops,fail,resets,reset_op,page0_op;bool stopped,mismatch;} chip;
static bool read_reg(void *ctx,uint8_t r,uint8_t *v){chip *c=ctx;c->ops++;if(c->fail==c->ops)return false;*v=c->r[c->page][r];if(c->mismatch && c->page==1 && r==8)*v^=1;return true;}
static bool write_reg(void *ctx,uint8_t r,uint8_t v){
    chip *c=ctx;c->ops++;if(c->fail==c->ops)return false;
    /* R4 PCM-02: 0x00=0xFE is the software reset (SLAS831D p85). */
    if(!r && v==0xfe){c->resets++;c->reset_op=c->ops;c->page=0;return true;}
    if(!r){if(!c->page0_op)c->page0_op=c->ops;c->page=v;return v<2;}c->r[c->page][r]=v;
    if(c->page==1 && r==1){unsigned a=c->r[1][2];C(a<24);
        if(v==1)memcpy(c->coeff[a],c->r[1]+4,3);
        if(v==2)memcpy(c->r[1]+8,c->coeff[a],3);
        c->r[1][1]=c->stopped?7:0;
    }return true;
}
static void reset(chip *c){memset(c,0,sizeof(*c));for(unsigned r=6;r<=9;r++)c->r[0][r]=0x40;
    c->r[0][5]=0xc6;c->r[0][0xb]=0x60;c->r[0][0x10]=1;c->r[0][0x71]=0x70;
    c->r[0][0x72]=15;c->r[0][0x73]=3;c->r[0][0x74]=0x34;c->r[0][0x78]=7;
}
static void run(sv_pcm1864 *p,chip *c){sv_pcm_start(p,(sv_codec_bus){c,read_reg,write_reg},0);
    for(unsigned t=0;t<=10001 && !p->fault && !p->ready;t++){unsigned before=c->ops;sv_pcm_tick(p,t);C(c->ops-before<=1);}}
static void chord(sv_factory *d,uint32_t at){sv_factory_tick(d,false,true,true,at);sv_factory_tick(d,true,true,true,at+1);sv_factory_tick(d,true,true,true,at+1501);}
int main(void){
    chip c;sv_pcm1864 p;groups++;reset(&c);run(&p,&c);C(p.ready && !p.fault && c.page==0);
    C(c.r[0][5]==0x86 && c.r[0][6]==0x41 && c.r[0][7]==0x41 && c.r[0][8]==0x44 && c.r[0][9]==0x40);
    C(c.r[0][0xb]==0x60 && c.r[0][0x10]==0x51 && c.r[0][0x71]==0x78);
    /* R4 PCM-02: reset is the first operation, page 0 select follows; PCM-01: pickup PGA +12 dB, AUX 0 dB. */
    C(c.resets==1 && c.reset_op==1 && c.page0_op==2);C(c.r[0][1]==0x18 && c.r[0][2]==0 && c.r[0][3]==0 && c.r[0][4]==0);
    for(unsigned i=0;i<24;i++){C(c.coeff[i][0]==((i==0||i==7||i==14||i==21)?16:0));C(!c.coeff[i][1]&&!c.coeff[i][2]);}
    unsigned operations=c.ops;groups++;
    for(unsigned fail=1;fail<=operations;fail++){reset(&c);c.fail=fail;run(&p,&c);C(!p.ready && (p.fault&SV_PCM_BUS));unsigned before=c.ops;sv_pcm_tick(&p,10002);C(c.ops==before);}
    groups++;reset(&c);c.stopped=true;run(&p,&c);C(!p.ready && (p.fault&SV_PCM_TIMEOUT));
    reset(&c);c.mismatch=true;run(&p,&c);C(!p.ready && (p.fault&SV_PCM_READBACK));
    reset(&c);c.r[0][6]=0;run(&p,&c);C(!p.ready && (p.fault&SV_PCM_RESERVED));
    reset(&c);c.r[0][0x75]=1;run(&p,&c);C(!p.ready && (p.fault&SV_PCM_READBACK));
    groups++;sv_factory d;sv_factory_init(&d,0);C(!d.armed&&!d.window&&!d.port);
    sv_frame f={.type=0x31,.seq=1,.session_id=1,.length=1,.payload={63}};
    C(sv_factory_command(&d,&f,0)==SV_PHYSICAL);chord(&d,0);C(d.window);
    f.session_id=d.nonce;C(sv_factory_command(&d,&f,1502)==SV_OK && d.armed);
    f=(sv_frame){.type=0x32,.seq=2,.session_id=d.nonce,.length=3,.payload={SV_SPK,1,0}};
    C(sv_factory_command(&d,&f,1503)==SV_OK);C(sv_factory_command(&d,&f,1503)==SV_REPLAY);
    f.seq=3;f.session_id++;C(sv_factory_command(&d,&f,1503)==SV_AUTH);
    sv_factory_tick(&d,true,true,true,3503);C(!d.armed&&!d.port);
    sv_factory_tick(&d,true,true,true,10000);C(!d.window);chord(&d,10001);C(d.window);
    f=(sv_frame){.type=0x31,.seq=1,.session_id=d.nonce,.length=1,.payload={SV_D_POWER}};
    C(sv_factory_command(&d,&f,11503)==SV_OK);
    f=(sv_frame){.type=0x32,.seq=2,.session_id=d.nonce,.length=3,.payload={SV_SPK,2,0}};
    C(sv_factory_command(&d,&f,11504)==SV_PHYSICAL);sv_factory_tick(&d,false,true,false,11505);C(d.faults&SV_D_FAULT_SENSOR);
    chord(&d,20000);C(!d.armed&&!d.window);sv_factory_init(&d,d.faults);chord(&d,0);C(!d.window);
    groups++;sv_factory_init(&d,0);d.armed=true;d.port=SV_SPK;d.mode=1;uint32_t a[256],b[256],dac[256],spk[256],phase=UINT32_MAX;
    memset(a,0xff,sizeof(a));memset(b,0x80,sizeof(b));
    sv_factory_render(&d,a,b,dac,spk,128,&phase);C(phase<48);
    for(unsigned n=0;n<128;n++){C(dac[2*n]==0 && dac[2*n+1]==0 && spk[2*n+1]==0);C(sv_sample24(spk[2*n])<=3355392 && sv_sample24(spk[2*n])>=-3355392);}
    C(sv_sample24(0x80000000u)==-8388608 && sv_sample24(0x7fffff00u)==8388607);
    for(unsigned input=0;input<4;input++){d.mode=2;d.input=input;sv_factory_render(&d,a,b,dac,spk,128,&phase);for(unsigned n=0;n<128;n++){C(!dac[2*n]&&!dac[2*n+1]&&!spk[2*n+1]);C(sv_sample24(spk[2*n])>=-3355392);}}
    d.port=SV_LINE;d.mode=1;sv_factory_render(&d,a,b,dac,spk,128,&phase);for(unsigned n=0;n<128;n++)C(!spk[2*n]&&!spk[2*n+1]&&dac[2*n]==dac[2*n+1]);
    d.faults=1;sv_factory_render(&d,a,b,dac,spk,128,&phase);for(unsigned n=0;n<256;n++)C(!dac[n]&&!spk[n]);
    groups++;C(!(SV_UNUSED_C&(1u<<13)) && !(SV_UNUSED_E&(1u<<2)) && !(SV_UNUSED_E&(1u<<8)));
    for(unsigned odr=0;odr<65536;odr++){unsigned e=(odr|(SV_E_BOOT_BSRR&65535))&~(SV_E_BOOT_BSRR>>16);C(!(e&(SV_PE_AUDIO_POWER|SV_PE_CHARGE|SV_PE_EN1|SV_PE_EN2)));C(e&SV_PE_BOOT);}
    printf("PASS diagnostics groups=%u assertions=%u PCM_operations=%u hardware_tests=0\n",groups,checks,operations);return 0;
}
