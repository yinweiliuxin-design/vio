#ifdef SV_SAFETY_REGISTER_MODEL
#include "safety_hal_model.h"
#else
#include "stm32h7xx_hal.h"
#endif
#include "safety_inputs.h"
#include "audio_hw.h"
extern uint32_t sv_target_millis(void);
sv_input_guard sv_input_safety;
static volatile bool initialized;
/* R4 Q7: polarity from HP_DETECT_ACTIVE_HIGH (sv_input_guard.h). */
static bool hp_raw(void){return sv_hp_inserted_from_pin((GPIOA->IDR&GPIO_PIN_4)!=0);}
void sv_safety_inputs_init(uint32_t boot_at){
    initialized=false;sv_input_guard_init(&sv_input_safety,boot_at);
    /* PC4 and PA4 cannot both own EXTI4. Route it to the short LTC INT pulse;
     * PA4 speaker cutoff instead runs in the highest-priority1ms SysTick. */
    GPIO_InitTypeDef g={0};g.Pin=GPIO_PIN_4;g.Mode=GPIO_MODE_IT_FALLING;g.Pull=GPIO_NOPULL;
    HAL_GPIO_Init(GPIOC,&g);
    __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_4);
    HAL_NVIC_SetPriority(EXTI4_IRQn,0,0);initialized=true;HAL_NVIC_EnableIRQ(EXTI4_IRQn);
}
void sv_safety_inputs_tick(uint32_t now){
    if(!initialized)return;
    bool inserted=hp_raw();
    if(inserted)GPIOA->BSRR=(uint32_t)GPIO_PIN_2<<16;
    sv_input_guard_tick(&sv_input_safety,inserted,!(GPIOC->IDR&GPIO_PIN_4),now);
    if(sv_input_safety.shutdown)sv_audio_emergency_mute();
}
void EXTI4_IRQHandler(void){
    if(__HAL_GPIO_EXTI_GET_IT(GPIO_PIN_4)){
        __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_4);
        if(initialized){
            sv_input_power_edge(&sv_input_safety,sv_target_millis());
            if(sv_input_safety.shutdown)sv_audio_emergency_mute();
        }
    }
}
bool sv_safety_shutdown_requested(void){return sv_input_safety.shutdown;}
bool sv_safety_hp_inserted(void){return sv_input_safety.hp_inserted;}
void sv_safety_rearm(uint32_t now){
    uint32_t primask=__get_PRIMASK();__disable_irq();
    sv_input_guard_rearm(&sv_input_safety,now);
    __DMB();__set_PRIMASK(primask);
}
static bool permitted(bool headphone){
    uint32_t primask=__get_PRIMASK();__disable_irq();
    bool raw=hp_raw(),ok=false;
    if(initialized){
        if(raw)GPIOA->BSRR=(uint32_t)GPIO_PIN_2<<16;
        sv_input_observe_hp(&sv_input_safety,raw,sv_target_millis());
        ok=headphone?sv_input_headphone_allowed(&sv_input_safety,raw):sv_input_speaker_allowed(&sv_input_safety,raw);
    }
    __DMB();__set_PRIMASK(primask);return ok;
}
bool sv_safety_speaker_permitted(void){return permitted(false);}
bool sv_safety_headphone_permitted(void){return permitted(true);}
uint8_t sv_safety_apply_outputs(uint8_t desired){
    uint32_t primask=__get_PRIMASK();__disable_irq();
    /* An IRQ can already have muted after main computed desired. Recheck at
     * the actual BSRR write, not only in the higher-level route decision. */
    bool raw=hp_raw();
    if(initialized)sv_input_observe_hp(&sv_input_safety,raw,sv_target_millis());
    desired=initialized?sv_input_output_mask(&sv_input_safety,desired,raw):0;
    GPIOA->BSRR=((uint32_t)(15u&~desired)<<16)|(desired&15u);
#if SV_HAS_GROUPED_PORTS
    GPIOD->BSRR=((uint32_t)(3u&~(desired>>4))<<(14+16))|((uint32_t)((desired>>4)&3u)<<14);
#endif
    __DMB();__set_PRIMASK(primask);return desired;
}
