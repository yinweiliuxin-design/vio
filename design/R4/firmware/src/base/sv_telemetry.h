#ifndef SV_TELEMETRY_H
#define SV_TELEMETRY_H
#include "sv_control.h"

enum { SV_MON_USB, SV_MON_BAT, SV_MON_SYS, SV_MON_ISET, SV_MON_CHANNELS };
enum { SV_MON_BUS=1, SV_MON_CONFIG=2, SV_MON_TIMEOUT=4, SV_MON_RANGE=8,
       SV_MON_TIMING=16, SV_MON_ID=32 };
/* 7-bit addresses; big-endian register words. HAL must return within timeout_ms. */
typedef bool (*sv_i2c_read)(void *, uint8_t, uint8_t, uint8_t *, size_t, uint32_t);
typedef bool (*sv_i2c_write)(void *, uint8_t, uint8_t, const uint8_t *, size_t, uint32_t);
typedef struct { void *ctx; sv_i2c_read read; sv_i2c_write write; } sv_mon_bus;
typedef struct {
    bool electrical_calibration_approved, thermal_attachment_approved;
    int32_t gain_ppm[SV_MON_CHANNELS];
    int16_t offset_mv[SV_MON_CHANNELS];
} sv_mon_cal;
typedef struct {
    bool valid;
    uint16_t mv[SV_MON_CHANNELS];
    int16_t temperature_deci_c;
    uint32_t started_at, completed_at, generation;
} sv_mon_frame;
typedef struct {
    sv_mon_bus bus;
    sv_mon_cal cal;
    sv_mon_frame frame;
    uint32_t fault, last_tick, stage_at, frame_at, published_at;
    uint16_t pending_mv[SV_MON_CHANNELS];
    uint8_t stage, channel;
    bool initialized;
} sv_monitor;
void sv_mon_init(sv_monitor *, uint32_t, sv_mon_bus, const sv_mon_cal *);
void sv_mon_tick(sv_monitor *, uint32_t, bool rail_and_switch_settled);
bool sv_mon_snapshot(const sv_monitor *, uint32_t, sv_mon_frame *);
/* ADS1115 channel divider ratio x1000 (R4 E-02: PACK/SYS 2687, USB 2650, ISET 1000). */
uint32_t sv_mon_divider_x1000(unsigned channel);
/* ISET estimate only during qualified active charging; mirror is +/-10%. */
bool sv_mon_charge_current(const sv_mon_frame *, bool actively_charging, uint16_t *ma);

/* One enabled charging interval per physical USB session. No auto fault retry. */
typedef struct {
    bool locked, started, qualifying, absent_tracking, have_tick;
    uint32_t qualified_at, absent_at, last_tick;
} sv_charge_guard;
void sv_guard_init(sv_charge_guard *);
/* Call before sv_tick. This replaces caller-supplied voltage/temperature validity. */
void sv_mon_apply(const sv_monitor *, uint32_t, sv_inputs *);
void sv_power_status_apply(sv_inputs *, bool gpio_valid, bool pgood_n, bool efuse_fault_n);
/* Call LAST after all control/protocol mutations; only then apply GPIO outputs. */
void sv_guard_apply(sv_charge_guard *, sv_control *, uint32_t, bool usb_physically_present);
#endif
