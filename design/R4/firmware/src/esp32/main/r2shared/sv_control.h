#ifndef SV_CONTROL_H
#define SV_CONTROL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Portable control core, not a board firmware or a hardware safety interlock. */
enum { SV_HP=1, SV_LINE=2, SV_SPK=4, SV_BT=8 };
typedef enum { SV_BOOT, SV_READY, SV_FAULT, SV_STOPPING, SV_OFF } sv_state;
enum { SV_F_POWER=1, SV_F_CLOCK=2, SV_F_PORT=4, SV_F_TIMING=8,
       SV_F_BOOT=16, SV_F_INPUT=32, SV_F_CHARGER=64 };
typedef struct {
    bool power_good, clocks_good, codec_ready, usb_phy_ready;
    bool external_fault, cc_fault, usb_data_fault;
    bool headphones_raw, bt_button_raw, power_interrupt;
    bool usb_present, usb_configured, usb_suspended;
    bool battery_present, temperature_valid, speaker_calibrated;
    bool usb_measurement_valid, board_budget_valid;
    uint16_t usb_budget_ma, board_usb_budget_ma, usb_mv, battery_mv;
    int16_t temperature_deci_c;
    bool startup_selftest_passed, battery_measurement_valid;
    bool usb_authorization_valid, physical_usb_valid, charger_fault;
    bool bluetooth_authenticated;
    bool v3d_measurement_valid;
    uint16_t v3d_mv;
    uint32_t board_evidence_at;
} sv_inputs;
typedef struct {
    /* Zero-initialized configuration disables charging. Not remotely writable. */
    bool pack_approved, charging_path_approved;
    uint16_t charge_current_worst_ma, charge_overhead_ma;
    int16_t charge_min_deci_c, charge_max_deci_c;
    /* Approved cell safety ceiling, NOT the normal CC/CV termination voltage. */
    uint16_t pack_safety_max_mv, battery_error_bound_mv;
} sv_config;
typedef struct {
    bool boot_hold, dac_unmute, hp_enable, speaker_enable, port_enable;
    bool bluetooth_audio, usb_enable, charge_allow, chg_en1, chg_en2;
    bool feed_watchdog;
    uint8_t active_routes;
} sv_outputs;
typedef struct { bool raw, stable; uint32_t changed; } sv_debounce;
typedef struct {
    sv_state state;
    uint32_t faults, boot_at, last_tick, state_at, healthy_at, pair_at, bt_at;
    bool healthy_tracking, pair_open, pair_used, bt_consumed, bt_tracking;
    uint8_t requested_routes;
    int16_t gain_deci_db;
    sv_debounce hp, bt;
    sv_inputs input;
    sv_config config;
    sv_outputs out;
} sv_control;
void sv_init(sv_control *c, uint32_t now, const sv_config *cfg);
void sv_tick(sv_control *c, uint32_t now, const sv_inputs *in);
bool sv_set_routes(sv_control *c, uint8_t routes);
bool sv_ack_fault_local(sv_control *c, uint32_t now);
bool sv_take_pair_window(sv_control *c, uint32_t now);
void sv_stop_local(sv_control *c, uint32_t now);

typedef struct {
    uint8_t bytes[270];
    uint16_t count;
    uint32_t started_at, errors;
} sv_parser;
typedef struct {
    uint8_t type;
    uint16_t seq, length;
    uint32_t session_id;
    uint8_t payload[256];
} sv_frame;
typedef struct { bool authorized, have_seq; uint32_t session_id; uint16_t last_seq; } sv_session;
typedef enum { SV_OK, SV_AUTH, SV_FRAME, SV_LENGTH, SV_RANGE, SV_REPLAY,
               SV_NOT_READY, SV_PHYSICAL } sv_result;
uint16_t sv_crc16(const uint8_t *bytes, size_t length);
bool sv_frame_type_known(uint8_t type);
void sv_parser_reset(sv_parser *p);
void sv_parser_poll(sv_parser *p, uint32_t now);
bool sv_parser_byte(sv_parser *p, uint8_t byte, uint32_t now, sv_frame *out);
size_t sv_frame_encode(const sv_frame *f, uint8_t *out, size_t capacity);
bool sv_session_begin_trusted(sv_session *s, uint32_t session_id);
void sv_session_end(sv_session *s);
sv_result sv_execute(sv_control *c, sv_session *s, const sv_frame *f, uint32_t now);
#endif
