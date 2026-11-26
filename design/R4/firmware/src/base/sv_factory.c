#include "sv_factory.h"
#include <string.h>
void sv_factory_init(sv_factory *d,uint32_t faults){memset(d,0,sizeof(*d));d->faults=faults;}
void sv_factory_fault(sv_factory *d,uint32_t f){d->faults|=f;d->armed=false;d->programming=false;d->port=0;d->window=false;sv_ui_enable(&d->ui,false);sv_session_end(&d->session);}
void sv_factory_product_arm(sv_factory *d,uint8_t port,uint32_t now){
    d->faults=0;d->product=true;d->grants=SV_D_POWER|SV_D_ADC|SV_D_LINE|SV_D_HP|SV_D_SPK|SV_D_RF;
    d->armed=true;d->programming=false;d->window=false;d->armed_at=d->last_command=now;
    d->port=port;d->mode=2;
    sv_session_end(&d->session);sv_session_begin_trusted(&d->session,SV_PRODUCT_SESSION);d->session.have_seq=true;
}
void sv_factory_tick(sv_factory *d,bool chord,bool rails,bool sensor,uint32_t now){
    if(d->armed && (!rails || !sensor))sv_factory_fault(d,!rails?SV_D_FAULT_POWER:SV_D_FAULT_SENSOR);
    if(d->faults || d->shutdown)return;
    if(d->programming){if(now-d->armed_at>=300000){d->armed=false;d->programming=false;sv_session_end(&d->session);}return;}
    if(!chord){d->holding=false;d->chord_used=false;}
    else if(!d->holding){d->holding=true;d->held_at=now;}
    else if(!d->chord_used && !d->window && !d->armed && now-d->held_at>=1500){
        d->nonce=now^0x53562601u;if(!d->nonce)d->nonce=1;
        d->opened_at=now;d->window=true;d->chord_used=true;
    }
    if(d->window && now-d->opened_at>=60000){d->window=false;d->armed=false;d->port=0;sv_session_end(&d->session);}
    if(d->armed && !d->product && (now-d->armed_at>=60000 || now-d->last_command>=2000)){
        d->armed=false;d->port=0;sv_ui_enable(&d->ui,false);sv_session_end(&d->session);
    }
}
sv_result sv_factory_command(sv_factory *d,const sv_frame *f,uint32_t now){
    if(f->type==0x30)return f->length?SV_LENGTH:SV_OK;
    if(f->type==0x33){if(f->length)return SV_LENGTH;d->armed=false;d->programming=false;d->port=0;d->window=false;sv_ui_enable(&d->ui,false);sv_session_end(&d->session);return SV_OK;}
    if(d->faults || d->shutdown)return SV_NOT_READY;
    if(f->type==0x3b){
        if(f->length!=1 || f->payload[0]!=SV_D_POWER)return SV_RANGE;
        if(d->armed || !d->window || now-d->opened_at>=60000 || f->session_id!=d->nonce)return SV_PHYSICAL;
        d->programming=true;d->armed=true;d->armed_at=now;d->window=false;d->grants=SV_D_POWER;d->port=d->mode=0;
        sv_ui_enable(&d->ui,false);sv_session_begin_trusted(&d->session,f->session_id);
        d->session.have_seq=true;d->session.last_seq=f->seq;return SV_OK;
    }
    if(d->programming)return SV_NOT_READY;
    if(f->type==0x31){
        if(f->length!=1)return SV_LENGTH;
        if(!d->window || now-d->opened_at>=60000 || f->session_id!=d->nonce)return SV_PHYSICAL;
        if(!(f->payload[0]&SV_D_POWER) || (f->payload[0]&~63u))return SV_RANGE;
        d->grants=f->payload[0];d->armed=true;d->armed_at=now;d->last_command=now;d->window=false;d->port=d->mode=d->input=0;sv_ui_enable(&d->ui,false);
        sv_session_begin_trusted(&d->session,f->session_id);d->session.have_seq=true;d->session.last_seq=f->seq;return SV_OK;
    }
    if(!d->armed || !d->session.authorized || f->session_id!=d->session.session_id)return SV_AUTH;
    uint16_t delta=(uint16_t)(f->seq-d->session.last_seq);
    if(!delta || delta>=32768)return SV_REPLAY;
    if(f->type==0x32){
        if(f->length!=3)return SV_LENGTH;
        uint8_t port=f->payload[0],mode=f->payload[1],input=f->payload[2];
        if((port!=0 && port!=SV_LINE && port!=SV_HP && port!=SV_SPK && port!=SV_BT) || mode>2 || input>4)return SV_RANGE;
        uint8_t grant=port==SV_LINE?SV_D_LINE:port==SV_HP?SV_D_HP:port==SV_SPK?SV_D_SPK:port==SV_BT?SV_D_RF:0;
        if(port && !(d->grants&grant))return SV_PHYSICAL;
        if(mode==2 && !(d->grants&SV_D_ADC))return SV_PHYSICAL;
        d->port=port;d->mode=mode;d->input=input;
    }else if(f->type==0x3a){
        if(f->length!=1)return SV_LENGTH;
        if(f->payload[0]>1)return SV_RANGE;
        if(f->payload[0] && !d->ui.fresh)return SV_NOT_READY;
        sv_ui_enable(&d->ui,f->payload[0]!=0);d->port=0;
    }else if(f->type==0x34){if(f->length)return SV_LENGTH;}
    else return SV_AUTH;
    d->session.last_seq=f->seq;d->last_command=now;return SV_OK;
}
unsigned sv_factory_buttons(sv_factory *d,uint8_t pressed,uint32_t now){
    uint32_t e=sv_ui_tick(&d->ui,pressed,d->armed && !d->faults && !d->shutdown && !d->programming,now);
    if(e&(1u<<SV_UI_FX))d->ui.fx=!d->ui.fx;
    if(e&(1u<<(8+SV_UI_FX)))d->ui.rate=(d->ui.rate+1)%3;
    if(e&(1u<<(8+SV_UI_MODE)))d->ui.muted=!d->ui.muted;
    if(e&(1u<<SV_UI_MODE)){
        static const uint8_t ports[5]={0,SV_HP,SV_LINE,SV_SPK,SV_BT};
        static const uint8_t grants[5]={0,SV_D_HP,SV_D_LINE,SV_D_SPK,SV_D_RF};
        unsigned index=0;for(unsigned i=1;i<5;i++)if(d->port==ports[i])index=i;
        for(unsigned n=1;n<=5;n++){unsigned i=(index+n)%5;if(!i || (d->grants&grants[i])){d->port=ports[i];break;}}
    }
    if(e&(1u<<SV_UI_MIX))d->input=d->input==0?1:d->input==1?4:0;
    if(e&(1u<<(8+SV_UI_MIX)))d->input=0;
    /* R4 product: the BT key works in every route (1=short: BT on/off, 2=long: pairing window). */
    if(d->product && (d->grants&SV_D_RF)){
        if(e&(1u<<SV_UI_BT))return 1;
        if(e&(1u<<(8+SV_UI_BT)))return 2;
        return 0;
    }
    if(d->port==SV_BT && (d->grants&SV_D_RF)){
        if(e&(1u<<SV_UI_BT))return 1;
        if(e&(1u<<(8+SV_UI_BT)))return 2;
    }
    return 0;
}
int32_t sv_sample24(uint32_t word){uint32_t v=word>>8;return (v&0x800000u)?(int32_t)v-16777216:(int32_t)v;}
static int32_t limit(int32_t v,int32_t cap){return v>cap?cap:v< -cap? -cap:v;}
void sv_factory_render(sv_factory *d,const uint32_t *a,const uint32_t *b,uint32_t *dac,uint32_t *spk,size_t frames,uint32_t *phase){
    static const int16_t sine[48]={0,67,133,196,256,312,362,406,443,473,495,508,512,508,495,473,443,406,362,312,256,196,133,67,0,-67,-133,-196,-256,-312,-362,-406,-443,-473,-495,-508,-512,-508,-495,-473,-443,-406,-362,-312,-256,-196,-133,-67};
    if(!d || !dac || !spk || !phase || frames>128)return;
    float mono[128];
    for(size_t n=0;n<frames;n++){
        int32_t l=0,r=0;
        if(d->armed && !d->faults && d->port && d->mode==1){l=r=sine[*phase%48]*256;*phase=(*phase%48+1)%48;}
        else if(d->armed && !d->faults && d->port && d->mode==2 && a && b){
            /* PCM-01: was /16 (-24 dB); now -6 dB headroom, pickup gain comes from the PGA. */
            int32_t pickup=sv_sample24(a[2*n])/2,rl=sv_sample24(a[2*n+1])/2,rr=sv_sample24(b[2*n])/2;
            if(d->input==0){l=r=pickup;}else if(d->input==1){l=rl;r=rr;}else if(d->input==2){l=r=rl;}else if(d->input==3){l=r=rr;}else {l=pickup/2+rl/2;r=pickup/2+rr/2;}
        }
        l=limit(l,8388607);r=limit(r,8388607);
        if(d->armed && !d->faults && d->port && d->mode){
            if(!sv_ui_process(&d->ui,&l,&r))sv_factory_fault(d,SV_D_FAULT_DMA);
        }else {d->ui.gain=0;memset(d->ui.filter,0,sizeof(d->ui.filter));}
        if(d->port==SV_SPK){mono[n]=(l/2+r/2)/8388608.0f;spk[2*n]=spk[2*n+1]=0;dac[2*n]=dac[2*n+1]=0;}
        else {dac[2*n]=(uint32_t)l*256u;dac[2*n+1]=(uint32_t)r*256u;spk[2*n]=spk[2*n+1]=0;}
    }
    if(d->port==SV_SPK && d->armed && !d->faults && d->mode){
        if(!sv_speaker_process(&d->speaker,mono,spk,frames,5500))sv_factory_fault(d,SV_D_FAULT_DMA);
    }else sv_speaker_reset(&d->speaker);
}
