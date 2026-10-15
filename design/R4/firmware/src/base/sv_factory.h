#ifndef SV_FACTORY_H
#define SV_FACTORY_H
#include "sv_control.h"
#include "sv_speaker.h"
#include "sv_ui.h"
enum {SV_D_POWER=1,SV_D_ADC=2,SV_D_LINE=4,SV_D_HP=8,SV_D_SPK=16,SV_D_RF=32};
enum {SV_D_FAULT_POWER=1,SV_D_FAULT_SENSOR=2,SV_D_FAULT_DMA=4,SV_D_FAULT_CODEC=8,SV_D_FAULT_CLOCK=16,SV_D_FAULT_RESET=32,SV_D_FAULT_PROTOCOL=64};
typedef struct {
    uint32_t faults,nonce,opened_at,held_at,armed_at,last_command;
    bool holding,chord_used,window,armed,shutdown,programming,product;uint8_t grants,port,mode,input;
    sv_session session;
    sv_speaker speaker;
    sv_ui ui;
} sv_factory;
void sv_factory_init(sv_factory *,uint32_t retained_faults);
void sv_factory_tick(sv_factory *,bool chord,bool rails,bool sensor,uint32_t now);
sv_result sv_factory_command(sv_factory *,const sv_frame *,uint32_t now);
void sv_factory_fault(sv_factory *,uint32_t);
/* R4 FW-FAULT-LATCH: product (player) arm. All routes granted, live input,
 * no 2 s/60 s command timeouts. Faults still disarm; the caller retries. */
enum {SV_PRODUCT_SESSION=0x53565234u};
void sv_factory_product_arm(sv_factory *,uint8_t port,uint32_t now);
/* Returns BT action:1=disconnect,2=reconnect selected peer; no new grants. */
unsigned sv_factory_buttons(sv_factory *,uint8_t pressed,uint32_t now);
/* Factory mailbox/UART is not a security boundary: requires physical chord,
 * read nonce, explicit bench/load grants. Never grants charging or USB data. */
int32_t sv_sample24(uint32_t word);
void sv_factory_render(sv_factory *,const uint32_t *a,const uint32_t *b,
                       uint32_t *dac,uint32_t *speaker,size_t frames,uint32_t *phase);
#endif
