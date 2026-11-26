#include "stm32h7xx_hal.h"
#include "audio_hw.h"
#include "sv_sai_contract.h"
#include "sv_audio_meter.h"
#include <string.h>
_Static_assert(SV_SAI_CR1_MASK==(SAI_xCR1_MODE|SAI_xCR1_PRTCFG|SAI_xCR1_DS|SAI_xCR1_LSBFIRST|SAI_xCR1_CKSTR|SAI_xCR1_SYNCEN|SAI_xCR1_MONO|SAI_xCR1_OUTDRIV|SAI_xCR1_NODIV|SAI_xCR1_MCKDIV|SAI_xCR1_OSR|SAI_xCR1_MCKEN),"CR1 official mask");
_Static_assert(SV_SAI_FRCR_MASK==(SAI_xFRCR_FRL|SAI_xFRCR_FSALL|SAI_xFRCR_FSDEF|SAI_xFRCR_FSPOL|SAI_xFRCR_FSOFF),"FRCR official mask");
_Static_assert(SV_SAI_SLOTR_MASK==(SAI_xSLOTR_FBOFF|SAI_xSLOTR_SLOTSZ|SAI_xSLOTR_NBSLOT|SAI_xSLOTR_SLOTEN),"SLOTR official mask");
/* D2 SRAM1 is DMA-accessible (CMSIS D2_AHBSRAM_BASE). D-cache stays disabled. */
static uint32_t samples[4][256] __attribute__((section(".dma"),aligned(32)));
static uint32_t paired[2][128];
static SAI_HandleTypeDef sai[4];
static DMA_HandleTypeDef dma[4];
static volatile uint32_t completed[4][2],errors;
static uint32_t consumed[4][2],pairs,phase,last_rx,last_tx,tx_sent,rendered_pair[2];
static uint32_t codec_pair_base;
static bool running,codec_qualified;
sv_audio_meter sv_audio_telemetry;
volatile struct {uint32_t service_calls,rx_pairs,tx_halves,ownership_waits,errors,max_cycles,last_cycles;} sv_dma_telemetry;
/* SWD-readable actual register snapshots, only populated on target execution. */
volatile struct {uint32_t cr1[4],frcr[4],slotr[4],kernel[2],pllckselr,pllcfgr,pll2divr,pll2fracr,d2ccip1r,cfgr,revid;} sv_audio_clock_snapshot;
static bool registers_valid(void){
    bool ok=true;
    for(unsigned i=0;i<4;i++){
        if(!sai[i].Instance)return false;
        uint32_t c=sai[i].Instance->CR1,f=sai[i].Instance->FRCR,s=sai[i].Instance->SLOTR;
        sv_audio_clock_snapshot.cr1[i]=c;sv_audio_clock_snapshot.frcr[i]=f;sv_audio_clock_snapshot.slotr[i]=s;
        ok=sv_sai_registers_valid(i,c,f,s,sv_audio_clock_snapshot.kernel[i/2]) && ok;
    }
    return ok;
}
static bool free_half(unsigned i,unsigned half){
    uint32_t n=__HAL_DMA_GET_COUNTER(&dma[i]);
    /* Keep at least32 words before ownership switches. Check again after work;
     * target WCET and NDTR/IRQ races still require on-board qualification. */
    return sv_dma_half_free(half,n);
}
void sv_audio_emergency_mute(void){GPIOA->BSRR=0x0fu<<16;GPIOC->BSRR=1u<<(5+16);GPIOE->BSRR=1u<<(14+16);
#if SV_HAS_GROUPED_PORTS
    GPIOD->BSRR=3u<<(14+16); /* R4 E-03 HP/RET PhotoMOS groups off */
#endif
}
static void pin(GPIO_TypeDef *p,uint16_t bits,uint32_t af){
    GPIO_InitTypeDef g={0};g.Pin=bits;g.Mode=GPIO_MODE_AF_PP;g.Pull=GPIO_NOPULL;
    g.Speed=GPIO_SPEED_FREQ_HIGH;g.Alternate=af;HAL_GPIO_Init(p,&g);
}
static void analog(GPIO_TypeDef *p,uint16_t bits){
    GPIO_InitTypeDef g={0};g.Pin=bits;g.Mode=GPIO_MODE_ANALOG;g.Pull=GPIO_NOPULL;HAL_GPIO_Init(p,&g);
}
static bool clocks(void){
    /* Only Y/V timing tables were reviewed. Unknown die revisions fail muted
     * pending their datasheet/errata review; do not infer revision from MPN. */
    if(HAL_GetREVID()!=REV_ID_Y && HAL_GetREVID()!=REV_ID_V)return false;
    RCC_OscInitTypeDef o={0};o.OscillatorType=RCC_OSCILLATORTYPE_HSE|RCC_OSCILLATORTYPE_CSI;
    o.HSEState=RCC_HSE_ON;o.CSIState=RCC_CSI_ON;o.PLL.PLLState=RCC_PLL_NONE;
    if(HAL_RCC_OscConfig(&o)!=HAL_OK)return false;
    __HAL_RCC_PLL_PLLSOURCE_CONFIG(RCC_PLLSOURCE_HSE);
    RCC_PeriphCLKInitTypeDef c={0};c.PeriphClockSelection=RCC_PERIPHCLK_SAI1|RCC_PERIPHCLK_SAI23;
    c.Sai1ClockSelection=RCC_SAI1CLKSOURCE_PLL2;c.Sai23ClockSelection=RCC_SAI23CLKSOURCE_PLL2;
    c.PLL2.PLL2M=6;c.PLL2.PLL2N=96;c.PLL2.PLL2P=8;c.PLL2.PLL2Q=8;c.PLL2.PLL2R=8;
    c.PLL2.PLL2RGE=RCC_PLL2VCIRANGE_2;c.PLL2.PLL2VCOSEL=RCC_PLL2VCOWIDE;c.PLL2.PLL2FRACN=0;
    if(HAL_RCCEx_PeriphCLKConfig(&c)!=HAL_OK)return false;
    HAL_RCC_MCOConfig(RCC_MCO2,RCC_MCO2SOURCE_PLL2PCLK,RCC_MCODIV_2);
    sv_audio_clock_snapshot.kernel[0]=HAL_RCCEx_GetPeriphCLKFreq(RCC_PERIPHCLK_SAI1);
    sv_audio_clock_snapshot.kernel[1]=HAL_RCCEx_GetPeriphCLKFreq(RCC_PERIPHCLK_SAI23);
    sv_audio_clock_snapshot.pllckselr=RCC->PLLCKSELR;sv_audio_clock_snapshot.pllcfgr=RCC->PLLCFGR;
    sv_audio_clock_snapshot.pll2divr=RCC->PLL2DIVR;sv_audio_clock_snapshot.pll2fracr=RCC->PLL2FRACR;
    sv_audio_clock_snapshot.d2ccip1r=RCC->D2CCIP1R;sv_audio_clock_snapshot.cfgr=RCC->CFGR;sv_audio_clock_snapshot.revid=HAL_GetREVID();
    return sv_audio_clock_snapshot.kernel[0]==49152000u && sv_audio_clock_snapshot.kernel[1]==49152000u &&
        (RCC->PLLCKSELR&(RCC_PLLCKSELR_PLLSRC|RCC_PLLCKSELR_DIVM2))==(RCC_PLLSOURCE_HSE|(6u<<RCC_PLLCKSELR_DIVM2_Pos)) &&
        (RCC->PLLCFGR&(RCC_PLLCFGR_PLL2VCOSEL|RCC_PLLCFGR_PLL2RGE|RCC_PLLCFGR_DIVP2EN))==(RCC_PLL2VCIRANGE_2|RCC_PLLCFGR_DIVP2EN) &&
        (RCC->PLL2DIVR&(RCC_PLL2DIVR_N2|RCC_PLL2DIVR_P2|RCC_PLL2DIVR_Q2|RCC_PLL2DIVR_R2))==(95u|(7u<<9)|(7u<<16)|(7u<<24)) &&
        !(RCC->PLL2FRACR&RCC_PLL2FRACR_FRACN2) &&
        (RCC->D2CCIP1R&(RCC_D2CCIP1R_SAI1SEL|RCC_D2CCIP1R_SAI23SEL))==(RCC_SAI1CLKSOURCE_PLL2|RCC_SAI23CLKSOURCE_PLL2) &&
        (RCC->CFGR&(RCC_CFGR_MCO2|RCC_CFGR_MCO2PRE))==(RCC_MCO2SOURCE_PLL2PCLK|(2u<<RCC_CFGR_MCO2PRE_Pos));
}
static bool block(unsigned i,SAI_Block_TypeDef *instance,DMA_Stream_TypeDef *stream,uint32_t request){
    DMA_HandleTypeDef *d=&dma[i];d->Instance=stream;d->Init.Request=request;
    d->Init.Direction=i<2?DMA_PERIPH_TO_MEMORY:DMA_MEMORY_TO_PERIPH;
    d->Init.PeriphInc=DMA_PINC_DISABLE;d->Init.MemInc=DMA_MINC_ENABLE;
    d->Init.PeriphDataAlignment=DMA_PDATAALIGN_WORD;d->Init.MemDataAlignment=DMA_MDATAALIGN_WORD;
    d->Init.Mode=DMA_CIRCULAR;d->Init.Priority=DMA_PRIORITY_HIGH;d->Init.FIFOMode=DMA_FIFOMODE_DISABLE;
    if(HAL_DMA_Init(d)!=HAL_OK)return false;
    SAI_HandleTypeDef *h=&sai[i];h->Instance=instance;
    h->Init.AudioMode=i<2?(i==0?SAI_MODEMASTER_RX:SAI_MODESLAVE_RX):(i==2?SAI_MODEMASTER_TX:SAI_MODESLAVE_TX);
    h->Init.Synchro=(i&1)?SAI_SYNCHRONOUS:SAI_ASYNCHRONOUS;h->Init.SynchroExt=SAI_SYNCEXT_DISABLE;
    h->Init.OutputDrive=SAI_OUTPUTDRIVE_ENABLE;h->Init.NoDivider=SAI_MASTERDIVIDER_DISABLE;
    h->Init.FIFOThreshold=SAI_FIFOTHRESHOLD_1QF;h->Init.AudioFrequency=SAI_AUDIO_FREQUENCY_MCKDIV;h->Init.Mckdiv=16;
    h->Init.MckOutput=SAI_MCK_OUTPUT_DISABLE;h->Init.MckOverSampling=SAI_MCK_OVERSAMPLING_DISABLE;
    h->Init.MonoStereoMode=SAI_STEREOMODE;h->Init.CompandingMode=SAI_NOCOMPANDING;h->Init.TriState=SAI_OUTPUT_NOTRELEASED;
    if(i<2){__HAL_LINKDMA(h,hdmarx,*d);}else {__HAL_LINKDMA(h,hdmatx,*d);}
    if(HAL_SAI_InitProtocol(h,SAI_I2S_STANDARD,SAI_PROTOCOL_DATASIZE_32BIT,2)!=HAL_OK)return false;
    /* InitProtocol sets SlotActive=ALL. Reinitialize while disabled to freeze
     * just slots0/1; HAL structure checks alone cannot prove clock registers. */
    h->SlotInit.SlotActive=SAI_SLOTACTIVE_0|SAI_SLOTACTIVE_1;
    if(HAL_SAI_Init(h)!=HAL_OK)return false;
    return sv_sai_registers_valid(i,h->Instance->CR1,h->Instance->FRCR,h->Instance->SLOTR,sv_audio_clock_snapshot.kernel[i/2]);
}
bool sv_audio_hw_start(void){
    memset(&sv_audio_telemetry,0,sizeof(sv_audio_telemetry));memset((void*)&sv_dma_telemetry,0,sizeof(sv_dma_telemetry));
    CoreDebug->DEMCR|=CoreDebug_DEMCR_TRCENA_Msk;DWT->CTRL|=DWT_CTRL_CYCCNTENA_Msk;
    sv_audio_emergency_mute();running=false;codec_qualified=false;codec_pair_base=0;errors=0;pairs=phase=tx_sent=0;last_rx=last_tx=HAL_GetTick();
    memset(rendered_pair,0,sizeof(rendered_pair));
    __HAL_RCC_D2SRAM1_CLK_ENABLE();(void)RCC->AHB2ENR;
    memset(samples,0,sizeof(samples));memset(paired,0,sizeof(paired));
    memset((void*)completed,0,sizeof(completed));memset(consumed,0,sizeof(consumed));
    memset(sai,0,sizeof(sai));memset(dma,0,sizeof(dma));
    if(!clocks())return false;
    __HAL_RCC_DMA1_CLK_ENABLE();__HAL_RCC_SAI1_CLK_ENABLE();__HAL_RCC_SAI2_CLK_ENABLE();
    pin(GPIOE,GPIO_PIN_3|GPIO_PIN_4|GPIO_PIN_5|GPIO_PIN_6,GPIO_AF6_SAI1);
    pin(GPIOD,GPIO_PIN_11|GPIO_PIN_12|GPIO_PIN_13,GPIO_AF10_SAI2);pin(GPIOE,GPIO_PIN_11,GPIO_AF10_SAI2);
    if(!block(0,SAI1_Block_A,DMA1_Stream0,DMA_REQUEST_SAI1_A) ||
       !block(1,SAI1_Block_B,DMA1_Stream1,DMA_REQUEST_SAI1_B) ||
       !block(2,SAI2_Block_A,DMA1_Stream2,DMA_REQUEST_SAI2_A) ||
       !block(3,SAI2_Block_B,DMA1_Stream3,DMA_REQUEST_SAI2_B))return false;
    const IRQn_Type irq[]={DMA1_Stream0_IRQn,DMA1_Stream1_IRQn,DMA1_Stream2_IRQn,DMA1_Stream3_IRQn,SAI1_IRQn,SAI2_IRQn};
    for(unsigned i=0;i<6;i++){HAL_NVIC_SetPriority(irq[i],3,0);HAL_NVIC_EnableIRQ(irq[i]);}
    __DSB();running=true;
    /* Arm synchronized B before master A to avoid losing the first frame. */
    if(HAL_SAI_Receive_DMA(&sai[1],(uint8_t*)samples[1],256)!=HAL_OK ||
       HAL_SAI_Receive_DMA(&sai[0],(uint8_t*)samples[0],256)!=HAL_OK ||
       HAL_SAI_Transmit_DMA(&sai[3],(uint8_t*)samples[3],256)!=HAL_OK ||
       HAL_SAI_Transmit_DMA(&sai[2],(uint8_t*)samples[2],256)!=HAL_OK){errors|=SV_D_FAULT_DMA;return false;}
    if(!registers_valid()){errors|=SV_D_FAULT_CLOCK;sv_audio_emergency_mute();return false;}
    return true;
}
void sv_audio_hw_stop(void){
    sv_audio_emergency_mute();running=false;
    for(unsigned i=0;i<4;i++)if(sai[i].Instance){HAL_SAI_DMAStop(&sai[i]);HAL_SAI_DeInit(&sai[i]);}
    const IRQn_Type irq[]={DMA1_Stream0_IRQn,DMA1_Stream1_IRQn,DMA1_Stream2_IRQn,DMA1_Stream3_IRQn,SAI1_IRQn,SAI2_IRQn};
    for(unsigned i=0;i<6;i++)HAL_NVIC_DisableIRQ(irq[i]);
    analog(GPIOE,GPIO_PIN_3|GPIO_PIN_4|GPIO_PIN_5|GPIO_PIN_6|GPIO_PIN_11);
    analog(GPIOD,GPIO_PIN_11|GPIO_PIN_12|GPIO_PIN_13);analog(GPIOC,GPIO_PIN_9);
    __HAL_RCC_PLL2_DISABLE();
}
uint32_t sv_audio_hw_pairs(void){return pairs;}
void sv_audio_hw_codec_ready(uint32_t now){
    codec_pair_base=pairs;tx_sent=0;last_tx=now;memset(rendered_pair,0,sizeof(rendered_pair));codec_qualified=true;
}
bool sv_audio_hw_ready(uint32_t now){return running && codec_qualified && sv_audio_stream_ready(pairs-codec_pair_base,tx_sent,last_rx,last_tx,now,errors,registers_valid());}
uint32_t sv_audio_hw_service(sv_factory *d,uint32_t now){
    if(!running)return errors;
    uint32_t started=DWT->CYCCNT;sv_dma_telemetry.service_calls++;
    if(!registers_valid())errors|=SV_D_FAULT_CLOCK;
    for(unsigned half=0;half<2;half++){
        uint32_t a=completed[0][half],b=completed[1][half];
        if(sv_dma_lost(a,consumed[0][half]) || sv_dma_lost(b,consumed[1][half])){errors|=SV_D_FAULT_DMA;break;}
        if(a!=consumed[0][half] && a==b){
            /* Copy only a half no longer owned by either RX DMA. */
            if(!free_half(0,half) || !free_half(1,half)){sv_dma_telemetry.ownership_waits++;continue;}
            memcpy(paired[0],samples[0]+half*128,512);memcpy(paired[1],samples[1]+half*128,512);
            __DMB();
            if(a!=completed[0][half] || b!=completed[1][half] || !free_half(0,half) || !free_half(1,half)){errors|=SV_D_FAULT_DMA;break;}
            consumed[0][half]=a;consumed[1][half]=b;pairs++;last_rx=now;
            sv_dma_telemetry.rx_pairs++;
        }
        uint32_t x=completed[2][half],y=completed[3][half];
        if(sv_dma_lost(x,consumed[2][half]) || sv_dma_lost(y,consumed[3][half])){errors|=SV_D_FAULT_DMA;break;}
        if(x!=consumed[2][half] && x==y){
            if(!free_half(2,half) || !free_half(3,half)){sv_dma_telemetry.ownership_waits++;continue;}
            /* Completion proves this half was transmitted, not just queued.
             * Force startup silence until RX has four fresh paired blocks. */
            if(rendered_pair[half]){tx_sent++;last_tx=now;}
            bool qualified=codec_qualified && pairs-codec_pair_base>=4 && !errors;
            if(!qualified){memset(samples[2]+half*128,0,512);memset(samples[3]+half*128,0,512);sv_speaker_reset(&d->speaker);}
            else sv_factory_render(d,paired[0],paired[1],samples[2]+half*128,samples[3]+half*128,64,&phase);
            rendered_pair[half]=qualified?pairs:0;
            __DSB();if(!free_half(2,half) || !free_half(3,half)){errors|=SV_D_FAULT_DMA;break;}
            consumed[2][half]=x;consumed[3][half]=y;
            sv_dma_telemetry.tx_halves++;
            sv_audio_measure(&sv_audio_telemetry,samples[2]+half*128,samples[3]+half*128,64);
        }
    }
    if(now-last_rx>50)errors|=SV_D_FAULT_DMA;
    if(codec_qualified && pairs-codec_pair_base>=4 && now-last_tx>50)errors|=SV_D_FAULT_DMA;
    if(errors)sv_audio_emergency_mute();
    sv_dma_telemetry.errors=errors;sv_dma_telemetry.last_cycles=DWT->CYCCNT-started;
    if(sv_dma_telemetry.last_cycles>sv_dma_telemetry.max_cycles)sv_dma_telemetry.max_cycles=sv_dma_telemetry.last_cycles;
    return errors;
}
static void done(SAI_HandleTypeDef *h,unsigned half){for(unsigned i=0;i<4;i++)if(h==&sai[i])completed[i][half]++;}
void HAL_SAI_RxHalfCpltCallback(SAI_HandleTypeDef *h){done(h,0);}
void HAL_SAI_RxCpltCallback(SAI_HandleTypeDef *h){done(h,1);}
void HAL_SAI_TxHalfCpltCallback(SAI_HandleTypeDef *h){done(h,0);}
void HAL_SAI_TxCpltCallback(SAI_HandleTypeDef *h){done(h,1);}
void HAL_SAI_ErrorCallback(SAI_HandleTypeDef *h){(void)h;errors|=SV_D_FAULT_DMA;sv_audio_emergency_mute();}
void DMA1_Stream0_IRQHandler(void){HAL_DMA_IRQHandler(&dma[0]);}
void DMA1_Stream1_IRQHandler(void){HAL_DMA_IRQHandler(&dma[1]);}
void DMA1_Stream2_IRQHandler(void){HAL_DMA_IRQHandler(&dma[2]);}
void DMA1_Stream3_IRQHandler(void){HAL_DMA_IRQHandler(&dma[3]);}
void SAI1_IRQHandler(void){HAL_SAI_IRQHandler(&sai[0]);HAL_SAI_IRQHandler(&sai[1]);}
void SAI2_IRQHandler(void){HAL_SAI_IRQHandler(&sai[2]);HAL_SAI_IRQHandler(&sai[3]);}
