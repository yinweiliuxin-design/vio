/* SmartVio R4 image (was: isolated V27 diagnostic image). Real peripherals,
 * never hardware-qualified (hardware tests: 0). SV_PRODUCT_MODE=1 (sv_product.h):
 * powers up playable, transient faults auto-recover, auto HP/SPK route, UVLO,
 * simple USB500 charging. SV_PRODUCT_MODE=0 keeps the R3 bench arm flow. */
#include "stm32h7xx_hal.h"
#include "sv_telemetry.h"
#include "sv_factory.h"
#include "board_pins.h"
#include "i2c_probe.h"
#include "audio_hw.h"
#include "fault_store.h"
#include "pot_adc.h"
#include "safety_inputs.h"
#include "sv_rf_reply.h"
#include "sv_service_clear.h"
#include "sv27_power_profile.h"
#include "sv_product.h"
/* R4 FW-NO-CHARGE-PATH: the V27 one-shot session/journal gate (always vetoed)
 * is replaced by the simple gate in sv_product.c; TPS3700 + BQ24074 TS still
 * veto CE in hardware. */
#include <string.h>
static volatile uint32_t milliseconds;
static volatile uint32_t charge_gate_tick;
static sv_charge charge;static sv_charge_out charge_out;
volatile struct {uint32_t version,vbus,usb_mv,pack_mv,board_deci_c,allow,en1,en2,port_fault,efuse_fault,chg_status_n,pgood_n,iset_estimate_ma,iset_estimate_valid;} sv_charge_diag;
static sv_battery battery;static sv_power pwr;
static uint32_t recover_count,logged_faults,show_until,ui_events_seen,vbus_seen_at;static bool recover_pending;
#if SV_PRODUCT_MODE
static uint32_t recover_at,recovered_at;static bool hp_was;static uint8_t user_port;
static sv_bt_ui btui; /* R4 product BT key */
#endif
/* R4 USART3 RX: RXNE/RXFNE interrupt into a ring (FW-UART-OVERRUN). */
static volatile uint8_t rx_ring[512];static volatile uint32_t rx_head,rx_tail;
static uint32_t rf_ka_session,rf_ka_at;static uint16_t rf_ka_seq;
volatile struct {uint32_t version,product,hw_rev_r4,hp_active_high,pll1,cpu_hz,battery_mv,battery_warn,battery_off,
    power,recoveries,retained_faults,rx_errors,rx_drops,tx_timeouts,keepalives,hp_inserted,leds;} sv_r4_diag;
static sv_monitor monitor;
static sv_pcm1864 codec;
static sv_factory factory;
static sv_pot_scan pot_scan;
static uint32_t pot_generation;
static bool pot_initialized,selected_peer;
static sv_rf_guard rf;
static IWDG_HandleTypeDef watchdog;
static sv_parser parser;
static uint8_t tx[270];static size_t tx_count,tx_at;
static uint32_t tx_started,rail_at,discharged_at,recorded;
static unsigned power_state;
static bool uart_on,codec_gate;
static uint8_t previous_port;
static uint32_t port_changed,status_at;static unsigned status_index;
/* SWD mailbox: write fields then increment request last; poll completed/result.
 * Bench interface only, not remotely writable production control. */
volatile struct {
    uint32_t request,completed,nonce,faults,state,pairs,monitor_generation,selftest;
    int32_t temperature_deci_c;uint32_t mv[4];
    uint32_t type,length,session,seq,payload[64],result;
} sv_diag;
volatile struct {
    uint32_t version,raw[3],generation,sampled,adc_fault,ui_enabled,picked_up,muted,fx,rate,input,port,events,session_seq,bt_result,program_remaining_ms;
} sv_ui_diag;
volatile uint32_t sv_rf_pcm_diag[8];
/* Observe ESP acknowledgements independently of queued MCU command results. */
sv_rf_reply sv_rf_reply_diag;
static sv_service_clear service_clear;
/* Separate SWD-only mailbox. No UART opcode maps to this service. */
volatile struct {
    uint32_t version,enabled,request,completed,action,token,state,challenge,faults,result;
} sv_service_diag;
uint32_t HAL_GetTick(void){return milliseconds;}
uint32_t sv_target_millis(void){return milliseconds;}
void SysTick_Handler(void){
    milliseconds++;sv_safety_inputs_tick(milliseconds);
    /* Independent veto: a stalled foreground drops CHARGE_ALLOW within 100 ms. */
    if((uint32_t)(milliseconds-charge_gate_tick)>SV27_INPUT_MAX_AGE_MS)
        GPIOE->BSRR=1u<<(14+16);
}
static void mode(GPIO_TypeDef *p,unsigned n,unsigned m){p->MODER=(p->MODER&~(3u<<(2*n)))|(m<<(2*n));}
static void level(GPIO_TypeDef *p,unsigned n,bool hi){p->BSRR=1u<<(n+(hi?0:16));}
/* Executed before C initialization. Only official CMSIS register definitions. */
void sv_early_safe_gpio(void){
    RCC->AHB4ENR|=RCC_AHB4ENR_GPIOAEN|RCC_AHB4ENR_GPIOBEN|RCC_AHB4ENR_GPIOCEN|RCC_AHB4ENR_GPIOEEN;
    (void)RCC->AHB4ENR;GPIOC->BSRR=SV_C_RF_OFF_BSRR;GPIOE->BSRR=SV_E_BOOT_BSRR;
    GPIOC->OTYPER&=~(SV_PC_RF|SV_PC_AUDIO_BUS);
    GPIOC->MODER=(GPIOC->MODER&~((3u<<10)|(3u<<26)))|(1u<<10)|(1u<<26);
    GPIOE->OTYPER&=~(SV_PE_AUDIO_POWER|SV_PE_BOOT|SV_PE_USB_DISABLE|SV_PE_EN1|SV_PE_EN2|SV_PE_CHARGE);
    GPIOE->MODER=(GPIOE->MODER&~SV_E_SAFE_MODE_MASK)|SV_E_SAFE_MODE_BITS;
    GPIOA->BSRR=0x0fu<<16;GPIOA->MODER=(GPIOA->MODER&~0xffu)|0x55u;
    GPIOB->BSRR=1u<<(10+16);GPIOB->MODER=(GPIOB->MODER&~(3u<<20))|(1u<<20);
    RCC->CR=(RCC->CR&~RCC_CR_HSIDIV)|RCC_CR_HSIDIV_8;__DSB();
}
static void unused(GPIO_TypeDef *p,uint16_t pins){uint32_t mask=0;for(unsigned n=0;n<16;n++)if(pins&(1u<<n))mask|=3u<<(2*n);p->PUPDR&=~mask;p->MODER|=mask;}
static void safe_gpio(void){
    RCC->AHB4ENR|=RCC_AHB4ENR_GPIODEN;(void)RCC->AHB4ENR;
    GPIOC->OSPEEDR&=~((3u<<10)|(3u<<26));
    unused(GPIOA,SV_UNUSED_A);unused(GPIOB,SV_UNUSED_B);unused(GPIOC,SV_UNUSED_C);unused(GPIOD,SV_UNUSED_D);unused(GPIOE,SV_UNUSED_E);
    for(unsigned n=4;n<8;n++)mode(GPIOA,n,0);
    mode(GPIOC,0,0);mode(GPIOC,4,0);mode(GPIOE,8,0);mode(GPIOE,9,0);mode(GPIOE,15,0);
    unused(GPIOE,(15u<<3)|(1u<<11));unused(GPIOD,(3u<<8)|(7u<<11));unused(GPIOC,1u<<9);
    /* R4 FW-UNUSED-STATUS-IO: PA9 VBUS_SENSE, PB11 CHG_PGOOD_N, PD10 CHG_STATUS_N
     * inputs (external pull-ups R816/R817, R505, R506); LED_ZONE_1..3 PC6..PC8 outputs. */
    mode(GPIOA,9,0);mode(GPIOB,11,0);mode(GPIOD,10,0);
    GPIOC->BSRR=7u<<(6+16);GPIOC->OTYPER&=~(7u<<6);for(unsigned n=6;n<9;n++)mode(GPIOC,n,1);
#if SV_HAS_GROUPED_PORTS
    /* R4 E-03: PD14 HP_PORT_ENABLE, PD15 RET_PORT_ENABLE push-pull, low (R1213/R1215 hold gates low in reset). */
    GPIOD->BSRR=3u<<(14+16);GPIOD->OTYPER&=~(3u<<14);mode(GPIOD,14,1);mode(GPIOD,15,1);
#endif
#if SV_HAS_PWR_PB_SENSE
    /* R4 E-11: PB12 PWR_PB_SENSE input with internal pull-up; low (~0.6 V via BAS116) = key pressed. */
    GPIOB->PUPDR=(GPIOB->PUPDR&~(3u<<24))|(1u<<24);mode(GPIOB,12,0);
#endif
}
static bool pwr_key_low(void){
#if SV_HAS_PWR_PB_SENSE
    return !(GPIOB->IDR&(1u<<12));
#else
    return false;
#endif
}
static bool vbus_present(void){return (GPIOA->IDR&(1u<<9))!=0;}
/* FW-SYSTICK-PRIO: SysTick_Config() resets the priority to 15; restore 0 every time. */
static void systick_start(void){SystemCoreClockUpdate();SysTick_Config(SystemCoreClock/1000u);NVIC_SetPriority(SysTick_IRQn,0);}
/* FW-RT-BUDGET + R4 battery budget: fast mode runs the CPU from PLL1 off HSE
 * 24.576 MHz instead of HSI 64 MHz at 7 WS, with I/D-cache on (main()).
 * Default SV_CPU_FAST_MHZ=120: M6 N117 P4 -> 119.808 MHz, VOS2, AXI/AHB /1
 * = 119.8 MHz (<=150), APB /2 = 59.9 MHz (<=75), Flash 2 WS (VOS2 <=165 MHz).
 * Option 200: M6 N96 P2 -> 196.608 MHz, VOS1, AHB /2 = 98.3 MHz, APB /1, 2 WS.
 * USART3/I2C1 kernels stay on HSI (HSIDIV=1): BRR/TIMINGR unchanged. ADC sync
 * clock = HCLK/4 (30.0 / 24.6 MHz). SAI/MCO2 stay on PLL2 (audio_hw.c), unchanged.
 * Falls back to HSI 64 MHz if HSE/PLL1 fail. */
#ifndef SV_CPU_FAST_MHZ
#define SV_CPU_FAST_MHZ 120
#endif
#if SV_CPU_FAST_MHZ==120
enum {SV_PLL1N=117,SV_PLL1P=4};
#define SV_FAST_VOS PWR_REGULATOR_VOLTAGE_SCALE2
#define SV_FAST_HPRE RCC_HCLK_DIV1
#define SV_FAST_APB_DIV(n) RCC_APB##n##_DIV2
#elif SV_CPU_FAST_MHZ==200
enum {SV_PLL1N=96,SV_PLL1P=2};
#define SV_FAST_VOS PWR_REGULATOR_VOLTAGE_SCALE1
#define SV_FAST_HPRE RCC_HCLK_DIV2
#define SV_FAST_APB_DIV(n) RCC_APB##n##_DIV1
#else
#error "SV_CPU_FAST_MHZ must be 120 or 200"
#endif
static bool pll1_start(void){
    if(HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY)!=HAL_OK)return false;
    __HAL_PWR_VOLTAGESCALING_CONFIG(SV_FAST_VOS);
    uint32_t t=milliseconds;
    while(!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY))if(milliseconds-t>10)return false;
    /* Own bounded HSE wait (<=50 ms) keeps the main loop below its 100 ms gap check. */
    RCC->CR|=RCC_CR_HSEON;t=milliseconds;
    while(!(RCC->CR&RCC_CR_HSERDY))if(milliseconds-t>50){RCC->CR&=~RCC_CR_HSEON;return false;}
    RCC_OscInitTypeDef o={0};o.OscillatorType=RCC_OSCILLATORTYPE_HSE;o.HSEState=RCC_HSE_ON;
    o.PLL.PLLState=RCC_PLL_ON;o.PLL.PLLSource=RCC_PLLSOURCE_HSE;
    o.PLL.PLLM=6;o.PLL.PLLN=SV_PLL1N;o.PLL.PLLP=SV_PLL1P;o.PLL.PLLQ=8;o.PLL.PLLR=8;
    o.PLL.PLLRGE=RCC_PLL1VCIRANGE_2;o.PLL.PLLVCOSEL=RCC_PLL1VCOWIDE;o.PLL.PLLFRACN=0;
    if(HAL_RCC_OscConfig(&o)!=HAL_OK)return false;
    RCC_ClkInitTypeDef c={0};
    c.ClockType=RCC_CLOCKTYPE_SYSCLK|RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_D1PCLK1|RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2|RCC_CLOCKTYPE_D3PCLK1;
    c.SYSCLKSource=RCC_SYSCLKSOURCE_PLLCLK;c.SYSCLKDivider=RCC_SYSCLK_DIV1;c.AHBCLKDivider=SV_FAST_HPRE;
    c.APB3CLKDivider=SV_FAST_APB_DIV(3);c.APB1CLKDivider=SV_FAST_APB_DIV(1);c.APB2CLKDivider=SV_FAST_APB_DIV(2);c.APB4CLKDivider=SV_FAST_APB_DIV(4);
    uwTickPrio=0; /* HAL_InitTick inside ClockConfig: SysTick priority 0 */
    return HAL_RCC_ClockConfig(&c,FLASH_LATENCY_2)==HAL_OK;
}
/* D-cache safety: the SAI/ADC DMA buffers (.dma, D2 SRAM1 0x30000000) and the
 * Bank2 fault-journal sector are mapped normal non-cacheable, so no cache
 * maintenance is needed for DMA or for flash programming read-back. */
static void caches_on(void){
    HAL_MPU_Disable();
    MPU_Region_InitTypeDef r={0};
    r.Enable=MPU_REGION_ENABLE;r.Number=MPU_REGION_NUMBER0;r.BaseAddress=0x30000000u;r.Size=MPU_REGION_SIZE_128KB;
    r.SubRegionDisable=0;r.TypeExtField=MPU_TEX_LEVEL1;r.AccessPermission=MPU_REGION_FULL_ACCESS;
    r.DisableExec=MPU_INSTRUCTION_ACCESS_DISABLE;r.IsShareable=MPU_ACCESS_SHAREABLE;
    r.IsCacheable=MPU_ACCESS_NOT_CACHEABLE;r.IsBufferable=MPU_ACCESS_NOT_BUFFERABLE;
    HAL_MPU_ConfigRegion(&r);
    r.Number=MPU_REGION_NUMBER1;r.BaseAddress=FLASH_BANK2_BASE+7u*128u*1024u;
    HAL_MPU_ConfigRegion(&r);
    HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
    SCB_EnableICache();SCB_EnableDCache();
}
static void clocks_slow(void){
    if(__HAL_RCC_GET_SYSCLK_SOURCE()!=RCC_CFGR_SWS_HSI){
        RCC->CR=(RCC->CR&~RCC_CR_HSIDIV)|RCC_CR_HSIDIV_1;
        RCC_ClkInitTypeDef c={0};
        c.ClockType=RCC_CLOCKTYPE_SYSCLK|RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_D1PCLK1|RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2|RCC_CLOCKTYPE_D3PCLK1;
        c.SYSCLKSource=RCC_SYSCLKSOURCE_HSI;c.SYSCLKDivider=RCC_SYSCLK_DIV1;c.AHBCLKDivider=RCC_HCLK_DIV1;
        c.APB3CLKDivider=RCC_APB3_DIV1;c.APB1CLKDivider=RCC_APB1_DIV1;c.APB2CLKDivider=RCC_APB2_DIV1;c.APB4CLKDivider=RCC_APB4_DIV1;
        uwTickPrio=0;(void)HAL_RCC_ClockConfig(&c,FLASH_LATENCY_7); /* R3 reset latency for journal writes */
    }
    if(__HAL_RCC_GET_SYSCLK_SOURCE()==RCC_CFGR_SWS_HSI){
        __HAL_RCC_PLL_DISABLE();
        /* FW-HSE-LEFT-ON: HSE/CSI off once neither PLL needs them (audio already stopped). */
        if(!(RCC->CR&(RCC_CR_PLL1ON|RCC_CR_PLL2ON|RCC_CR_PLL3ON)))RCC->CR&=~(RCC_CR_HSEON|RCC_CR_CSION);
    }
    RCC->CR=(RCC->CR&~RCC_CR_HSIDIV)|RCC_CR_HSIDIV_8;
}
static void cpu(bool fast){
    if(pot_initialized){sv_pot_adc_stop();pot_initialized=false;}
    if(fast){
        RCC->CR=(RCC->CR&~RCC_CR_HSIDIV)|RCC_CR_HSIDIV_1;systick_start();
        sv_r4_diag.pll1=__HAL_RCC_GET_SYSCLK_SOURCE()==RCC_CFGR_SWS_PLL1 || pll1_start();
    }else clocks_slow();
    systick_start();sv_r4_diag.cpu_hz=SystemCoreClock;
}
static void pots_start(uint32_t now){
    pot_initialized=sv_pot_adc_init();pot_generation=0;factory.ui.fresh=false;factory.ui.picked_up=false;
    sv_pot_init(&pot_scan,sv_pot_adc_bus(),now);
    if(!pot_initialized){pot_scan.fault=true;sv_factory_fault(&factory,SV_D_FAULT_SENSOR);}
}
static void uart_stop(void){
    NVIC_DisableIRQ(USART3_IRQn);sv_rf_reply_cancel(&sv_rf_reply_diag);USART3->CR1=0;uart_on=false;tx_count=0;
    rx_head=rx_tail=0;sv_parser_reset(&parser);unused(GPIOD,3u<<8);
}
static void uart_start(void){
    RCC->D2CCIP2R=(RCC->D2CCIP2R&~RCC_D2CCIP2R_USART28SEL)|(3u<<RCC_D2CCIP2R_USART28SEL_Pos);
    RCC->APB1LENR|=RCC_APB1LENR_USART3EN;(void)RCC->APB1LENR;
    USART3->CR1=0;USART3->CR2=0;USART3->CR3=0;USART3->PRESC=0;USART3->BRR=(64000000u+57600u)/115200u;
    GPIOD->AFR[1]=(GPIOD->AFR[1]&~0xffu)|0x77u;
    /* FW-UART-OVERRUN: PD9 (RF_TX) internal pull-up; the line floats while the ESP boots. */
    GPIOD->PUPDR=(GPIOD->PUPDR&~(3u<<18))|(1u<<18);mode(GPIOD,8,2);mode(GPIOD,9,2);
    rx_head=rx_tail=0;
    USART3->CR3=USART_CR3_EIE;
    USART3->CR1=USART_CR1_FIFOEN|USART_CR1_RXNEIE_RXFNEIE|USART_CR1_RE|USART_CR1_TE|USART_CR1_UE;uart_on=true;
    NVIC_SetPriority(USART3_IRQn,2);NVIC_EnableIRQ(USART3_IRQn);
}
void USART3_IRQHandler(void){
    uint32_t isr=USART3->ISR;
    if(isr&(USART_ISR_ORE|USART_ISR_FE|USART_ISR_NE|USART_ISR_PE)){
        /* Counted only; the parser resynchronises on magic+CRC. Never a latched fault. */
        USART3->ICR=USART_ICR_ORECF|USART_ICR_FECF|USART_ICR_NECF|USART_ICR_PECF;sv_r4_diag.rx_errors++;
    }
    while(USART3->ISR&USART_ISR_RXNE_RXFNE){
        uint8_t b=(uint8_t)USART3->RDR;uint32_t next=(rx_head+1u)%sizeof(rx_ring);
        if(next!=rx_tail){rx_ring[rx_head]=b;rx_head=next;}else sv_r4_diag.rx_drops++;
    }
}
static void power_off(uint32_t now){
    sv_audio_emergency_mute();level(GPIOC,13,false);sv_rf_request(&rf,false,false,now);
    uart_stop();sv_audio_hw_stop();level(GPIOE,2,false);power_state=4;discharged_at=now;
    cpu(false);pots_start(now);selected_peer=false;if(!sv_stm32_i2c1_init())sv_factory_fault(&factory,SV_D_FAULT_SENSOR);
}
static void request_off(void){
    factory.shutdown=true;factory.armed=false;factory.programming=false;
    factory.port=0;factory.window=false;sv_ui_enable(&factory.ui,false);sv_session_end(&factory.session);
}
static void latch_shutdown(void){
    if(sv_safety_shutdown_requested())request_off();
}
static bool evidence(uint32_t now){
    sv_mon_frame f;if(!sv_mon_snapshot(&monitor,now,&f))return false;
#if SV_PRODUCT_MODE
    /* Player window: SYS plausible, TMP117 board -20..60 C. USB port fault lines
     * (PE8/PE9) only gate charging, they must not mute a battery-powered player. */
    return f.mv[SV_MON_SYS]>=2900 && f.mv[SV_MON_SYS]<=4600 && f.temperature_deci_c>=-200 && f.temperature_deci_c<=600;
#else
    /* TMP117 is board temperature, not the cell NTC. Diagnostic window only. */
    return f.mv[SV_MON_SYS]>=2900 && f.mv[SV_MON_SYS]<=4600 && f.temperature_deci_c>=100 && f.temperature_deci_c<=400 &&
        (GPIOE->IDR&((1u<<8)|(1u<<9)))==((1u<<8)|(1u<<9));
#endif
}
/* FW-RT-BUDGET: service the audio DMA halves after every blocking monitor I2C
 * transaction (~0.5 ms at 100 kHz) instead of once per main-loop pass. */
static sv_mon_bus mon_hw;
static void audio_poll(void){
    if(power_state==2 || power_state==3){uint32_t e=sv_audio_hw_service(&factory,milliseconds);if(e)sv_factory_fault(&factory,e);}
}
static bool mon_read(void *c,uint8_t a,uint8_t r,uint8_t *d,size_t n,uint32_t t){bool ok=mon_hw.read(c,a,r,d,n,t);audio_poll();return ok;}
static bool mon_write(void *c,uint8_t a,uint8_t r,const uint8_t *d,size_t n,uint32_t t){bool ok=mon_hw.write(c,a,r,d,n,t);audio_poll();return ok;}
static sv_mon_bus monitor_bus(void){mon_hw=sv_stm32_monitor_bus();sv_mon_bus b={mon_hw.ctx,mon_read,mon_write};return b;}
static void charge_apply(uint32_t now,bool vbus){
    /* FW-NO-CHARGE-PATH: CHARGE_ALLOW (PE14) -> R1601 -> CHARGE_GATE, which the
     * TPS3700 window (U1921 OUTA/OUTB, cell NTC) pulls low out of window; BQ24074
     * TS also stops outside its NTC window. EN1=1/EN2=0 = USB500. No USB-PD. */
    sv_mon_frame f;bool frame=sv_mon_snapshot(&monitor,now,&f);
    sv_charge_in i={0};
    (void)vbus;i.vbus=frame && f.mv[SV_MON_USB]>=4400 && f.mv[SV_MON_USB]<=5600;i.frame_valid=frame;
    i.port_fault=(GPIOE->IDR&((1u<<8)|(1u<<9)))!=((1u<<8)|(1u<<9)); /* TPD2S300 / TPD2S703 FLT_N */
    i.efuse_fault=!(GPIOE->IDR&(1u<<15));                             /* TPS259470 FLT via R1901 */
    i.system_fault=(factory.faults&SV_D_FAULT_POWER)!=0;i.service_image=SV_DIAGNOSTIC_SERVICE_CLEAR;
    i.pack_mv=f.mv[SV_MON_BAT];i.board_deci_c=f.temperature_deci_c;
    charge_out=sv_charge_decide(&charge,&i,now);
    GPIOE->BSRR=sv_input_mode_bsrr(charge_out.en1,charge_out.en2);
    level(GPIOE,14,charge_out.allow);
    charge_gate_tick=milliseconds;
    uint16_t current_ma=0;bool current_valid=frame && sv_mon_charge_current(&f,charge_out.allow,&current_ma);
    sv_charge_diag.version=3;sv_charge_diag.vbus=i.vbus;sv_charge_diag.usb_mv=f.mv[SV_MON_USB];sv_charge_diag.pack_mv=i.pack_mv;
    sv_charge_diag.board_deci_c=(uint32_t)(int32_t)i.board_deci_c;sv_charge_diag.allow=charge_out.allow;
    sv_charge_diag.en1=charge_out.en1;sv_charge_diag.en2=charge_out.en2;sv_charge_diag.port_fault=i.port_fault;
    sv_charge_diag.efuse_fault=i.efuse_fault;sv_charge_diag.chg_status_n=(GPIOD->IDR>>10)&1u;sv_charge_diag.pgood_n=(GPIOB->IDR>>11)&1u;
    sv_charge_diag.iset_estimate_ma=current_ma;sv_charge_diag.iset_estimate_valid=current_valid;
}
/* "Save state" before KILL / on faults: append new fault bits to the Bank2
 * journal once per boot (product), never below 3.1 V pack without USB
 * (FW-FLASH-ECC-BOOTLOOP mitigation); a full/corrupt journal never mutes. */
static void journal_save(bool vbus){
    uint32_t fresh=factory.faults&~logged_faults;
    if(!fresh || !(vbus || sv_battery_mv(&battery)>=3100))return;
    (void)sv_fault_store_append(factory.faults);logged_faults|=factory.faults;
}
static void service_clear_tick(uint8_t keys,uint32_t now){
    sv_mon_frame f;
    bool safe=power_state==0 && !factory.armed && !factory.programming && !factory.shutdown &&
        !sv_safety_shutdown_requested() && !uart_on && !pot_scan.fault && evidence(now) &&
        sv_mon_snapshot(&monitor,now,&f) && f.mv[SV_MON_USB]>=4750 && f.mv[SV_MON_USB]<=5250 &&
        !(GPIOA->ODR&15u) && !(GPIOC->ODR&(SV_PC_RF|SV_PC_AUDIO_BUS)) &&
        !(GPIOE->ODR&(SV_PE_AUDIO_POWER|SV_PE_CHARGE|SV_PE_EN1|SV_PE_EN2)) &&
        (GPIOE->ODR&SV_PE_USB_DISABLE) && recorded==factory.faults &&
        sv_fault_store_service_ready(factory.faults);
    sv_service_poll(&service_clear,keys,factory.faults,safe,now);
    if(sv_service_diag.request!=sv_service_diag.completed){
        uint32_t request=sv_service_diag.request,token=sv_service_diag.token;
        sv_service_diag.result=SV_SERVICE_DENIED;
        if(sv_service_diag.action==1 && sv_service_prepare(&service_clear,factory.faults,safe,now))
            sv_service_diag.result=SV_SERVICE_PENDING;
        else if(sv_service_diag.action==2 && sv_service_consume(&service_clear,token,keys,factory.faults,safe,now)){
            if(sv_fault_store_service_clear(factory.faults,token))sv_service_diag.result=SV_SERVICE_REBOOT_REQUIRED;
            else sv_service_diag.result=SV_SERVICE_FLASH_ERROR;
        }else if(sv_service_diag.action!=1 && sv_service_diag.action!=2)sv_service_cancel(&service_clear);
        __DMB();sv_service_diag.completed=request;
    }
    sv_service_diag.version=1;sv_service_diag.enabled=SV_DIAGNOSTIC_SERVICE_CLEAR;
    sv_service_diag.state=service_clear.state;sv_service_diag.challenge=service_clear.challenge;
    sv_service_diag.faults=factory.faults;
    if(sv_service_diag.result==SV_SERVICE_REBOOT_REQUIRED){
        /* Keep the RAM latch and outputs off. Do not append it over the clear
         * marker. Only a deliberate NRST/power reset can start a new test. */
        for(;;){level(GPIOE,14,false);sv_safety_apply_outputs(0);HAL_IWDG_Refresh(&watchdog);}
    }
}
static sv_result command(const sv_frame *f,uint32_t now){
    latch_shutdown();
    if((f->type==0x31 || f->type==0x3b) && (!evidence(now) || pot_scan.fault))return SV_NOT_READY;
    if(f->type==0x3b && power_state!=0)return SV_NOT_READY;
    if(f->type==0x35){if(f->length)return SV_LENGTH;factory.shutdown=true;factory.armed=false;factory.programming=false;return SV_OK;}
    if((f->type>=0x36 && f->type<=0x39) || f->type==0x3c){
        if(f->length!=(f->type==0x36?6:0))return SV_LENGTH;
        if(!uart_on || !sv_rf_handshake_ready(&rf,now) || !factory.armed || factory.port!=SV_BT || !evidence(now))return SV_NOT_READY;
        if(tx_count || sv_rf_reply_diag.pending)return SV_NOT_READY;
        sv_frame check=*f;check.type=0x34;check.length=0;
        sv_result r=sv_factory_command(&factory,&check,now);if(r!=SV_OK)return r;
        sv_frame out=*f;out.type=f->type==0x36?0x40:f->type==0x37?0x41:f->type==0x38?0x42:f->type==0x39?0x43:0x22;
        if(out.type>=0x40){rf_ka_session=out.session_id;rf_ka_seq=out.seq;rf_ka_at=now;}
        tx_count=sv_frame_encode(&out,tx,sizeof(tx));tx_at=0;tx_started=now;
        sv_rf_reply_begin(&sv_rf_reply_diag,out.type,out.seq,out.session_id,now);
        if(f->type==0x36)selected_peer=false;
#if SV_PRODUCT_MODE
        if(f->type==0x36)sv_bt_learn_peer(&btui,f->payload); /* remembered for the BT key (RAM, this power session) */
#endif
        return SV_OK;
    }
    return sv_factory_command(&factory,f,now);
}
static bool startup_core(void){
    if(sv_crc16((const uint8_t*)"123456789",9)!=0x29b1)return false;
    sv_parser p;sv_parser_reset(&p);
    sv_frame in={.type=0x30,.seq=0x1234,.session_id=0x53562601,.length=3,.payload={0,0x53,0x56}},out;
    uint8_t bytes[270];size_t n=sv_frame_encode(&in,bytes,sizeof(bytes));unsigned received=0;
    if(n!=17)return false;
    for(size_t i=0;i<n;i++)received+=sv_parser_byte(&p,bytes[i],0,&out);
    if(received!=1 || out.type!=in.type || out.seq!=in.seq || out.session_id!=in.session_id || out.length!=3 || memcmp(out.payload,in.payload,3))return false;
    bytes[n-1]^=1;sv_parser_reset(&p);received=0;
    for(size_t i=0;i<n;i++)received+=sv_parser_byte(&p,bytes[i],0,&out);
    return !received;
}
static void uart_service(uint32_t now){
    if(!uart_on)return;
    sv_rf_reply_poll(&sv_rf_reply_diag,now);
    for(unsigned n=0;n<128 && rx_tail!=rx_head;n++){
        uint8_t b=rx_ring[rx_tail];rx_tail=(rx_tail+1u)%sizeof(rx_ring);
        sv_frame f;if(sv_parser_byte(&parser,b,now,&f)){
            if(f.type==0xa0 || f.type==0xa1){
                if(sv_rf_reply_accept(&sv_rf_reply_diag,&f,now)){
                    if(f.type==0xa1)memcpy((void*)sv_rf_pcm_diag,f.payload,32);
                    if(sv_rf_reply_diag.command==0x40)selected_peer=sv_rf_reply_diag.result==SV_OK;
                }
                continue;
            }
            if(f.type==0x80)continue;
            sv_result result=command(&f,now);
            if(!tx_count){sv_frame reply={.type=0xb0,.seq=f.seq,.session_id=f.session_id,.length=9};reply.payload[0]=result;
                memcpy(reply.payload+1,&factory.nonce,4);memcpy(reply.payload+5,&factory.faults,4);
                tx_count=sv_frame_encode(&reply,tx,sizeof(tx));tx_at=0;tx_started=now;}
        }
    }
    sv_parser_poll(&parser,now);
    if(tx_count && (USART3->ISR&USART_ISR_TXE_TXFNF)){USART3->TDR=tx[tx_at++];if(tx_at==tx_count)tx_count=0;}
    /* FW-UART-OVERRUN: a stuck TX is dropped and counted, not a latched fault. */
    if(tx_count && now-tx_started>=250){tx_count=0;sv_r4_diag.tx_timeouts++;}
    /* FW-BT-SECURITY-STREAM (part): ESP quiesces after 2 s without MCU traffic;
     * keep the selected-peer session alive with 0x41 once per second. */
    if(selected_peer && factory.port==SV_BT && !tx_count && !sv_rf_reply_diag.pending && now-rf_ka_at>=1000){
        sv_frame k={.type=0x41,.seq=++rf_ka_seq,.session_id=rf_ka_session};
        tx_count=sv_frame_encode(&k,tx,sizeof(tx));tx_at=0;tx_started=rf_ka_at=now;
        sv_rf_reply_begin(&sv_rf_reply_diag,k.type,k.seq,k.session_id,now);sv_r4_diag.keepalives++;
    }
}
void HardFault_Handler(void){
    /* PCM-03: stop PLL2 (SAI kernel + MCO2) and float the clock/data pins into
     * the V3LOAD domain before AUDIO_PWR_EN goes low: PC9 MCO2, PE3-PE6 SAI1,
     * PE11 SAI2_SD_B, PD11-PD13 SAI2, PD8 USART3_TX (RF_RX). */
    sv_audio_emergency_mute();RCC->CR&=~RCC_CR_PLL2ON;
    GPIOC->MODER|=3u<<18;GPIOE->MODER|=(0xffu<<6)|(3u<<22);GPIOD->MODER|=(0x3fu<<22)|(3u<<16);
    GPIOC->BSRR=SV_PC_AUDIO_BUS<<16;GPIOE->BSRR=SV_PE_AUDIO_POWER<<16;__disable_irq();for(;;)__NOP();
}
void NMI_Handler(void){HardFault_Handler();}
int main(void){
    caches_on(); /* FW-RT-BUDGET: I/D-cache, DMA + journal regions non-cacheable */
    safe_gpio();cpu(false);sv_safety_inputs_init(0);
    watchdog.Instance=IWDG1;watchdog.Init.Prescaler=IWDG_PRESCALER_256;watchdog.Init.Reload=249;watchdog.Init.Window=IWDG_WINDOW_DISABLE;
    if(HAL_IWDG_Init(&watchdog)!=HAL_OK)HardFault_Handler();
    uint32_t reset_flags=RCC->RSR;
    uint32_t retained=sv_fault_store_load(),faults=retained;if(reset_flags&RCC_RSR_IWDG1RSTF)faults|=SV_D_FAULT_RESET;
    RCC->RSR|=RCC_RSR_RMVF;recorded=retained;
#if SV_PRODUCT_MODE
    /* FW-FAULT-LATCH: journal faults are history, not a boot-time mute. */
    /* Only this boot's IWDG reset (if any) is a live fault: it mutes once, recovers and is logged. */
    sv_factory_init(&factory,faults&~retained);logged_faults=retained;sv_r4_diag.retained_faults=faults;
#else
    sv_factory_init(&factory,faults);
#endif
    bool core_ok=startup_core();if(!core_ok)sv_factory_fault(&factory,SV_D_FAULT_PROTOCOL);
    if(!sv_stm32_i2c1_init())sv_factory_fault(&factory,SV_D_FAULT_SENSOR);
    sv_mon_init(&monitor,milliseconds,monitor_bus(),NULL);level(GPIOB,10,true);
    sv_parser_reset(&parser);sv_rf_request(&rf,false,false,milliseconds);pots_start(milliseconds);
    sv_battery_init(&battery);
    bool boot_decided=!SV_PRODUCT_MODE;
    show_until=milliseconds+5000u;
    uint32_t last=milliseconds,last_codec=milliseconds;
    for(;;){
        uint32_t now=milliseconds;
        latch_shutdown();
        if(now-last>=1){
            if(now-last>100)sv_factory_fault(&factory,SV_D_FAULT_RESET);
            last=now;sv_mon_tick(&monitor,now,now>=SV_MON_SETTLE_MS);
            if(pot_initialized)sv_pot_tick(&pot_scan,now);
            if(pot_scan.valid && pot_scan.generation!=pot_generation){
                pot_generation=pot_scan.generation;
                if(!sv_ui_pots(&factory.ui,pot_scan.raw,pot_scan.sampled))sv_factory_fault(&factory,SV_D_FAULT_SENSOR);
            }
            if(pot_scan.fault)sv_factory_fault(&factory,SV_D_FAULT_SENSOR);
            /* VBUS: PA9 (USB_5V_SAFE/2, near VIH at 4.75 V) or the ADS1115 USB channel. */
            sv_mon_frame mf;bool mframe=sv_mon_snapshot(&monitor,now,&mf);
            bool vbus=vbus_present() || (mframe && mf.mv[SV_MON_USB]>=4000);if(vbus)vbus_seen_at=now;
            if(mframe)sv_battery_update(&battery,mf.mv[SV_MON_BAT],mf.generation,vbus,now);
            if(!boot_decided && (mframe || now>=1500)){
                /* FW-USB-SHUTDOWN-LATCH: powered only by USB (no LTC2954 turn-on) => charge-only standby. */
                boot_decided=true;
                /* R4 E-11: a power-key wake reboots via NVIC_SystemReset (SFTRSTF) or the key is still held. */
                bool key_on=(reset_flags&RCC_RSR_SFTRSTF)!=0 || pwr_key_low();
                if(vbus && !key_on){request_off();pwr.state=SV_PWR_STANDBY;}
            }
#if SV_PRODUCT_MODE
            /* FW-NO-UVLO: filtered PACK < 3.30 V for 3 s on battery => orderly off. */
            if(battery.shutdown && pwr.state==SV_PWR_RUN && !factory.shutdown)request_off();
#endif
            bool healthy=evidence(now);bool chord=(GPIOA->IDR&((1u<<5)|(1u<<6)))==0;
            sv_factory_tick(&factory,chord,healthy,healthy,now);
            uint8_t keys=(uint8_t)((~GPIOA->IDR>>5)&7u);if(!(GPIOC->IDR&1u))keys|=8;
            unsigned bt_action=sv_factory_buttons(&factory,keys,now);
            if(factory.ui.events!=ui_events_seen){ui_events_seen=factory.ui.events;show_until=now+5000u;}
            if(factory.ui.enabled && !factory.ui.fresh)sv_factory_fault(&factory,SV_D_FAULT_SENSOR);
#if SV_PRODUCT_MODE
            if(bt_action && factory.product){
                /* R4 product BT key: short = BT route on/off, long (>=2 s) = pairing window for the known peer. */
                uint8_t port=sv_bt_key(&btui,bt_action,factory.port,now);
                if(port==SV_SPK && sv_safety_hp_inserted())port=SV_HP;
                factory.port=port;sv_ui_diag.bt_result=(bt_action==2 && !btui.have_peer)?SV_NOT_READY:SV_OK;
            }else
#endif
            if(bt_action){
                sv_frame f={.type=bt_action==1?0x38:0x39,.seq=(uint16_t)(factory.session.last_seq+1),.session_id=factory.session.session_id};
                sv_ui_diag.bt_result=selected_peer?command(&f,now):SV_NOT_READY;
            }
            if(monitor.fault)sv_factory_fault(&factory,SV_D_FAULT_SENSOR);
            if(sv_diag.request!=sv_diag.completed){
                sv_frame f={.type=(uint8_t)sv_diag.type,.length=(uint16_t)sv_diag.length,.session_id=sv_diag.session,.seq=(uint16_t)sv_diag.seq};
                if(sv_diag.length>256)sv_diag.result=SV_LENGTH;
                else {for(unsigned n=0;n<64;n++)memcpy(f.payload+n*4,(const void*)&sv_diag.payload[n],4);sv_diag.result=command(&f,now);}
                __DMB();sv_diag.completed=sv_diag.request;
            }
            latch_shutdown();
#if SV_PRODUCT_MODE
            /* FW-FAULT-LATCH: product state machine. A fault mutes (power_off below),
             * waits 1,2,4..30 s, re-initialises the failed block and re-arms. */
            bool hp_now=sv_safety_hp_inserted();
            if(hp_now!=hp_was){if(factory.armed)factory.port=sv_hp_auto_route(factory.port,hp_was,hp_now);hp_was=hp_now;}
            if(factory.armed && factory.port)user_port=factory.port;
            if(boot_decided && !factory.armed && !factory.shutdown && !power_state && pwr.state==SV_PWR_RUN){
                if(factory.faults){
                    if(!recover_pending){recover_pending=true;recover_at=now+sv_recover_delay(recover_count);}
                    else if((int32_t)(now-recover_at)>=0){
                        recover_pending=false;recover_count++;sv_r4_diag.recoveries++;
                        if(monitor.fault){(void)sv_stm32_i2c1_init();sv_mon_init(&monitor,now,monitor_bus(),NULL);}
                        if(pot_scan.fault)pots_start(now);
                        factory.faults=0;
                    }
                }else if(healthy && factory.ui.fresh && !pot_scan.fault){
                    uint8_t port=hp_now?SV_HP:(user_port==SV_LINE || user_port==SV_BT)?user_port:SV_SPK;
                    sv_factory_product_arm(&factory,port,now);recovered_at=now;
                }
            }
            if(recover_count && power_state==3 && now-recovered_at>=SV_RECOVER_STABLE_MS)recover_count=0;
#endif
            if((!factory.armed || factory.faults || factory.shutdown) && power_state && power_state!=4)power_off(now);
            if(power_state==4 && now-discharged_at>=1000){power_state=0;level(GPIOC,5,false);mode(GPIOC,5,1);}
            if(factory.armed && healthy && !factory.shutdown && !sv_safety_shutdown_requested() && !power_state){
                cpu(!factory.programming);pots_start(now);if(!sv_stm32_i2c1_init())sv_factory_fault(&factory,SV_D_FAULT_SENSOR);
                latch_shutdown();
                if(factory.armed && !factory.faults && !factory.shutdown){
                    if(factory.programming){uart_stop();unused(GPIOC,1u<<5);level(GPIOC,13,false);}
                    level(GPIOE,2,true);rail_at=now;power_state=1;
                }
            }
            if(power_state==1 && now-rail_at>=50){
                if(factory.programming)power_state=5;
                else {
                    level(GPIOC,13,true);
                    if(!sv_audio_hw_start())sv_factory_fault(&factory,SV_D_FAULT_CLOCK);
                    else {sv_pcm_start(&codec,sv_stm32_codec_bus(),now);codec_gate=false;power_state=2;}
                }
            }
            if(power_state==2 && now-last_codec>=1){last_codec=now;sv_pcm_tick(&codec,now);
                if(codec.fault)sv_factory_fault(&factory,SV_D_FAULT_CODEC);
                else if(codec.ready){
                    if(!codec_gate){sv_audio_hw_codec_ready(now);codec_gate=true;}
                    if(sv_audio_hw_ready(now)){power_state=3;status_at=now;status_index=0;}
                }
            }
            if(power_state==3 && now-status_at>=20){
                static const uint8_t regs[]={0x72,0x73,0x74,0x75,0x78},masks[]={15,7,127,255,7},values[]={15,3,0x34,0,7};
                uint8_t v;status_at=now;
                if(!codec.bus.read(codec.bus.ctx,regs[status_index],&v) || (v&masks[status_index])!=values[status_index])sv_factory_fault(&factory,SV_D_FAULT_CODEC);
                status_index=(status_index+1)%5;audio_poll();
            }
#if SV_PRODUCT_MODE
            /* Product UI (wheels/keys) is enabled only once audio runs and the pots are fresh. */
            if(factory.product && factory.armed && power_state==3 && !factory.ui.enabled && factory.ui.fresh){
                sv_ui_enable(&factory.ui,true);factory.ui.auto_pickup=true;factory.ui.picked_up=true;
            }
#endif
            latch_shutdown();
            if(factory.shutdown && power_state && power_state!=4)power_off(now);
            bool rf_on=sv_rf_request(&rf,power_state==3 && factory.port==SV_BT,factory.armed && healthy && !factory.faults && !factory.shutdown,now);
            level(GPIOC,5,rf_on);if(sv_rf_handshake_ready(&rf,now) && !uart_on)uart_start();
            if(!rf_on && uart_on)uart_stop();
            if(!rf_on)selected_peer=false;
            bool bt_connected=selected_peer && sv_rf_reply_diag.generation && now-sv_rf_reply_diag.received_at<3000u &&
                sv_rf_reply_diag.status[3] && sv_rf_reply_diag.status[5]; /* ESP status: connected && encrypted */
#if SV_PRODUCT_MODE
            /* Send the existing 0x36 (-> ESP 0x40 with the peer BDADDR) through the normal command path
             * once the ESP link is up; repeat after a reply timeout until accepted or 8 s. */
            if(btui.pending){
                if(factory.port!=SV_BT || selected_peer || now-btui.pending_at>=SV_BT_SEND_TIMEOUT_MS)btui.pending=false;
                else if(uart_on && sv_rf_handshake_ready(&rf,now) && !tx_count && !sv_rf_reply_diag.pending){
                    sv_frame f={.type=0x36,.seq=(uint16_t)(factory.session.last_seq+1),.session_id=factory.session.session_id,.length=6};
                    memcpy(f.payload,btui.peer,6);
                    if(command(&f,now)==SV_OK){btui.window=true;btui.window_at=now;}
                }
            }
#endif
            if(factory.port!=previous_port){previous_port=factory.port;port_changed=now;}
            uint8_t desired=0;
            if(power_state==3 && sv_audio_hw_ready(now) && factory.armed && factory.mode && sv_ui_audible(&factory.ui) && healthy && !factory.faults && now-port_changed>=50 &&
               (!factory.product || factory.ui.enabled)){
                /* FW-PORT-ENABLE-HP: HP = PA0|PA1|PA3; AUX/RETURN input adds PA3 in every route. */
                desired=sv_route_outputs(factory.port,factory.input);
                if(factory.port==SV_HP && !sv_safety_headphone_permitted())desired=0;
                if(factory.port==SV_SPK && !sv_safety_speaker_permitted())desired=0;
            }
            sv_safety_apply_outputs(desired);
            charge_apply(now,vbus);
            /* FW-USB-SHUTDOWN-LATCH / FW-NO-UVLO: mute -> save -> KILL low. If still
             * alive 1.5 s later USB holds V3D: release KILL, charge-only standby, and
             * leave it again on PWR/key (or LTC EN with the ECO) or VBUS loss. */
            bool off=factory.shutdown && (power_state==0 || power_state==4);
            if(off && pwr.state==SV_PWR_RUN)journal_save(vbus);
            uint8_t before=pwr.state;bool kill=sv_power_kill(&pwr,off,now);
            level(GPIOE,7,!kill);
            if(before==SV_PWR_KILL && pwr.state==SV_PWR_STANDBY)sv_safety_rearm(now);
#if SV_HAS_PWR_PB_SENSE
            /* R4: in standby the key is read on PB12; an LTC INT edge must not hold the guard latched. */
            if(pwr.state==SV_PWR_STANDBY && sv_safety_shutdown_requested())sv_safety_rearm(now);
#endif
            if(sv_power_pb_wake(&pwr,pwr_key_low(),now)){
                /* R4 E-11 / FW-USB-SHUTDOWN-LATCH: clear the latch and restart into play. */
                sv_safety_rearm(now);factory.shutdown=false;GPIOC->BSRR=7u<<(6+16);__DSB();NVIC_SystemReset();
            }
            if(sv_power_standby_wake(&pwr,sv_safety_shutdown_requested(),keys!=0,now-vbus_seen_at<300u)){ /* VBUS loss debounced 300 ms */
                sv_safety_rearm(now);pwr.state=SV_PWR_RUN;factory.shutdown=false;sv_battery_init(&battery);
                recover_count=0;recover_pending=false;factory.faults=0;show_until=now+5000u;
            }
#if !SV_PRODUCT_MODE
            if(factory.faults!=recorded && (power_state==0 || power_state==4)){
                if(sv_fault_store_append(factory.faults))recorded=factory.faults;
                else {factory.faults|=SV_D_FAULT_RESET;recorded=factory.faults;}
            }
#else
            if(factory.faults && (power_state==0 || power_state==4))journal_save(vbus);
#endif
            {
                sv_led_in li={.playing=power_state==3,.charging=charge_out.allow && !(GPIOD->IDR&(1u<<10)),.usb=vbus,
                    .warn=battery.warn,.fault=factory.faults!=0 && !factory.shutdown,.standby=pwr.state==SV_PWR_STANDBY,
                    .pack_mv=sv_battery_mv(&battery),.show_until=show_until,
#if SV_PRODUCT_MODE
                    .bt=sv_bt_led_state(&btui,factory.port==SV_BT && rf_on,bt_connected,now)
#else
                    .bt=(uint8_t)(bt_connected?SV_BT_LED_ON:SV_BT_LED_OFF)
#endif
                    };
                uint8_t leds=(factory.shutdown && pwr.state!=SV_PWR_STANDBY)?0:sv_led_pattern(&li,now);
                GPIOC->BSRR=((uint32_t)(leds&7u)<<6)|((uint32_t)(~leds&7u)<<(6+16));sv_r4_diag.leds=leds;
            }
            service_clear_tick(keys,now);
            HAL_IWDG_Refresh(&watchdog);
            sv_diag.nonce=factory.nonce;sv_diag.faults=factory.faults;sv_diag.state=power_state;
            sv_diag.pairs=sv_audio_hw_pairs();sv_diag.monitor_generation=monitor.frame.generation;
            sv_diag.selftest=(core_ok?1u:0u)|(healthy?2u:0u)|(codec.ready?4u:0u)|(power_state==3 && sv_audio_hw_ready(now)?8u:0u);
            sv_diag.temperature_deci_c=monitor.frame.temperature_deci_c;
            for(unsigned n=0;n<4;n++)sv_diag.mv[n]=monitor.frame.mv[n];
            sv_ui_diag.version=1;for(unsigned n=0;n<3;n++)sv_ui_diag.raw[n]=pot_scan.raw[n];
            sv_ui_diag.generation=pot_scan.generation;sv_ui_diag.sampled=pot_scan.sampled;sv_ui_diag.adc_fault=pot_scan.fault;
            sv_ui_diag.ui_enabled=factory.ui.enabled;sv_ui_diag.picked_up=factory.ui.picked_up;sv_ui_diag.muted=factory.ui.muted;
            sv_ui_diag.fx=factory.ui.fx;sv_ui_diag.rate=factory.ui.rate;sv_ui_diag.input=factory.input;sv_ui_diag.port=factory.port;
            sv_ui_diag.events=factory.ui.events;sv_ui_diag.session_seq=factory.session.last_seq;
            sv_ui_diag.program_remaining_ms=factory.programming?300000-(now-factory.armed_at):0;
            sv_r4_diag.version=1;sv_r4_diag.product=SV_PRODUCT_MODE;sv_r4_diag.hw_rev_r4=SV_HW_REV_R4;
            sv_r4_diag.hp_active_high=HP_DETECT_ACTIVE_HIGH;sv_r4_diag.battery_mv=sv_battery_mv(&battery);
            sv_r4_diag.battery_warn=battery.warn;sv_r4_diag.battery_off=battery.shutdown;sv_r4_diag.power=pwr.state;
            sv_r4_diag.hp_inserted=sv_safety_hp_inserted();
        }
        audio_poll();
        uart_service(now);
    }
}
