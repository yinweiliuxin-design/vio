#include "sv_sai_contract.h"
#include "sv_resample.h"
#include "sv_factory.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <limits.h>
static unsigned groups,checks;
#define C(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL audio contract line%d\n",__LINE__);exit(1);}}while(0)
static double response(double hz){
    sv_speaker s;sv_speaker_reset(&s);float f[128];uint32_t out[256];double energy=0;
    for(unsigned n=0;n<48000;n+=128){
        unsigned size=48000-n<128?48000-n:128;
        for(unsigned j=0;j<size;j++)f[j]=(float)(0.01*sin(6.283185307179586*hz*(n+j)/48000));
        C(sv_speaker_process(&s,f,out,size,5500));
        for(unsigned j=0;j<size;j++){C(!out[2*j+1]);if(n+j>=24000){double v=sv_sample24(out[2*j])/8388608.0;energy+=v*v;}}
    }
    return sqrt(energy/24000)/(0.01/sqrt(2.0));
}
int main(void){
    groups++;
    for(unsigned i=0;i<4;i++){
        uint32_t c=sv_sai_cr1(i);
        C(sv_sai_registers_valid(i,c,SV_SAI_FRCR,SV_SAI_SLOTR,49152000));
        C(sv_sai_registers_valid(i,c|(1u<<16)|(1u<<17),SV_SAI_FRCR,SV_SAI_SLOTR,49152000));
        for(unsigned bit=0;bit<32;bit++){
            if(SV_SAI_CR1_MASK&(1u<<bit))C(!sv_sai_registers_valid(i,c^(1u<<bit),SV_SAI_FRCR,SV_SAI_SLOTR,49152000));
            if(SV_SAI_FRCR_MASK&(1u<<bit))C(!sv_sai_registers_valid(i,c,SV_SAI_FRCR^(1u<<bit),SV_SAI_SLOTR,49152000));
            if(SV_SAI_SLOTR_MASK&(1u<<bit))C(!sv_sai_registers_valid(i,c,SV_SAI_FRCR,SV_SAI_SLOTR^(1u<<bit),49152000));
        }
        C(!sv_sai_registers_valid(i,c,SV_SAI_FRCR,0xffff0180u,49152000));
        C(!sv_sai_registers_valid(i,c,SV_SAI_FRCR,SV_SAI_SLOTR,98304000));
    }
    C(!sv_sai_registers_valid(4,sv_sai_cr1(0),SV_SAI_FRCR,SV_SAI_SLOTR,49152000));
    groups++;
    C(!sv_audio_stream_ready(0,0,0,0,1,0,true));C(!sv_audio_stream_ready(4,0,5,5,6,0,true));
    C(!sv_audio_stream_ready(4,1,5,5,6,0,true));C(sv_audio_stream_ready(4,2,5,5,6,0,true));
    C(!sv_audio_stream_ready(4,2,5,5,56,0,true));C(!sv_audio_stream_ready(4,2,5,5,6,1,true));
    C(!sv_audio_stream_ready(4,2,5,5,6,0,false));C(sv_audio_stream_ready(4,2,UINT32_MAX-10,UINT32_MAX-10,5,0,true));
    groups++;
    for(int a=INT16_MIN;a<=INT16_MAX;a++){
        C(sv_resample_lerp((int16_t)a,(int16_t)a,0)==a);
        C(sv_resample_lerp((int16_t)a,(int16_t)a,73)==a);
        C(sv_resample_lerp((int16_t)a,(int16_t)a,146)==a);
    }
    for(unsigned f=0;f<147;f++){
        int32_t ref=((int32_t)INT16_MIN*(int32_t)(147-f)+(int32_t)INT16_MAX*(int32_t)f)/147;
        C(sv_resample_lerp(INT16_MIN,INT16_MAX,f)==ref);
    }
    C(sv_resample_lerp(-1,1,147)==0);
    groups++;
    double at850=response(850),at200=response(200),at100=response(100),at4000=response(4000);
    C(at850>0.70 && at850<0.715);C(at200/at100>3.9);C(at4000>0.99);
    groups++;
    sv_speaker s;float f[128];uint32_t out[256];int32_t cap=sv_speaker_peak_cap(5500);
    C(cap<=3355392 && cap>0);C(sv_speaker_peak_cap(3300)==cap);C(!sv_speaker_peak_cap(6001));
    for(unsigned mode=0;mode<3;mode++){
        sv_speaker_reset(&s);
        for(unsigned n=0;n<1000;n++){
            for(unsigned j=0;j<128;j++)f[j]=mode==0?1.0f:mode==1?-1.0f:(j&1?-1.0f:1.0f);
            C(sv_speaker_process(&s,f,out,128,5500));
            for(unsigned j=0;j<128;j++){int32_t v=sv_sample24(out[2*j]);C(v<=cap && v>=-cap);C(out[2*j+1]==0);}
        }
        if(mode<2)C(abs(sv_sample24(out[254]))<16);
    }
    f[0]=NAN;C(!sv_speaker_process(&s,f,out,128,5500));for(unsigned i=0;i<256;i++)C(!out[i]);
    /* R4 PCM-01: ADC words scaled 1/2 (was 1/16); full scale must not wrap. */
    groups++;sv_factory d;sv_factory_init(&d,0);d.armed=true;d.port=SV_LINE;d.mode=2;d.input=1;
    uint32_t a[256],b[256],spk[256],phase=0;
    for(unsigned j=0;j<128;j++){a[2*j]=0x80000000u;a[2*j+1]=0x7fffff00u;b[2*j]=0x80000000u;b[2*j+1]=0;}
    sv_factory_render(&d,a,b,out,spk,128,&phase);
    for(unsigned j=0;j<128;j++){C(sv_sample24(out[2*j])==8388607/2);C(sv_sample24(out[2*j+1])==-8388608/2);C(!spk[2*j]&&!spk[2*j+1]);}
    d.port=SV_HP;sv_factory_render(&d,a,b,out,spk,128,&phase);
    for(unsigned j=0;j<128;j++){C(sv_sample24(out[2*j])==8388607/2);C(sv_sample24(out[2*j+1])==-8388608/2);}
    d.port=SV_SPK;sv_factory_render(&d,a,b,out,spk,128,&phase);
    for(unsigned j=0;j<128;j++){C(!out[2*j]&&!out[2*j+1]);C(!spk[2*j+1]);C(abs(sv_sample24(spk[2*j]))<=cap);}
    printf("{\"groups\":%u,\"assertions\":%u,\"hardware_tests\":0,\"suite\":\"audio_contract\",\"HPF850Gain\":%.6f,\"lowOctaveRatio\":%.6f,\"speakerCap24\":%d}\n",groups,checks,at850,at200/at100,cap);
    return 0;
}
