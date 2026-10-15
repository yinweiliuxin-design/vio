#include "safety_hal_model.h"
#include "safety_inputs.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
GPIO_TypeDef sv_fake_gpioa,sv_fake_gpioc,sv_fake_gpiod,sv_fake_gpioe;
uint32_t sv_model_pending,sv_model_primask;
static unsigned groups,checks,muted,enabled_irq;
static uint32_t now;static bool inject_hp;
extern sv_input_guard sv_input_safety;
extern void EXTI4_IRQHandler(void);
/* R4 Q7: PA4 level for a given plug state under HP_DETECT_ACTIVE_HIGH. */
#define HP_PIN(ins) (((ins)!=0)==(HP_DETECT_ACTIVE_HIGH!=0)?GPIO_PIN_4:0u)
enum {D=SV_HP_INSERT_DEBOUNCE_MS,R=SV_HP_RELEASE_GUARD_MS};
#define C(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL target safety line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
void HAL_GPIO_Init(GPIO_TypeDef *port,GPIO_InitTypeDef *g){C(port==GPIOC);C(g->Pin==GPIO_PIN_4);C(g->Mode==GPIO_MODE_IT_FALLING);C(g->Pull==GPIO_NOPULL);}
void HAL_NVIC_SetPriority(int irq,unsigned preempt,unsigned sub){C(irq==EXTI4_IRQn && preempt==0 && sub==0);}
void HAL_NVIC_EnableIRQ(int irq){C(irq==EXTI4_IRQn);enabled_irq++;}
void sv_model_disable_irq(void){sv_model_primask=1;if(inject_hp){GPIOA->IDR=HP_PIN(true);inject_hp=false;}}
uint32_t sv_target_millis(void){return now;}
void sv_audio_emergency_mute(void){muted++;GPIOA->BSRR=15u<<16;GPIOC->BSRR=1u<<21;GPIOE->BSRR=1u<<30;if(SV_HAS_GROUPED_PORTS)GPIOD->BSRR=3u<<30;}
static void reset(uint32_t boot){
    memset(GPIOA,0,sizeof(*GPIOA));memset(GPIOC,0,sizeof(*GPIOC));memset(GPIOE,0,sizeof(*GPIOE));
    GPIOA->IDR=HP_PIN(false);GPIOC->IDR=GPIO_PIN_4;now=boot;muted=enabled_irq=0;sv_model_primask=0;inject_hp=false;
    sv_model_pending=GPIO_PIN_4;sv_safety_inputs_init(boot);C(!sv_model_pending&&enabled_irq==1);
}
static void tick(uint32_t at,bool hp,bool power){now=at;GPIOA->IDR=HP_PIN(hp);GPIOC->IDR=power?0:GPIO_PIN_4;sv_safety_inputs_tick(now);}
static void power_edge(uint32_t at){now=at;sv_model_pending|=GPIO_PIN_4;EXTI4_IRQHandler();C(!sv_model_pending);}
static bool legacy_30ms(unsigned width,unsigned gap){
    bool tracking=false,shutdown=false;unsigned started=0;
    for(unsigned t=0;t<100;t+=gap){if(t<width){if(!tracking){tracking=true;started=t;}else if(t-started>=30)shutdown=true;}else tracking=false;}
    return shutdown;
}
int main(void){
    groups++;GPIOA->IDR=HP_PIN(false);C(!sv_safety_apply_outputs(15));C(GPIOA->BSRR==(15u<<16));
    C(!sv_safety_speaker_permitted());C(!sv_safety_headphone_permitted());
    groups++;C(!legacy_30ms(26,1));C(!legacy_30ms(26,100));C(legacy_30ms(32,1));
    /* Pulse arrives/recedes while main never polls. Hardware pending remains;
     * ISR latches even after raw INT is HIGH again. No raw-level recheck. */
    for(unsigned phase=0;phase<26;phase++){
        reset(0);tick(1000,false,false);power_edge(1001+phase);C(sv_safety_shutdown_requested());
        tick(1027+phase,false,false);C(sv_safety_shutdown_requested());C(!sv_safety_apply_outputs(4));C(muted>0);
        reset(0);tick(1000,false,false);GPIOC->IDR=GPIO_PIN_4;power_edge(1100+phase);C(sv_safety_shutdown_requested());
    }
    groups++;reset(0);power_edge(500);tick(526,false,false);C(!sv_safety_shutdown_requested());C(!muted);
    power_edge(999);C(!sv_safety_shutdown_requested());C(sv_input_safety.ignored_edges==2);
    tick(1000,false,false);C(!sv_safety_shutdown_requested());power_edge(1000);C(sv_safety_shutdown_requested());
    groups++;reset(0);for(unsigned t=900;t<=1001;t++)tick(t,false,true);C(!sv_safety_shutdown_requested());
    tick(1002,false,true);C(sv_safety_shutdown_requested());tick(1200,false,false);C(sv_safety_shutdown_requested());
    reset(0);tick(1000,false,true);tick(1001,false,false);C(!sv_safety_shutdown_requested());
    /* No EXTI delivery: a real 26ms LOW still latches with a 1ms sampler,
     * independent of main-loop work. Startup-only pulses never carry over. */
    groups++;
    for(unsigned phase=0;phase<26;phase++){
        reset(0);tick(1000,false,false);
        for(unsigned t=1001;t<1060;t++)tick(t,false,t>=1001+phase && t<1027+phase);
        C(sv_safety_shutdown_requested());C(!sv_safety_apply_outputs(15));
        reset(0);for(unsigned t=974;t<=1000;t++)tick(t,false,t<1000);
        C(!sv_safety_shutdown_requested());
    }
    groups++;uint32_t boot=UINT32_MAX-500;reset(boot);tick(boot+999,false,false);power_edge(boot+999);C(!sv_safety_shutdown_requested());
    tick(boot+1000,false,false);power_edge(boot+1001);C(sv_safety_shutdown_requested());
    reset(0);tick(1000,false,false);tick(UINT32_MAX,false,false);power_edge(2);C(sv_safety_shutdown_requested());
    groups++;reset(0);tick(0,false,false);C(!sv_safety_apply_outputs(4));tick(R-1,false,false);C(!sv_safety_speaker_permitted());
    tick(R,false,false);C(sv_safety_speaker_permitted());C(sv_safety_apply_outputs(4)==4);
    /* Raw insertion edge immediately clears the actual target BSRR (before debounce). */
    uint32_t t0=R+1;tick(t0,true,false);C(GPIOA->BSRR==(4u<<16));C(!sv_safety_speaker_permitted());C(!sv_safety_apply_outputs(4));C(!(GPIOA->BSRR&4));C(GPIOA->BSRR&(4u<<16));
    C(!sv_safety_headphone_permitted());tick(t0+D-1,true,false);C(!sv_safety_headphone_permitted());tick(t0+D,true,false);C(sv_safety_headphone_permitted());
    /* FW-PORT-ENABLE-HP: the HP route PA0|PA1|PA3 (=11) passes the final mask unchanged. */
    C(sv_safety_apply_outputs(11)==11);C(GPIOA->BSRR==(11u|(4u<<16)));C(sv_safety_apply_outputs(3)==3);
#if SV_HAS_GROUPED_PORTS
    /* R4 E-03: HP group PD14 (bit4) + RET group PD15 (bit5) reach GPIOD only while HP is debounced in. */
    C(sv_safety_apply_outputs(1|2|16|32)==(1|2|16|32));C(GPIOD->BSRR==((3u<<14)));C(GPIOA->BSRR==(3u|(12u<<16)));
    C(sv_safety_apply_outputs(32)==32);C(GPIOD->BSRR==((1u<<15)|(1u<<30)));
#endif
    C(sv_safety_apply_outputs(9)==9);C(!sv_safety_apply_outputs(4));C(sv_safety_apply_outputs(12)==8);
    /* Q7: raw glitches while inserted (tip-contact variant, loud audio) keep HP and never enable SPK. */
    groups++;uint32_t t1=t0+D+1;
    for(uint32_t t=t1;t<t1+100;t++){tick(t,(t&1)!=0,false);C(sv_safety_headphone_permitted());C(!sv_safety_apply_outputs(4));}
    /* Real unplug: debounced state changes only after R ms stable; then SPK. */
    uint32_t t2=t1+100;tick(t2,false,false);C(!sv_safety_apply_outputs(4));
    tick(t2+R-2,false,false);C(sv_safety_headphone_permitted());C(!sv_safety_apply_outputs(4));
    tick(t2+R,false,false);C(!sv_safety_headphone_permitted());C(!sv_safety_apply_outputs(3));C(sv_safety_apply_outputs(4)==4);
    C(!sv_safety_apply_outputs(16));C(sv_safety_apply_outputs(8|32)==(SV_HAS_GROUPED_PORTS?40:8));
    C(!sv_safety_apply_outputs(0)); /* stable unplug alone never grants a port */
    groups++;reset(0);tick(0,false,false);tick(R,false,false);C(sv_safety_apply_outputs(4)==4);
    /* Insertion races with main's old desired=SPK. Commit rechecks raw input
     * after masking IRQs and also starts release guard for a sub-tick event. */
    now=R+1;inject_hp=true;C(!sv_safety_apply_outputs(4));C(!sv_model_primask);
    GPIOA->IDR=HP_PIN(false);now=R+2;C(!sv_safety_apply_outputs(4));now=2*R+1;C(!sv_safety_apply_outputs(4));now=2*R+2;C(sv_safety_apply_outputs(4)==4);
    sv_model_primask=1;C(sv_safety_apply_outputs(4)==4);C(sv_model_primask==1);sv_model_primask=0;
    groups++;reset(0);tick(0,false,false);tick(1000,false,false);C(sv_safety_apply_outputs(4)==4);power_edge(1001);
    for(unsigned mask=0;mask<256;mask++){C(!sv_safety_apply_outputs((uint8_t)mask));C(GPIOA->BSRR==(15u<<16));}
    C(GPIOC->BSRR==(1u<<21));C(GPIOE->BSRR==(1u<<30)); /* no PC13/PE8 rewrite */
    groups++;reset(UINT32_MAX-20);tick(UINT32_MAX-20,true,false);tick(0,false,false);
    tick(R-1,false,false);C(!sv_safety_apply_outputs(4));tick(R,false,false);C(sv_safety_apply_outputs(4)==4);
    groups++;reset(0);EXTI4_IRQHandler();C(!sv_safety_shutdown_requested());C(!muted);
    sv_input_safety.ignored_edges=UINT32_MAX;power_edge(999);C(sv_input_safety.ignored_edges==UINT32_MAX);
    sv_input_safety.power_edges=UINT32_MAX;power_edge(1000);power_edge(1001);C(sv_input_safety.power_edges==UINT32_MAX);
    C(sv_safety_shutdown_requested());sv_model_primask=1;C(!sv_safety_apply_outputs(15));C(sv_model_primask==1);sv_model_primask=0;
    /* R4 FW-USB-SHUTDOWN-LATCH: rearm clears the latch, ignores INT for 1 s, then sees the next edge. */
    groups++;sv_safety_rearm(5000);C(!sv_safety_shutdown_requested());power_edge(5999);C(!sv_safety_shutdown_requested());
    tick(6000,false,false);power_edge(6001);C(sv_safety_shutdown_requested());
    printf("{\"groups\":%u,\"assertions\":%u,\"suite\":\"target_safety_inputs\",\"legacy26msNegativeReproduced\":true,\"hp_active_high\":%d,\"hp_debounce_ms\":%d,\"hardware_tests\":0}\n",groups,checks,HP_DETECT_ACTIVE_HIGH,(int)D);return 0;
}
