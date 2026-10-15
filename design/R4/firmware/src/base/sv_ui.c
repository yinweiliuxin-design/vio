#include "sv_ui.h"
#include "dsp/filtering_functions.h"
#include <string.h>
#include <math.h>
void sv_ui_init(sv_ui *u){memset(u,0,sizeof(*u));}
void sv_ui_enable(sv_ui *u,bool enable){
    u->enabled=enable;u->picked_up=false;u->muted=false;u->gain=0;u->phase=0;
    for(unsigned i=0;i<4;i++)u->buttons[i].released=false;
    memset(u->filter,0,sizeof(u->filter));
}
bool sv_ui_pots(sv_ui *u,const uint32_t raw[3],uint32_t now){
    for(unsigned i=0;i<3;i++)if(raw[i]>4095){u->fresh=false;u->picked_up=false;return false;}
    for(unsigned i=0;i<3;i++)u->pots[i]=(uint16_t)raw[i];
    u->sampled=now;u->generation++;u->fresh=true;
    /* R4 product: no 'roll VOL to zero first' pickup after a stale scan. */
    if(u->enabled && (raw[0]<=64 || u->auto_pickup))u->picked_up=true;
    return true;
}
uint32_t sv_ui_tick(sv_ui *u,uint8_t pressed,bool authorized,uint32_t now){
    uint32_t events=0;
    if(now-u->sampled>100){u->fresh=false;u->picked_up=false;u->gain=0;}
    if((pressed&3u)==3u)u->chord_lock=true;
    for(unsigned i=0;i<4;i++){
        sv_button *b=&u->buttons[i];bool raw=(pressed&(1u<<i))!=0;
        if(raw!=b->raw){b->raw=raw;b->changed=now;}
        if(now-b->changed>=30){
            if(!raw && !b->down)b->released=true;
            if(raw!=b->down){
                b->down=raw;
                if(raw){b->pressed=now;b->long_sent=false;}
                else {if(b->released && !b->long_sent)events|=1u<<i;b->released=true;}
            }
            if(b->down && b->released && !b->long_sent && now-b->pressed>=1500){b->long_sent=true;events|=1u<<(8+i);}
        }
    }
    if(u->chord_lock){events&=~0x303u;if(!(pressed&3u) && !u->buttons[0].down && !u->buttons[1].down)u->chord_lock=false;}
    if(!authorized || !u->enabled)events=0;
    if(events)u->events++;
    return events;
}
bool sv_ui_audible(const sv_ui *u){return !u->enabled || (u->fresh && u->picked_up && !u->muted);}
bool sv_ui_process(sv_ui *u,int32_t *l,int32_t *r){
    if(!u->enabled)return true;
    if(!sv_ui_audible(u)){*l=*r=0;u->gain=0;memset(u->filter,0,sizeof(u->filter));return true;}
    /* 1kHz/48kHz Butterworth LPF, bilinear transform; CMSIS positive feedback.
     * TONE crossfades this dark response with dry. FX is bounded tremolo. */
    static const float coeff[5]={0.003916127f,0.007832253f,0.003916127f,1.815341083f,-0.831005589f};
    float target=u->pots[0]/4095.0f;target*=target;
    u->gain+=(target-u->gain)*(1.0f/512.0f);
    u->tone+=(u->pots[1]/4095.0f-u->tone)*(1.0f/512.0f);
    u->depth+=(u->pots[2]/4095.0f-u->depth)*(1.0f/512.0f);
    static const uint32_t periods[3]={24000,9600,6000};uint32_t period=periods[u->rate%3];
    u->phase=(u->phase+1)%period;
    float triangle=2.0f*(float)(u->phase<period/2?u->phase:period-u->phase)/(float)period;
    float modulation=u->fx?1.0f-u->depth*triangle:1.0f;
    int32_t *channels[2]={l,r};
    for(unsigned c=0;c<2;c++){
        float dry=(float)*channels[c],wet;
        arm_biquad_casd_df1_inst_f32 f={.numStages=1,.pState=u->filter[c],.pCoeffs=coeff};
        arm_biquad_cascade_df1_f32(&f,&dry,&wet,1);
        float sample=(wet+(dry-wet)*u->tone)*u->gain*modulation;
        if(!isfinite(sample)){*l=*r=0;u->picked_up=false;return false;}
        if(sample>8388607.0f)sample=8388607.0f;
        if(sample< -8388608.0f)sample=-8388608.0f;
        *channels[c]=(int32_t)sample;
    }
    return true;
}
void sv_pot_init(sv_pot_scan *s,sv_pot_bus bus,uint32_t now){memset(s,0,sizeof(*s));s->bus=bus;s->next=now;}
void sv_pot_tick(sv_pot_scan *s,uint32_t now){
    if(s->fault)return;
    if(s->pending){
        uint32_t raw[3];int state=s->bus.poll(s->bus.ctx,raw);
        if(state<0 || now-s->at>=5){s->fault=true;s->valid=false;s->pending=false;s->bus.stop(s->bus.ctx);return;}
        if(state>0){
            s->bus.stop(s->bus.ctx);s->pending=false;
            for(unsigned i=0;i<3;i++)if(raw[i]>4095){s->fault=true;s->valid=false;return;}
            memcpy(s->raw,raw,sizeof(raw));s->valid=true;s->generation++;s->sampled=now;s->next=now+20;
        }
    }else if((int32_t)(now-s->next)>=0){
        if(!s->bus.start(s->bus.ctx)){s->fault=true;s->valid=false;return;}
        s->pending=true;s->at=now;
    }
    if(s->valid && now-s->sampled>100){s->fault=true;s->valid=false;s->bus.stop(s->bus.ctx);}
}
