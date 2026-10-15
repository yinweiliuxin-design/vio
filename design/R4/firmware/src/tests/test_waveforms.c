#include "sv_factory.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void){
    sv_factory d;sv_factory_init(&d,0);uint32_t dac[256],spk[256],a[256],b[256],phase=0;
    d.armed=true;d.port=SV_LINE;d.mode=1;
    sv_factory_render(&d,NULL,NULL,dac,spk,96,&phase);
    int32_t peak=0;long sum=0;
    for(unsigned i=0;i<96;i++){
        int32_t s=sv_sample24(dac[2*i]);if(s>peak)peak=s;sum+=s;
        assert(dac[2*i]==dac[2*i+1] && !spk[2*i] && !spk[2*i+1]);
        if(i<48)assert(dac[2*i]==dac[2*(i+48)]);
    }
    assert(peak==131072 && sum==0 && phase==0);
    for(unsigned i=0;i<128;i++){a[2*i]=(uint32_t)16000*256;a[2*i+1]=(uint32_t)-32000*256;b[2*i]=(uint32_t)48000*256;b[2*i+1]=0;}
    d.mode=2;
    /* R4 PCM-01: ADC words now scaled 1/2 (was 1/16). */
    const int expected[5][2]={{8000,8000},{-16000,24000},{-16000,-16000},{24000,24000},{-4000,16000}};
    for(unsigned input=0;input<5;input++){
        d.input=input;sv_factory_render(&d,a,b,dac,spk,64,&phase);
        for(unsigned n=0;n<64;n++){assert(sv_sample24(dac[2*n])==expected[input][0]);assert(sv_sample24(dac[2*n+1])==expected[input][1]);}
    }
    sv_factory_fault(&d,SV_D_FAULT_DMA);sv_factory_render(&d,a,b,dac,spk,64,&phase);
    for(unsigned i=0;i<128;i++)assert(!dac[i] && !spk[i]);
    puts("PASS: 48-sample 1kHz digital tone peak131072, stereo/zero-DC, all five ADC routes at 1/2 (R4 PCM-01), fault silence; no analog measurements");
    return 0;
}
