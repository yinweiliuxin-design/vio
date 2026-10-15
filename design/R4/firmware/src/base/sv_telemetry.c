#include "sv_telemetry.h"
#include "sv27_power_profile.h"
#include "sv_hw_rev.h"
#include <string.h>

enum { INIT, ADC_START, ADC_WAIT, TEMP_WAIT, IDLE, FAILED };
static uint32_t age(uint32_t a, uint32_t b) { return a-b; }
uint32_t sv_mon_divider_x1000(unsigned ch) {
    return ch==SV_MON_ISET?1000u:ch==SV_MON_USB?(uint32_t)SV_MON_DIV_USB_X1000:(uint32_t)SV_MON_DIV_PACK_X1000;
}
static void fail(sv_monitor *m, uint32_t f) {
    m->fault |= f; m->frame.valid=false; m->stage=FAILED;
}
static bool rd(sv_monitor *m, uint8_t addr, uint8_t reg, uint16_t *v) {
    uint8_t b[2];
    if (!m->bus.read || !m->bus.read(m->bus.ctx,addr,reg,b,2,2)) {
        fail(m,SV_MON_BUS); return false;
    }
    *v=(uint16_t)(((uint16_t)b[0]<<8)|b[1]); return true;
}
static bool wr(sv_monitor *m, uint8_t addr, uint8_t reg, uint16_t v) {
    uint8_t b[2]={(uint8_t)(v>>8),(uint8_t)v};
    if (!m->bus.write || !m->bus.write(m->bus.ctx,addr,reg,b,2,2)) {
        fail(m,SV_MON_BUS); return false;
    }
    return true;
}
static int32_t signed_word(uint16_t v) {
    return (v&0x8000u)?(int32_t)v-65536:(int32_t)v;
}
static bool calibration_valid(const sv_mon_cal *c) {
    for (unsigned n=0;n<SV_MON_CHANNELS;n++)
        if(c->gain_ppm[n]<980000 || c->gain_ppm[n]>1020000 ||
           c->offset_mv[n]<-50 || c->offset_mv[n]>50) return false;
    return true;
}
void sv_mon_init(sv_monitor *m, uint32_t now, sv_mon_bus b, const sv_mon_cal *c) {
    memset(m,0,sizeof(*m)); m->bus=b; m->last_tick=now; m->stage_at=now;
    for(unsigned n=0;n<SV_MON_CHANNELS;n++)m->cal.gain_ppm[n]=1000000;
    if(c)m->cal=*c;
    if(!calibration_valid(&m->cal))fail(m,SV_MON_CONFIG);
}
void sv_mon_tick(sv_monitor *m, uint32_t now, bool settled) {
    uint16_t v; uint32_t dt=age(now,m->last_tick); m->last_tick=now;
    if(m->fault)return;
    if(dt>100){fail(m,SV_MON_TIMING);return;}
    if(!settled){
        if(m->initialized)fail(m,SV_MON_TIMING);
        else if(age(now,m->stage_at)>1000)fail(m,SV_MON_TIMEOUT);
        return;
    }
    switch(m->stage){
    case INIT:
        if(!rd(m,0x49,0x0f,&v))return;
        if((v&0x0fff)!=0x0117){fail(m,SV_MON_ID);return;}
        if(!rd(m,0x49,4,&v))return;
        if(v&0xc000){fail(m,SV_MON_CONFIG);return;}
        /* TMP117: continuous, 250ms cycle, no averaging, no EEPROM writes. */
        if(!wr(m,0x49,1,0x0100))return;
        m->initialized=true; m->stage=ADC_START; m->channel=0; m->frame_at=now;
        break;
    case ADC_START:
        /* Single ended, +/-4.096V, single shot, 128SPS, comparator disabled. */
        if(!wr(m,0x48,1,(uint16_t)(0xc383u+((uint16_t)m->channel<<12))))return;
        m->stage=ADC_WAIT; m->stage_at=now;
        break;
    case ADC_WAIT:
        if(age(now,m->stage_at)>30){fail(m,SV_MON_TIMEOUT);return;}
        if(age(now,m->stage_at)<10)return;
        if(!rd(m,0x48,1,&v))return;
        if((v&0x7fff)!=(uint16_t)(0x4383u+((uint16_t)m->channel<<12))){fail(m,SV_MON_CONFIG);return;}
        if(!(v&0x8000))return;
        if(!rd(m,0x48,0,&v))return;
        {
            int32_t raw=signed_word(v);
            if(raw < -16 || raw > 21000){fail(m,SV_MON_RANGE);return;}
            if(raw<0)raw=0;
            /* AIN0 USB 2.65 divider; AIN1 PACK / AIN2 SYS divider per board (R4 E-02: 2.687);
             * AIN3 is the undivided buffered ISET. LSB 125 uV: uv = raw*ratio_x1000/8. */
            int64_t factor=sv_mon_divider_x1000(m->channel);
            int64_t uv=((int64_t)raw*factor*m->cal.gain_ppm[m->channel]+4000000)/8000000;
            int64_t mv=(uv+500)/1000+m->cal.offset_mv[m->channel];
            if(mv < -10 || mv > 6500){fail(m,SV_MON_RANGE);return;}
            m->pending_mv[m->channel]=(uint16_t)(mv<0?0:mv);
        }
        if(++m->channel==SV_MON_CHANNELS)m->stage=TEMP_WAIT;
        else m->stage=ADC_START;
        break;
    case TEMP_WAIT:
        if(age(now,m->frame_at)>400){fail(m,SV_MON_TIMEOUT);return;}
        if(!rd(m,0x49,1,&v))return;
        if((v&0x0fff)!=0x0100 || (v&0x1000)){fail(m,SV_MON_CONFIG);return;}
        if(!(v&0x2000))return;
        if(!rd(m,0x49,0,&v))return;
        {
            int32_t raw=signed_word(v);
            if(raw < -5120 || raw > 10880){fail(m,SV_MON_RANGE);return;}
            int32_t deci=(raw*10+(raw<0?-64:64))/128;
            memcpy(m->frame.mv,m->pending_mv,sizeof(m->pending_mv));
            m->frame.temperature_deci_c=(int16_t)deci;
        }
        m->frame.started_at=m->frame_at; m->frame.completed_at=now;
        m->frame.generation++; m->frame.valid=true; m->published_at=now; m->stage=IDLE;
        break;
    case IDLE:
        if(age(now,m->published_at)>=200){m->channel=0; m->frame_at=now; m->stage=ADC_START;}
        break;
    default: fail(m,SV_MON_CONFIG); break;
    }
}
bool sv_mon_snapshot(const sv_monitor *m, uint32_t now, sv_mon_frame *out) {
    if(out)memset(out,0,sizeof(*out));
    if(!out || m->fault || !m->frame.valid || age(now,m->frame.started_at)>750 ||
       age(now,m->last_tick)>100)return false;
    *out=m->frame; return true;
}
bool sv_mon_charge_current(const sv_mon_frame *f, bool charging, uint16_t *ma) {
    if(ma)*ma=0;
    if(!f || !ma || !f->valid || !charging || f->mv[SV_MON_ISET]>2500)return false;
    /* Profile-bound diagnostic estimate; not an ITERM comparator or safety measurement. */
    uint64_t denominator=(uint64_t)SV27_RISET_OHM*SV27_MONITOR_OHM;
    uint64_t numerator=(uint64_t)f->mv[SV_MON_ISET]*400u*(SV27_RISET_OHM+SV27_MONITOR_OHM);
    *ma=(uint16_t)((numerator+denominator/2u)/denominator);
    return true;
}
void sv_mon_apply(const sv_monitor *m, uint32_t now, sv_inputs *i) {
    sv_mon_frame f;
    i->usb_measurement_valid=false; i->temperature_valid=false; i->battery_measurement_valid=false;
    i->usb_mv=0; i->battery_mv=0; i->temperature_deci_c=0;
    if(!sv_mon_snapshot(m,now,&f))return;
    i->usb_mv=f.mv[SV_MON_USB]; i->battery_mv=f.mv[SV_MON_BAT];
    i->temperature_deci_c=f.temperature_deci_c;
    bool rails=i->v3d_measurement_valid && i->v3d_mv>=3100 && i->v3d_mv<=3450 &&
               f.mv[SV_MON_SYS]>=2900 && f.mv[SV_MON_SYS]<=4600;
    i->usb_measurement_valid=rails && m->cal.electrical_calibration_approved;
    i->battery_measurement_valid=i->usb_measurement_valid;
    i->temperature_valid=i->usb_measurement_valid && m->cal.thermal_attachment_approved;
    /* Never infer battery presence, a USB current grant or factory approval here. */
}
void sv_guard_init(sv_charge_guard *g){memset(g,0,sizeof(*g));g->locked=true;}
void sv_power_status_apply(sv_inputs *i, bool valid, bool pgood_n, bool efuse_fault_n) {
    if(!valid || (i->usb_present && pgood_n))i->usb_measurement_valid=false;
    if(!valid)i->board_budget_valid=false;
    if(valid && !efuse_fault_n)i->external_fault=true;
}
void sv_guard_apply(sv_charge_guard *g, sv_control *c, uint32_t now, bool attached) {
    bool gap=g->have_tick && age(now,g->last_tick)>100;
    g->last_tick=now;g->have_tick=true;
    if(!c->input.physical_usb_valid){g->locked=true;g->started=false;g->qualifying=false;g->absent_tracking=false;c->out.charge_allow=false;return;}
    if(gap){g->locked=true;g->started=false;g->qualifying=false;g->absent_tracking=false;c->out.charge_allow=false;return;}
    if(!attached){
        if(!g->absent_tracking){g->absent_tracking=true;g->absent_at=now;}
        if(age(now,g->absent_at)>=1000){g->locked=false;g->started=false;}
        g->qualifying=false; c->out.charge_allow=false; return;
    }
    g->absent_tracking=false;
    bool eligible=c->out.charge_allow;
    if(g->started && !eligible)g->locked=true;
    if(!eligible || g->locked){g->qualifying=false;c->out.charge_allow=false;return;}
    if(!g->qualifying){g->qualifying=true;g->qualified_at=now;}
    if(age(now,g->qualified_at)<2000){c->out.charge_allow=false;return;}
    g->started=true;
}
