#include "sv_pcm1864.h"
#include <string.h>
/* TI SLAS831D: masked page0 configuration; page1 indirect 4.20 coefficients.
 * No coefficient access without running audio clocks. All outputs stay muted. */
static const uint8_t cfg[][3]={
    {0x71,0x8f,0x0f},{0x05,0x41,0},{0x01,0xff,SV_PCM_PICKUP_PGA_REG},{0x02,0xff,0},
    {0x03,0xff,0},{0x04,0xff,0},{0x06,0xbf,1},{0x07,0xbf,1},
    {0x08,0xbf,4},{0x09,0xbf,0},{0x0b,0x1f,0},{0x0c,3,0},
    {0x0d,0xff,0},{0x10,0xf0,0x50},{0x15,0x20,0x20},{0x20,0xf1,0x41}
};
static bool rd(sv_pcm1864 *p,uint8_t r,uint8_t *v){
    if(!p->bus.read || !p->bus.read(p->bus.ctx,r,v)){p->fault|=SV_PCM_BUS;return false;}return true;
}
static bool wr(sv_pcm1864 *p,uint8_t r,uint8_t v){
    if(!p->bus.write || !p->bus.write(p->bus.ctx,r,v)){p->fault|=SV_PCM_BUS;return false;}return true;
}
void sv_pcm_start(sv_pcm1864 *p,sv_codec_bus b,uint32_t now){memset(p,0,sizeof(*p));p->bus=b;p->at=now;}
static uint8_t coefficient(unsigned i){return (i==0 || i==7 || i==14 || i==21)?0x10:0;}
void sv_pcm_tick(sv_pcm1864 *p,uint32_t now){
    uint8_t v=0;
    if(p->ready || p->fault)return;
    if(now-p->at>10000){p->fault|=SV_PCM_TIMEOUT;return;}
    /* PCM-02: no reset pin/brown-out detector (SLAS831D p79): software reset
     * 0x00=0xFE, wait >=1 ms (2 ticks), then page 0, before any configuration. */
    if(p->phase==0){
        if(p->sub==0){if(wr(p,0,0xfe)){p->reset_at=now;p->sub=1;}return;}
        if(now-p->reset_at<2)return;
        if(wr(p,0,0)){p->sub=0;p->phase=1;}return;
    }
    if(p->phase==1){
        const uint8_t *c=cfg[p->index];
        if(p->sub==0){
            if(!rd(p,c[0],&p->old))return;
            if(c[0]>=6 && c[0]<=9 && !(p->old&0x40)){p->fault|=SV_PCM_RESERVED;return;}
        }else if(p->sub==1){if(!wr(p,c[0],(uint8_t)((p->old&~c[1])|c[2])))return;}
        else {if(!rd(p,c[0],&v))return;
            if((v&c[1])!=c[2] || (c[0]>=6 && c[0]<=9 && !(v&0x40))){p->fault|=SV_PCM_READBACK;return;}}
        if(++p->sub==3){p->sub=0;if(++p->index==sizeof(cfg)/sizeof(cfg[0])){p->index=0;p->phase=2;}}
        return;
    }
    if(p->phase==2){if(!wr(p,0,1))return;if(++p->sub==3){p->sub=0;p->phase=3;}return;}
    if(p->phase==3){if(!rd(p,1,&v))return;if(v&7){p->phase=2;return;}p->phase=4;return;}
    if(p->phase==4){
        const uint8_t regs[]={2,4,5,6,1};
        uint8_t values[]={p->index,coefficient(p->index),0,0,1};
        if(!wr(p,regs[p->sub],values[p->sub]))return;
        if(++p->sub==5){p->sub=0;p->phase=5;}return;
    }
    /* Refresh the arbiter through two dummy page-select writes after requests. */
    if(p->phase==5 || p->phase==8){if(!wr(p,0,1))return;if(++p->sub==2){p->sub=0;p->phase++;}return;}
    if(p->phase==6){if(!rd(p,1,&v))return;if(v&7){p->phase=5;return;}p->phase=7;return;}
    if(p->phase==7){if(wr(p,1,2))p->phase=8;return;}
    if(p->phase==9){if(!rd(p,1,&v))return;if(v&7){p->phase=8;return;}p->phase=10;return;}
    if(p->phase==10){
        if(!rd(p,(uint8_t)(8+p->sub),&v))return;
        if(v!=(p->sub==0?coefficient(p->index):0)){p->fault|=SV_PCM_READBACK;return;}
        if(++p->sub==3){p->sub=0;if(++p->index==24)p->phase=11;else p->phase=4;}return;
    }
    if(p->phase==11){if(wr(p,0,0)){p->index=0;p->phase=12;}return;}
    if(p->phase==12){
        static const uint8_t r[]={0x72,0x73,0x74,0x75,0x78};
        static const uint8_t mask[]={0x0f,7,0x7f,0xff,7},value[]={0x0f,3,0x34,0,7};
        if(!rd(p,r[p->index],&v))return;
        if((v&mask[p->index])!=value[p->index]){p->fault|=SV_PCM_READBACK;return;}
        if(++p->index==5)p->phase=13;
        return;
    }
    if(p->phase==13){
        /* Leave channel2R muted; don't alter filter or HPF bits. */
        if(p->sub==0){if(!rd(p,0x71,&p->old))return;p->sub=1;}
        else if(p->sub==1){if(wr(p,0x71,(uint8_t)((p->old&~0x8f)|8)))p->sub=2;}
        else {if(!rd(p,0x71,&v))return;if((v&0x8f)!=8)p->fault|=SV_PCM_READBACK;else p->ready=true;}
    }
}
bool sv_pcm_status(sv_pcm1864 *p){
    static const uint8_t r[]={0x72,0x73,0x74,0x75,0x78};
    static const uint8_t mask[]={0x0f,7,0x7f,0xff,7},value[]={0x0f,3,0x34,0,7};
    uint8_t v;
    for(unsigned i=0;i<5;i++){if(!rd(p,r[i],&v))return false;if((v&mask[i])!=value[i]){p->fault|=SV_PCM_READBACK;return false;}}
    return true;
}
