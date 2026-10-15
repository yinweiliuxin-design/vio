#include "sv_control.h"
#include "sv27_power_profile.h"
#include <string.h>

static uint32_t elapsed(uint32_t now, uint32_t then) { return now - then; }
static bool running(const sv_control *c) { return c->state == SV_READY && c->faults == 0; }
static void safe_outputs(sv_control *c) {
    memset(&c->out, 0, sizeof(c->out));
    /* Preserve the 100mA bootstrap path. CE authorization is independently LOW.
     * Standby disconnects IN and is only selected for actual USB suspend. */
    c->out.chg_en1 = c->input.usb_suspended;
    c->out.chg_en2 = c->input.usb_suspended;
    c->out.boot_hold = c->state != SV_OFF;
}
static void trip(sv_control *c, uint32_t faults, uint32_t now) {
    c->faults |= faults;
    c->state = SV_FAULT;
    c->state_at = now;
    c->healthy_tracking = false;
    c->requested_routes = 0;
    c->pair_open = false;
    c->bt_tracking = false;
    safe_outputs(c);
}
static bool debounce(sv_debounce *d, bool raw, uint32_t now) {
    if (d->raw != raw) { d->raw = raw; d->changed = now; }
    if (d->stable != d->raw && elapsed(now, d->changed) >= 30) {
        d->stable = d->raw;
        return true;
    }
    return false;
}
static bool healthy(const sv_inputs *i) {
    return i->power_good && i->clocks_good && i->codec_ready &&
        i->startup_selftest_passed && !i->charger_fault &&
        !i->external_fault && !i->cc_fault && !i->usb_data_fault;
}
static bool config_valid(const sv_config *p) {
    return p->pack_approved && p->charging_path_approved &&
        p->charge_current_worst_ma == SV27_CHARGE_WORST_MA &&
        p->charge_overhead_ma >= SV27_MIN_OVERHEAD_MA && p->charge_overhead_ma <= 50 &&
        p->charge_min_deci_c >= 0 && p->charge_max_deci_c <= 450 &&
        p->charge_min_deci_c < p->charge_max_deci_c &&
        p->battery_error_bound_mv >= 1 && p->battery_error_bound_mv <= 50 &&
        p->pack_safety_max_mv <= SV27_PACK_MAX_MV &&
        p->pack_safety_max_mv > 4230u + 2u*p->battery_error_bound_mv;
}
static void update_outputs(sv_control *c) {
    safe_outputs(c);
    const sv_inputs *i = &c->input;
    bool ready = running(c);
    c->out.feed_watchdog = c->state != SV_FAULT && c->state != SV_OFF;
    /* The adapter must independently measure and bound USB_5V_SAFE. */
    bool usb = i->usb_present && i->usb_measurement_valid && i->usb_mv >= 4500 && i->usb_mv <= 5500 &&
        !i->cc_fault && !i->usb_data_fault && !i->external_fault;
    c->out.usb_enable = (c->state == SV_BOOT || ready) && usb && i->usb_phy_ready;
    if (!ready) return;
    uint8_t bits = c->requested_routes;
    if (elapsed(c->last_tick,c->state_at)<50) bits=0;
    if (!c->hp.stable || !i->headphones_raw) bits &= (uint8_t)~SV_HP;
    if (c->hp.stable || i->headphones_raw || !i->speaker_calibrated) bits &= (uint8_t)~SV_SPK;
    c->out.active_routes = bits;
    c->out.hp_enable = (bits & SV_HP) != 0;
    c->out.speaker_enable = (bits & SV_SPK) != 0;
    if (!i->bluetooth_authenticated) bits &= (uint8_t)~SV_BT;
    c->out.active_routes = bits;
    c->out.bluetooth_audio = (bits & SV_BT) != 0;
    c->out.dac_unmute = (bits & (SV_HP | SV_LINE)) != 0;
    /* SEND/RETURN share PORT_ENABLE. It is not per-jack or galvanic isolation. */
    c->out.port_enable = bits != 0;
    if (!usb || i->usb_suspended || !i->usb_authorization_valid || !i->physical_usb_valid) return;
    /* Limit total input, not just the battery's charging current. */
    if (SV27_NORMAL_CHARGE_RELEASED && i->usb_configured && i->usb_budget_ma >= SV27_SOURCE_GRANT_MA) {
        c->out.chg_en1 = false;
        c->out.chg_en2 = true;
    }
    /* R502=1.50k: 995..1153mA modeled input clamp. Require an actual >=1500mA grant. */
    uint32_t total = (uint32_t)i->board_usb_budget_ma + c->config.charge_current_worst_ma + c->config.charge_overhead_ma;
    c->out.charge_allow = SV27_NORMAL_CHARGE_RELEASED && config_valid(&c->config) && i->usb_configured &&
        i->usb_budget_ma >= SV27_SOURCE_GRANT_MA && i->board_budget_valid && total <= SV27_DELIVERY_BUDGET_MA &&
        i->battery_present && i->battery_measurement_valid && i->battery_mv >= 3000 &&
        (uint32_t)i->battery_mv + c->config.battery_error_bound_mv < c->config.pack_safety_max_mv &&
        i->temperature_valid && i->temperature_deci_c >= c->config.charge_min_deci_c &&
        i->temperature_deci_c <= c->config.charge_max_deci_c;
}
void sv_init(sv_control *c, uint32_t now, const sv_config *cfg) {
    memset(c, 0, sizeof(*c));
    c->state = SV_BOOT;
    c->boot_at = c->last_tick = c->state_at = now;
    c->gain_deci_db = -600;
    if (cfg) c->config = *cfg;
    safe_outputs(c);
}
void sv_stop_local(sv_control *c, uint32_t now) {
    if (c->state == SV_OFF || c->state == SV_STOPPING) return;
    c->state = SV_STOPPING;
    c->state_at = now;
    c->requested_routes = 0;
    c->pair_open = false;
    safe_outputs(c);
}
void sv_tick(sv_control *c, uint32_t now, const sv_inputs *in) {
    /* OFF is terminal even when a late callback supplies invalid input. */
    if (c->state == SV_OFF) { safe_outputs(c); return; }
    if (!in) { trip(c, SV_F_INPUT, now); return; }
    c->input = *in;
    if (c->state == SV_OFF) { safe_outputs(c); return; }
    uint32_t dt = elapsed(now, c->last_tick);
    c->last_tick = now;
    if (in->power_interrupt) sv_stop_local(c, now);
    if (in->usb_suspended) sv_stop_local(c, now);
    if (c->state == SV_STOPPING) {
        if (elapsed(now,c->state_at) >= 50) c->state = SV_OFF;
        safe_outputs(c);
        return;
    }
    if (dt > 100) { trip(c, SV_F_TIMING, now); return; }
    uint32_t faults = 0;
    if (in->external_fault || in->cc_fault || in->usb_data_fault) faults |= SV_F_PORT;
    if (in->charger_fault) faults |= SV_F_CHARGER;
    if (config_valid(&c->config) && in->battery_measurement_valid &&
        (uint32_t)in->battery_mv + c->config.battery_error_bound_mv >= c->config.pack_safety_max_mv)
        faults |= SV_F_CHARGER;
    if (c->state == SV_READY && !in->power_good) faults |= SV_F_POWER;
    if (c->state == SV_READY && (!in->clocks_good || !in->codec_ready || !in->startup_selftest_passed)) faults |= SV_F_CLOCK;
    if (faults) { trip(c, faults, now); return; }
    /* Cancel private/speaker routes at the first edge, before contact debounce. */
    if (c->hp.raw != in->headphones_raw) c->requested_routes &= (uint8_t)~(SV_HP | SV_SPK);
    if (!in->bluetooth_authenticated) c->requested_routes &= (uint8_t)~SV_BT;
    debounce(&c->hp, in->headphones_raw, now);
    debounce(&c->bt, in->bt_button_raw, now);
    if (c->state == SV_BOOT) {
        if (elapsed(now,c->boot_at) >= 3000) { trip(c,SV_F_BOOT,now); return; }
        if (healthy(in)) { c->state=SV_READY; c->state_at=now; }
    }
    if (c->state == SV_FAULT) {
        if (!healthy(in)) c->healthy_tracking=false;
        else if (!c->healthy_tracking) { c->healthy_tracking=true; c->healthy_at=now; }
    }
    if (!running(c) || !c->bt.stable) {
        c->bt_tracking=false;
        if (!c->bt.stable) c->bt_consumed=false;
    } else if (!c->bt_consumed) {
        if (!c->bt_tracking) { c->bt_tracking=true; c->bt_at=now; }
        if (elapsed(now,c->bt_at) >= 1500) {
            c->pair_open=true; c->pair_used=false; c->pair_at=now; c->bt_consumed=true;
        }
    }
    if (c->pair_open && elapsed(now,c->pair_at) >= 60000) c->pair_open=false;
    update_outputs(c);
}
bool sv_set_routes(sv_control *c, uint8_t routes) {
    if (routes > 15 || (routes && !running(c))) return false;
    if ((routes & SV_HP) && (!c->hp.stable || !c->input.headphones_raw)) return false;
    if ((routes & SV_HP) && elapsed(c->last_tick,c->hp.changed)<50) return false;
    if ((routes & SV_SPK) && (c->hp.stable || c->input.headphones_raw || !c->input.speaker_calibrated)) return false;
    if ((routes & SV_BT) && !c->input.bluetooth_authenticated) return false;
    c->requested_routes=routes;
    bool charge_was_allowed=c->out.charge_allow;
    update_outputs(c);
    c->out.charge_allow = c->out.charge_allow && charge_was_allowed;
    return true;
}
bool sv_ack_fault_local(sv_control *c, uint32_t now) {
    if (c->state != SV_FAULT || !c->healthy_tracking || !healthy(&c->input) ||
        elapsed(now,c->healthy_at)<100 || elapsed(now,c->last_tick)>100 ||
        (c->faults & (SV_F_TIMING|SV_F_BOOT|SV_F_INPUT|SV_F_CHARGER))) return false;
    c->faults=0; c->state=SV_READY; c->requested_routes=0;
    update_outputs(c);
    c->out.charge_allow=false;
    return true;
}
bool sv_take_pair_window(sv_control *c, uint32_t now) {
    if (!running(c) || !c->pair_open || c->pair_used || elapsed(now,c->pair_at)>=60000 ||
        elapsed(now,c->last_tick)>100) return false;
    c->pair_used=true;
    c->pair_open=false;
    return true;
}

uint16_t sv_crc16(const uint8_t *bytes, size_t length) {
    uint16_t crc=0xffff;
    for (size_t n=0;n<length;n++) {
        crc^=(uint16_t)bytes[n]<<8;
        for(unsigned j=0;j<8;j++) crc=(uint16_t)((crc<<1)^((crc&0x8000)?0x1021:0));
    }
    return crc;
}
void sv_parser_reset(sv_parser *p) { memset(p,0,sizeof(*p)); }
void sv_parser_poll(sv_parser *p, uint32_t now) {
    if (p->count && elapsed(now,p->started_at)>=250) { p->count=0; p->errors++; }
}
static uint16_t le16(const uint8_t *b) { return (uint16_t)(b[0]|((uint16_t)b[1]<<8)); }
static uint32_t le32(const uint8_t *b) {
    return (uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);
}
size_t sv_frame_encode(const sv_frame *f, uint8_t *out, size_t capacity) {
    if (!f || !out || f->length>256 || capacity<(size_t)f->length+14) return 0;
    out[0]=0x53;out[1]=0x56;out[2]=3;out[3]=f->type;
    out[4]=(uint8_t)f->seq;out[5]=(uint8_t)(f->seq>>8);
    for(unsigned j=0;j<4;j++)out[6+j]=(uint8_t)(f->session_id>>(8*j));
    out[10]=(uint8_t)f->length;out[11]=(uint8_t)(f->length>>8);
    memcpy(out+12,f->payload,f->length);
    uint16_t crc=sv_crc16(out+2,(size_t)f->length+10);
    out[f->length+12]=(uint8_t)crc;out[f->length+13]=(uint8_t)(crc>>8);
    return (size_t)f->length+14;
}
/* R4 FW-PARSER-WHITELIST: every frame type actually used on the MCU<->ESP link
 * (legacy 1..6, telemetry 0x20..0x22, factory 0x30..0x3C, radio 0x40..0x43,
 * ESP replies 0xA0/0xA1, MCU result 0xB0, 0x80). CRC+length still gate frames;
 * the dispatcher decides what a type means. */
bool sv_frame_type_known(uint8_t t) {
    return (t>=1 && t<=6) || (t>=0x20 && t<=0x22) || (t>=0x30 && t<=0x3c) ||
        (t>=0x40 && t<=0x43) || t==0x80 || t==0xa0 || t==0xa1 || t==0xb0;
}
static void discard(sv_parser *p, uint16_t n) {
    p->count=(uint16_t)(p->count-n);
    memmove(p->bytes,p->bytes+n,p->count);
}
bool sv_parser_byte(sv_parser *p, uint8_t byte, uint32_t now, sv_frame *out) {
    if (!p || !out) return false;
    sv_parser_poll(p,now);
    if (!p->count) p->started_at=now;
    if (p->count==sizeof(p->bytes)) { p->count=0; p->errors++; p->started_at=now; }
    p->bytes[p->count++]=byte;
    while (p->count>=2) {
        const uint8_t *b=p->bytes;
        if (b[0]!=0x53 || b[1]!=0x56) { discard(p,1); continue; }
        if (p->count<12) return false;
        uint16_t n=le16(b+10);
        if (b[2]!=3 || !sv_frame_type_known(b[3]) || n>256) {p->errors++;discard(p,1);continue;}
        uint16_t total=(uint16_t)(n+14);
        if (p->count<total) return false;
        if (sv_crc16(b+2,(size_t)n+10)!=le16(b+total-2)) {p->errors++;discard(p,1);continue;}
        out->type=b[3]; out->seq=le16(b+4); out->length=n;
        out->session_id=le32(b+6);
        memcpy(out->payload,b+12,n);
        discard(p,total);
        return true;
    }
    return false;
}
bool sv_session_begin_trusted(sv_session *s, uint32_t id) {
    if (!s || s->authorized || id==0) return false;
    s->authorized=true; s->session_id=id; s->have_seq=false; s->last_seq=0;
    return true;
}
void sv_session_end(sv_session *s) { memset(s,0,sizeof(*s)); }
sv_result sv_execute(sv_control *c, sv_session *s, const sv_frame *f, uint32_t now) {
    if (!s || !s->authorized) return SV_AUTH;
    if (!c || !f || f->type<1 || f->type>6 || f->length>256) return SV_FRAME;
    if (f->session_id!=s->session_id) return SV_AUTH;
    if (elapsed(now,c->last_tick)>100) return SV_NOT_READY;
    uint16_t distance=(uint16_t)(f->seq-s->last_seq);
    if(s->have_seq && (distance==0 || distance>=32768)) return SV_REPLAY;
    switch(f->type) {
    case 1: {
        if(f->length!=2) return SV_LENGTH;
        int32_t value=(int32_t)le16(f->payload);
        if(value>=32768) value-=65536;
        if(value < -600 || value>0) return SV_RANGE;
        c->gain_deci_db=(int16_t)value;
        break;
    }
    case 2: case 5: {
        if(f->length!=1) return SV_LENGTH;
        if(f->payload[0]>(f->type==2?3:15)) return SV_RANGE;
        static const uint8_t legacy[]={0,SV_HP,SV_LINE,SV_SPK};
        uint8_t routes=f->type==2?legacy[f->payload[0]]:f->payload[0];
        if(!sv_set_routes(c,routes)) return SV_NOT_READY;
        break;
    }
    case 3:
        if(f->length) return SV_LENGTH;
        if(!sv_take_pair_window(c,now)) return SV_PHYSICAL;
        break;
    case 6:
        if(f->length) return SV_LENGTH;
        c->requested_routes &= (uint8_t)~SV_BT;
        c->out.bluetooth_audio=false;
        c->out.active_routes &= (uint8_t)~SV_BT;
        break;
    default:
        if(f->length) return SV_LENGTH;
        break;
    }
    s->last_seq=f->seq; s->have_seq=true;
    return SV_OK;
}
