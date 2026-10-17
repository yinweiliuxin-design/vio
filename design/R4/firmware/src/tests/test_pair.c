/* R4 ESP32 first-time pairing: host test of esp32/main/sv_pair.h together with the
 * real sv_retry.h and r2shared/sv_radio_core.c. The "glue" below mirrors
 * smartvio_rf.c pair_action()/process() (Bluedroid replaced by a scripted model:
 * page timeout 5.12 s -> DISCONNECTED, inquiry 10.24 s -> STOPPED). */
#include "sv_pair.h"
#include "sv_retry.h"
#include "sv_radio_core.h"
#include <stdio.h>
#include <stdlib.h>
static unsigned assertions;
#define CHECK(x) do{assertions++;if(!(x)){fprintf(stderr,"FAIL pair %d\n",__LINE__);exit(1);}}while(0)

/* reference CoD decode written from the Bluetooth Assigned Numbers, independent of sv_pair.h */
static int ref_sink(uint32_t cod){
    int format=cod&3,major=(cod>>8)&31,minor=(cod>>2)&63,service=(cod>>13)&0x7ff;
    if(format||major!=4)return 0;
    switch(minor){case 1:case 2:case 5:case 6:case 7:case 8:case 10:return 1;
    case 0:return (service&(0x20|0x100))!=0; default:return 0;}
}
/* ---- model of smartvio_rf.c glue ---- */
typedef struct {
    sv_radio_core radio;sv_retry retry;sv_pair pair;sv_pair_cand found;
    bool collecting,inquiry_running,quiesced;uint32_t inq_started,page_started;bool paging;
    uint8_t stored[6];bool have_stored;
    const uint8_t *present;     /* device that answers pages (NULL: none) */
    const uint8_t *discoverable;int8_t rssi; /* device found by inquiry */
    unsigned inquiries,connects,stops;
} model;
static void m_quiesce(model *m){sv_radio_quiesce(&m->radio);memset(&m->pair,0,sizeof(m->pair));m->collecting=false;
    sv_retry_stop(&m->retry,0);m->retry.draining=false;m->inquiry_running=false;m->quiesced=true;}
static void m_action(model *m,unsigned a,uint32_t now){
    if(a==SV_PAIR_DO_STOP){m->stops++;m_quiesce(m);return;}
    if(a==SV_PAIR_DO_INQUIRY){sv_radio_quiesce(&m->radio);sv_retry_stop(&m->retry,now);
        memset(&m->found,0,sizeof(m->found));m->collecting=true;m->inquiry_running=true;m->inq_started=now;m->inquiries++;
        sv_pair_disc_event(&m->pair,true);}
    else if(a==SV_PAIR_DO_CONNECT){m->collecting=false;m->inquiry_running=false;
        CHECK(sv_radio_open_local(&m->radio,m->pair.target,true,true,now));
        CHECK(sv_retry_open(&m->retry,m->pair.target,now));m->radio.opened_at=m->pair.started;}
}
static unsigned m_begin(model *m,const uint8_t req[6],uint16_t len,uint32_t now){
    m_quiesce(m);m->quiesced=false;unsigned k=sv_pair_kind(req,len);
    if(k==SV_PAIR_KIND_EXPLICIT||k==SV_PAIR_KIND_BAD)return k;
    m_action(m,sv_pair_begin(&m->pair,now,m->have_stored?m->stored:NULL,k==SV_PAIR_KIND_NEW),now);return k;
}
static void m_step(model *m,uint32_t now){
    /* scripted Bluedroid */
    if(m->inquiry_running && now-m->inq_started>=10240){
        if(m->discoverable && m->collecting)sv_pair_offer(&m->found,m->discoverable,true,m->rssi);
        m->inquiry_running=false;sv_pair_disc_event(&m->pair,false);}
    if(m->paging){
        bool ok=m->present && !memcmp(m->present,m->retry.peer,6);
        if(ok && now-m->page_started>=700){m->paging=false;
            if(sv_retry_connected(&m->retry,m->retry.peer,sv_radio_window(&m->radio,now),now))m->radio.connected=true;}
        else if(!ok && now-m->page_started>=5120){m->paging=false;sv_retry_disconnected(&m->retry,m->retry.peer,now);}
    }
    if(m->retry.draining && !m->paging)sv_retry_disconnected(&m->retry,m->retry.peer,now);
    /* process() tail */
    if(m->pair.phase){bool failed=m->retry.attempts>=SV_PAIR_ATTEMPTS && !m->retry.inflight && !m->retry.connected && !m->retry.draining && !m->radio.connected;
        m_action(m,sv_pair_poll(&m->pair,now,failed,m->radio.connected,&m->found),now);}
    if(m->radio.connected && sv_radio_window(&m->radio,now)){m->radio.opened_at=now;
        if(!m->have_stored||memcmp(m->stored,m->radio.peer,6)){memcpy(m->stored,m->radio.peer,6);m->have_stored=true;}}
    if(m->radio.local_window && !sv_radio_window(&m->radio,now))m_quiesce(m);
    unsigned r=sv_retry_poll(&m->retry,sv_radio_window(&m->radio,now),true,now);
    if(r==SV_RETRY_CONNECT){m->paging=true;m->page_started=now;m->connects++;}
    else if(r==SV_RETRY_ABORT){CHECK(0);} /* model always reports DISCONNECTED in time */
}
static uint32_t run(model *m,uint32_t from,uint32_t to,bool stop_on_connect){
    for(uint32_t t=from;t!=to;t+=5){m_step(m,t);if(stop_on_connect && m->radio.connected)return t;}
    return to;
}
int main(void){
    const uint8_t zero[6]={0},ff[6]={255,255,255,255,255,255},hs[6]={0x11,0x22,0x33,0x44,0x55,0x66},
        old[6]={0xa0,1,2,3,4,5},other[6]={0x11,0x22,0x33,0x44,0x55,0x67};
    /* kind */
    CHECK(sv_pair_kind(zero,0)==SV_PAIR_KIND_AUTO);CHECK(sv_pair_kind(NULL,0)==SV_PAIR_KIND_AUTO);
    CHECK(sv_pair_kind(zero,6)==SV_PAIR_KIND_AUTO);CHECK(sv_pair_kind(ff,6)==SV_PAIR_KIND_NEW);
    CHECK(sv_pair_kind(hs,6)==SV_PAIR_KIND_EXPLICIT);
    for(uint16_t n=1;n<300;n++)if(n!=6)CHECK(sv_pair_kind(hs,n)==SV_PAIR_KIND_BAD);
    CHECK(!sv_pair_valid_addr(zero)&&!sv_pair_valid_addr(ff)&&sv_pair_valid_addr(hs));
    /* CoD: exhaustive against the reference, plus known real-world values */
    for(uint32_t cod=0;cod<(1u<<24);cod++)CHECK(sv_pair_is_sink(cod)==ref_sink(cod));
    CHECK(sv_pair_is_sink(0x240404));CHECK(sv_pair_is_sink(0x240418));CHECK(sv_pair_is_sink(0x200414));
    CHECK(sv_pair_is_sink(0x04041c)); /* portable audio */
    CHECK(!sv_pair_is_sink(0x5a020c));/* smartphone */
    CHECK(!sv_pair_is_sink(0x240410));/* microphone */
    CHECK(!sv_pair_is_sink(0x000400));CHECK(sv_pair_is_sink(0x040400));
    CHECK(!sv_pair_is_sink(0x240405));/* format type != 0 */
    /* candidate selection */
    sv_pair_cand c={0};
    CHECK(!sv_pair_offer(&c,zero,true,-20));CHECK(!c.valid);
    CHECK(sv_pair_offer(&c,old,false,0));CHECK(c.valid&&!c.has_rssi&&c.rssi==-128);
    CHECK(!sv_pair_offer(&c,hs,false,0));            /* no RSSI does not replace the first */
    CHECK(sv_pair_offer(&c,hs,true,-80));CHECK(!memcmp(c.addr,hs,6));
    CHECK(!sv_pair_offer(&c,other,true,-80));        /* tie keeps the first */
    CHECK(sv_pair_offer(&c,other,true,-60));CHECK(!memcmp(c.addr,other,6));
    CHECK(!sv_pair_offer(&c,hs,true,-70));CHECK(!sv_pair_offer(&c,other,true,-50));CHECK(c.rssi==-50);
    CHECK(!sv_pair_offer(&c,hs,true,-50));CHECK(sv_pair_offer(&c,hs,true,-49));
    /* stale STOPPED from a cancelled inquiry is ignored */
    sv_pair p;CHECK(sv_pair_begin(&p,0,NULL,false)==SV_PAIR_DO_INQUIRY);
    sv_pair_disc_event(&p,false);CHECK(!p.inq_done);sv_pair_disc_event(&p,true);sv_pair_disc_event(&p,false);CHECK(p.inq_done);
    /* inquiry that never reports STOPPED: guard */
    CHECK(sv_pair_begin(&p,100,NULL,false)==SV_PAIR_DO_INQUIRY);
    CHECK(sv_pair_poll(&p,100+SV_PAIR_INQ_GUARD_MS-1,false,false,NULL)==SV_PAIR_NONE);
    CHECK(sv_pair_poll(&p,100+SV_PAIR_INQ_GUARD_MS,false,false,NULL)==SV_PAIR_DO_INQUIRY&&p.inquiries==2);
    /* explicit / bad requests do not start pairing */
    CHECK(sv_pair_begin(&p,0,old,true)==SV_PAIR_DO_INQUIRY);   /* NEW ignores the stored peer */
    CHECK(sv_pair_begin(&p,0,ff,false)==SV_PAIR_DO_INQUIRY);   /* corrupt stored value ignored */
    CHECK(sv_pair_poll(&(sv_pair){0},5,true,false,NULL)==SV_PAIR_NONE);

    for(unsigned wrap=0;wrap<2;wrap++){
        uint32_t t0=wrap?UINT32_MAX-30000:1000;model m;
        /* A: stored headset present -> first page connects, no inquiry, stays up past 60 s */
        memset(&m,0,sizeof(m));memcpy(m.stored,old,6);m.have_stored=true;m.present=old;
        CHECK(m_begin(&m,zero,6,t0)==SV_PAIR_KIND_AUTO&&m.pair.phase==SV_PAIR_STORED&&m.radio.local_window);
        uint32_t tc=run(&m,t0,t0+20000,true);CHECK(m.radio.connected&&tc-t0<1000&&m.inquiries==0&&m.connects==1);
        run(&m,tc,t0+180000,false);CHECK(m.radio.connected&&m.radio.local_window&&m.pair.phase==SV_PAIR_DONE&&!m.quiesced);
        /* B: stored headset absent, new one discoverable -> 2 pages, inquiry, connect, NVS updated */
        memset(&m,0,sizeof(m));memcpy(m.stored,old,6);m.have_stored=true;m.present=hs;m.discoverable=hs;m.rssi=-55;
        m_begin(&m,zero,6,t0);tc=run(&m,t0,t0+60000,true);
        CHECK(m.radio.connected&&!memcmp(m.radio.peer,hs,6)&&m.inquiries==1&&m.connects==3);
        CHECK(tc-t0>2*5120 && tc-t0<2*5120+500+10240+1500);
        run(&m,tc,tc+5,false);CHECK(m.have_stored&&!memcmp(m.stored,hs,6));
        /* C: nothing anywhere, no stored peer -> 4 inquiries then stop before the 60 s window */
        memset(&m,0,sizeof(m));m_begin(&m,NULL,0,t0);run(&m,t0,t0+70000,false);
        CHECK(m.inquiries==4&&m.stops==1&&m.connects==0&&!m.radio.local_window&&m.pair.phase==SV_PAIR_OFF);
        /* D: FF = pair new even if the stored headset would answer */
        memset(&m,0,sizeof(m));memcpy(m.stored,old,6);m.have_stored=true;m.present=hs;m.discoverable=hs;
        m_begin(&m,ff,6,t0);CHECK(m.pair.phase==SV_PAIR_INQUIRY&&m.inquiries==1);
        tc=run(&m,t0,t0+60000,true);CHECK(m.radio.connected&&!memcmp(m.radio.peer,hs,6)&&tc-t0<10240+1500);
        /* E: found device never accepts the page -> pages within the one 60 s window, then off */
        memset(&m,0,sizeof(m));m.discoverable=hs;m_begin(&m,zero,6,t0);run(&m,t0,t0+61000,false);
        CHECK(!m.radio.connected&&!m.radio.local_window&&m.quiesced&&m.inquiries>=2&&m.connects>=2&&m.connects<=6);
        /* F: window measured from the 0x40, not from the inquiry result */
        memset(&m,0,sizeof(m));m.discoverable=hs;m_begin(&m,zero,6,t0);run(&m,t0,t0+10300,false);
        CHECK(m.radio.local_window&&m.radio.opened_at==t0&&sv_radio_window(&m.radio,t0+59999)&&!sv_radio_window(&m.radio,t0+60000));
    }
    printf("test_pair: %u assertions\n",assertions);
    return 0;
}
