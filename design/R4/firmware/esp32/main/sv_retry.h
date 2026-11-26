#ifndef SV_RETRY_H
#define SV_RETRY_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
enum {SV_RETRY_NONE,SV_RETRY_CONNECT,SV_RETRY_DISCONNECT,SV_RETRY_ABORT};
enum {SV_RETRY_MAX_ATTEMPTS=4,SV_RETRY_CONNECT_MS=5000,SV_RETRY_DRAIN_MS=2000};
typedef struct {
    uint8_t peer[6];
    bool enabled,inflight,connected,draining,blocked;
    uint32_t attempts,due,started,drain_at;
} sv_retry;
static inline bool sv_retry_peer(const sv_retry *r,const uint8_t p[6]){return p && !memcmp(r->peer,p,6);}
static inline bool sv_retry_idle(const sv_retry *r){return !r->inflight && !r->connected && !r->draining && !r->blocked;}
static inline bool sv_retry_open(sv_retry *r,const uint8_t p[6],uint32_t now){
    if(!p || !sv_retry_idle(r))return false;
    unsigned any=0,all=1;for(unsigned i=0;i<6;i++){any|=p[i];all&=p[i]==255;}
    if(!any || all)return false;
    memset(r,0,sizeof(*r));memcpy(r->peer,p,6);r->enabled=true;r->due=now;return true;
}
static inline bool sv_retry_stop(sv_retry *r,uint32_t now){
    bool active=r->inflight || r->connected || r->draining;
    r->enabled=false;r->inflight=false;r->connected=false;
    if(active && !r->draining){r->draining=true;r->drain_at=now;}
    return active;
}
static inline bool sv_retry_close_connection(sv_retry *r,uint32_t now){
    if(r->draining || (!r->inflight && !r->connected))return false;
    r->inflight=false;r->connected=false;r->draining=true;r->drain_at=now;return true;
}
static inline void sv_retry_schedule(sv_retry *r,uint32_t now){
    if(r->attempts>=SV_RETRY_MAX_ATTEMPTS){r->enabled=false;return;}
    unsigned shift=r->attempts?r->attempts-1:0;
    r->due=now+(500u<<shift);
}
static inline void sv_retry_failed(sv_retry *r,uint32_t now){
    if(!r->inflight)return;
    r->inflight=false;if(r->enabled)sv_retry_schedule(r,now);
}
static inline bool sv_retry_disconnected(sv_retry *r,const uint8_t p[6],uint32_t now){
    if(!sv_retry_peer(r,p))return false;
    bool active=r->inflight || r->connected || r->draining;
    r->inflight=r->connected=r->draining=false;
    if(active && r->enabled)sv_retry_schedule(r,now);
    return active;
}
static inline bool sv_retry_connected(sv_retry *r,const uint8_t p[6],bool grant,uint32_t now){
    if(!sv_retry_peer(r,p))return false;
    if(!grant || !r->enabled || r->draining || r->blocked || (!r->inflight && !r->connected)){
        sv_retry_stop(r,now);
        if(!r->draining){r->draining=true;r->drain_at=now;}
        return false;
    }
    r->inflight=false;r->connected=true;return true;
}
static inline bool sv_retry_resume(sv_retry *r,bool grant,uint32_t now){
    /* Manual resume cannot bypass an in-progress disconnect or reset the cap. */
    if(!grant || !sv_retry_idle(r) || r->enabled || !r->attempts || r->attempts>=SV_RETRY_MAX_ATTEMPTS)return false;
    r->enabled=true;sv_retry_schedule(r,now);return true;
}
static inline unsigned sv_retry_poll(sv_retry *r,bool grant,bool profile_ready,uint32_t now){
    if(!grant && r->enabled){if(sv_retry_stop(r,now))return SV_RETRY_DISCONNECT;}
    if(r->draining){
        if(now-r->drain_at>=SV_RETRY_DRAIN_MS){r->blocked=true;r->enabled=false;r->draining=false;return SV_RETRY_ABORT;}
        return SV_RETRY_NONE;
    }
    if(!grant || !r->enabled || r->blocked)return SV_RETRY_NONE;
    if(r->inflight){
        if(now-r->started>=SV_RETRY_CONNECT_MS){r->inflight=false;r->draining=true;r->drain_at=now;return SV_RETRY_DISCONNECT;}
        return SV_RETRY_NONE;
    }
    if(r->connected || !profile_ready || (int32_t)(now-r->due)<0 || r->attempts>=SV_RETRY_MAX_ATTEMPTS)return SV_RETRY_NONE;
    r->attempts++;r->inflight=true;r->started=now;return SV_RETRY_CONNECT;
}
#endif
