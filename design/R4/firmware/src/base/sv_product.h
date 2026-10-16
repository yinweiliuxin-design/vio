#ifndef SV_PRODUCT_H
#define SV_PRODUCT_H
/* R4 product behaviour helpers (portable, host-tested). Pure functions/state
 * machines only; stm32/main.c applies the results to GPIO. */
#include <stdbool.h>
#include <stdint.h>
#include "sv_hw_rev.h"
/* 1 = R4 product image: powers up playable, faults auto-recover (no permanent
 * flash latch), auto HP/SPK routing, UVLO, simple charging. 0 = R3 bench flow. */
#ifndef SV_PRODUCT_MODE
#define SV_PRODUCT_MODE 1
#endif

/* PA0 DAC_UNMUTE, PA1 HP_EN_VALIDATED, PA2 SPK_ENABLE, PA3 PORT_ENABLE (R3: all 7
 * PhotoMOS; R4 E-03: LINE L/R + FX SEND only), R4: PD14 HP group, PD15 RET group. */
enum {SV_OUT_DAC=1u<<0,SV_OUT_HP=1u<<1,SV_OUT_SPK=1u<<2,SV_OUT_PORTS=1u<<3,SV_OUT_HPGRP=1u<<4,SV_OUT_RETGRP=1u<<5};
/* FW-PORT-ENABLE-HP: HP needs its PhotoMOS (K1201/K1202 in series with HP_L/R);
 * AUX/RETURN input (K1206/K1207) needs its PhotoMOS in every route. */
uint8_t sv_route_outputs(uint8_t port,uint8_t input);

/* UVLO on PACK_PLUS (ADS1115 AIN1, SV_MON_BAT; R1705 15k/R1706 10k, buffered). */
enum {SV_BAT_WARN_MV=3450,SV_BAT_WARN_CLEAR_MV=3550,SV_BAT_OFF_MV=3300,
      SV_BAT_OFF_HOLD_MS=3000,SV_BAT_FLASH_MIN_MV=3500};
typedef struct {
    bool valid,warn,shutdown;
    uint32_t filtered_mv_x8,generation,low_since;bool low_tracking;
} sv_battery;
void sv_battery_init(sv_battery *);
/* Call once per new monitor frame (generation changes). usb: VBUS present. */
void sv_battery_update(sv_battery *,uint16_t pack_mv,uint32_t generation,bool usb,uint32_t now);
uint16_t sv_battery_mv(const sv_battery *);

/* FW-NO-CHARGE-PATH: simple charge enable. The TPS3700 (U1921) cell-NTC window
 * and the BQ24074 TS pin gate CE in hardware after CHARGE_ALLOW (R1601/Q1601),
 * so firmware only adds: VBUS present, no USB/charger fault, plausible pack
 * voltage, board temperature sane, input fresh, 2 s qualification. */
typedef struct {
    bool vbus,frame_valid,port_fault,efuse_fault,system_fault,service_image;
    uint16_t pack_mv;int16_t board_deci_c;
} sv_charge_in;
/* Normal-charging release gate (work item P23 / test stage CHARGE). 0 = default for the
 * first sample: CHARGE_ALLOW stays low whatever the conditions; the decision still runs
 * and `qualified` reports what it would do. Build the -CHARGE-TEST image
 * (SV_R4_CHARGE_RELEASE=1) only after the VARTA pack NTC curve and stages B00-B12 are
 * signed off; the product image flips the default only after stage CHARGE passes. */
#ifndef SV_R4_CHARGE_RELEASE
#define SV_R4_CHARGE_RELEASE 0
#endif
typedef struct {bool allow,en1,en2,qualified;} sv_charge_out;
typedef struct {bool qualifying;uint32_t since;} sv_charge;
enum {SV_CHG_QUALIFY_MS=2000,SV_CHG_PACK_MIN_MV=2500,SV_CHG_PACK_MAX_MV=4250,
      SV_CHG_TEMP_MIN_DECI_C=0,SV_CHG_TEMP_MAX_DECI_C=450};
sv_charge_out sv_charge_decide(sv_charge *,const sv_charge_in *,uint32_t now);

/* FW-FAULT-LATCH: retry delay after a muting fault; never a permanent latch. */
enum {SV_RECOVER_FIRST_MS=1000,SV_RECOVER_MAX_MS=30000,SV_RECOVER_STABLE_MS=60000};
uint32_t sv_recover_delay(uint32_t attempts);

/* Q7 auto routing on debounced HP detect edges. Returns new port. */
uint8_t sv_hp_auto_route(uint8_t port,bool was_inserted,bool inserted);

/* R4 product BT key (MCU side only, existing frames). Short press toggles the BT
 * route (RF_ENABLE/ESP power + UART) and, if a peer is known, re-opens it; long
 * press (>=2 s) opens the ESP 60 s pairing/connect window for the known peer by
 * sending the normal 0x36 -> 0x40 frame. The ESP firmware has no inquiry/discovery,
 * so the peer BDADDR must come from a 0x36 (bench/app) earlier in this power session. */
enum {SV_BT_WINDOW_MS=60000,SV_BT_SEND_TIMEOUT_MS=8000};
/* req = address sent with the pending 0x36: the known peer, 6x00 (ESP reconnects its
 * NVS-stored headset or searches) or 6xFF (search for a new headset). */
typedef struct {uint8_t prev_port,peer[6],req[6];bool have_peer,pending,window;uint32_t pending_at,window_at;} sv_bt_ui;
void sv_bt_learn_peer(sv_bt_ui *,const uint8_t peer[6]);
/* action 1=short (BT on: reconnect; BT off), 2=long (pair a new headset). Returns the new port. */
uint8_t sv_bt_key(sv_bt_ui *,unsigned action,uint8_t port,uint32_t now);
/* LED2 while the BT route is on: connected solid, pairing window slow blink, else off. */
enum {SV_BT_LED_OFF,SV_BT_LED_BLINK,SV_BT_LED_ON};
uint8_t sv_bt_led_state(const sv_bt_ui *,bool bt_route,bool connected,uint32_t now);
/* LED_ZONE_1..3 (PC6..PC8) pattern, bit n = LED n+1. */
typedef struct {bool playing,charging,usb,warn,fault,standby;uint16_t pack_mv;uint32_t show_until;uint8_t bt;} sv_led_in;
uint8_t sv_led_pattern(const sv_led_in *,uint32_t now);

/* FW-USB-SHUTDOWN-LATCH: power state after a shutdown request. */
enum {SV_PWR_RUN,SV_PWR_KILL,SV_PWR_STANDBY};
enum {SV_KILL_HOLD_MS=1500};
typedef struct {uint8_t state;bool pb_released,pb_tracking;uint32_t kill_at,pb_since;} sv_power;
/* kill_requested: shutdown latched and audio already off. Returns true while KILL
 * (PE7) must be LOW. After SV_KILL_HOLD_MS still alive => USB holds V3D =>
 * STANDBY (KILL released HIGH so a later PWR turn-on is accepted). */
bool sv_power_kill(sv_power *,bool kill_requested,uint32_t now);
/* In STANDBY, software re-init into play on: VBUS loss while still alive (the
 * LTC2954 must be on); R3 board also on PWR INT edge or any front key. */
bool sv_power_standby_wake(const sv_power *,bool pwr_event,bool key,bool vbus);
/* R4 E-11: PB12 (PWR_PB_SENSE) low >= 50 ms in STANDBY, after it was seen released
 * there, requests clear-latch + NVIC_SystemReset into play. */
enum {SV_PB_WAKE_MS=50};
bool sv_power_pb_wake(sv_power *,bool pb_low,uint32_t now);
#endif
