#ifndef SV_PAIR_H
#define SV_PAIR_H
/* R4 first-time headset pairing. Pure state machine (no ESP-IDF calls) so it
 * is host-testable like sv_retry.h; smartvio_rf.c performs the Bluedroid calls.
 *
 * Trigger: the existing MCU 0x36 -> ESP 0x40 request (no new frame types).
 *   payload 6 x 00 or length 0 : AUTO - page the peer stored in NVS first
 *                                 (2 attempts), then inquire for a new sink.
 *   payload 6 x FF             : NEW  - skip the stored peer, inquire at once.
 *   any other 6-byte address   : EXPLICIT - R3 behaviour, unchanged.
 * Everything happens inside ONE 60 s window that starts at the 0x40. */
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
enum {SV_PAIR_KIND_EXPLICIT,SV_PAIR_KIND_AUTO,SV_PAIR_KIND_NEW,SV_PAIR_KIND_BAD};
enum {SV_PAIR_OFF,SV_PAIR_STORED,SV_PAIR_INQUIRY,SV_PAIR_NEW,SV_PAIR_DONE};
enum {SV_PAIR_NONE,SV_PAIR_DO_CONNECT,SV_PAIR_DO_INQUIRY,SV_PAIR_DO_STOP};
enum {
    SV_PAIR_WINDOW_MS=60000,     /* same 60 s as sv_radio_window() */
    SV_PAIR_INQ_UNITS=8,         /* x 1.28 s = 10.24 s general inquiry */
    SV_PAIR_INQ_GUARD_MS=13000,  /* inquiry never reported STOPPED: give up on it */
    SV_PAIR_INQ_MIN_LEFT_MS=20000, /* start an inquiry only if inquiry + a connect still fit */
    SV_PAIR_ATTEMPTS=2           /* page attempts per target before (re)inquiring */
};
typedef struct {uint8_t addr[6];int8_t rssi;bool valid,has_rssi;} sv_pair_cand;
typedef struct {
    uint8_t phase,inquiries;
    uint8_t target[6];
    uint32_t started,inq_at;
    bool inq_seen,inq_done;
} sv_pair;

static inline bool sv_pair_valid_addr(const uint8_t a[6]){
    unsigned any=0,all=1;for(unsigned i=0;i<6;i++){any|=a[i];all&=a[i]==255;}
    return any && !all;
}
static inline unsigned sv_pair_kind(const uint8_t *p,uint16_t length){
    if(length==0)return SV_PAIR_KIND_AUTO;
    if(length!=6 || !p)return SV_PAIR_KIND_BAD;
    unsigned any=0,all=1;for(unsigned i=0;i<6;i++){any|=p[i];all&=p[i]==255;}
    return !any?SV_PAIR_KIND_AUTO:all?SV_PAIR_KIND_NEW:SV_PAIR_KIND_EXPLICIT;
}
/* Class of Device filter for A2DP sinks: format type 0, major class
 * Audio/Video (4), minor = wearable headset 1, hands-free 2, loudspeaker 5,
 * headphones 6, portable audio 7, car audio 8, HiFi 10; or an uncategorised
 * A/V minor (0) that advertises the Rendering (bit 18) or Audio (bit 21) service. */
static inline bool sv_pair_is_sink(uint32_t cod){
    if(cod&3u)return false;
    if(((cod>>8)&0x1fu)!=4u)return false;
    unsigned minor=(cod>>2)&0x3fu;
    if(minor==1||minor==2||minor==5||minor==6||minor==7||minor==8||minor==10)return true;
    return minor==0 && (cod&((1u<<18)|(1u<<21)));
}
/* Keep the strongest RSSI; a result without RSSI only wins over nothing; ties keep the first. */
static inline bool sv_pair_offer(sv_pair_cand *c,const uint8_t a[6],bool has_rssi,int8_t rssi){
    if(!c || !a || !sv_pair_valid_addr(a))return false;
    if(c->valid && !memcmp(c->addr,a,6)){ /* same device again: keep its best reading */
        if(has_rssi && (!c->has_rssi || rssi>c->rssi)){c->rssi=rssi;c->has_rssi=true;}
        return false;
    }
    if(c->valid && (!has_rssi || (c->has_rssi && rssi<=c->rssi)))return false;
    memcpy(c->addr,a,6);c->rssi=has_rssi?rssi:-128;c->has_rssi=has_rssi;c->valid=true;return true;
}
static inline unsigned sv_pair_start_inquiry(sv_pair *p,uint32_t now){
    p->phase=SV_PAIR_INQUIRY;p->inq_at=now;p->inq_seen=false;p->inq_done=false;p->inquiries++;
    return SV_PAIR_DO_INQUIRY;
}
static inline unsigned sv_pair_begin(sv_pair *p,uint32_t now,const uint8_t *stored,bool force_new){
    memset(p,0,sizeof(*p));p->started=now;
    if(stored && !force_new && sv_pair_valid_addr(stored)){
        p->phase=SV_PAIR_STORED;memcpy(p->target,stored,6);return SV_PAIR_DO_CONNECT;
    }
    return sv_pair_start_inquiry(p,now);
}
/* Bluedroid DISC_STATE_CHANGED. A STOPPED counts only after this inquiry's
 * STARTED, so a late STOPPED from a cancelled earlier inquiry is ignored. */
static inline void sv_pair_disc_event(sv_pair *p,bool started){
    if(p->phase!=SV_PAIR_INQUIRY)return;
    if(started)p->inq_seen=true;else if(p->inq_seen)p->inq_done=true;
}
static inline bool sv_pair_left(const sv_pair *p,uint32_t now){
    return now-p->started<=SV_PAIR_WINDOW_MS-SV_PAIR_INQ_MIN_LEFT_MS;
}
/* link_failed: SV_PAIR_ATTEMPTS pages to target are over and nothing is in flight.
 * found: snapshot of the best sink seen by the current inquiry. */
static inline unsigned sv_pair_poll(sv_pair *p,uint32_t now,bool link_failed,bool connected,const sv_pair_cand *found){
    /* DONE: pairing logic finished; the radio window / MCU session govern from here. */
    if(p->phase==SV_PAIR_OFF || p->phase==SV_PAIR_DONE)return SV_PAIR_NONE;
    if(now-p->started>=SV_PAIR_WINDOW_MS){p->phase=SV_PAIR_OFF;return SV_PAIR_DO_STOP;}
    if(p->phase==SV_PAIR_STORED || p->phase==SV_PAIR_NEW){
        if(connected){p->phase=SV_PAIR_DONE;return SV_PAIR_NONE;}
        if(!link_failed)return SV_PAIR_NONE;
        if(sv_pair_left(p,now))return sv_pair_start_inquiry(p,now);
        p->phase=SV_PAIR_DONE;return SV_PAIR_NONE; /* sv_retry keeps its remaining attempts */
    }
    /* SV_PAIR_INQUIRY */
    if(!p->inq_done && now-p->inq_at<SV_PAIR_INQ_GUARD_MS)return SV_PAIR_NONE;
    if(found && found->valid){p->phase=SV_PAIR_NEW;memcpy(p->target,found->addr,6);return SV_PAIR_DO_CONNECT;}
    if(sv_pair_left(p,now))return sv_pair_start_inquiry(p,now);
    p->phase=SV_PAIR_OFF;return SV_PAIR_DO_STOP; /* nothing found and no time for another inquiry */
}
#endif
