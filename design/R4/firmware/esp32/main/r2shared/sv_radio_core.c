#include "sv_radio_core.h"
#include <string.h>
void sv_radio_init(sv_radio_core *r){memset(r,0,sizeof(*r));}
bool sv_radio_open_local(sv_radio_core *r,const uint8_t peer[6],bool power,bool physical,uint32_t now){
    sv_radio_quiesce(r);
    if(!peer || !power || !physical || r->faults)return false;
    unsigned any=0,all_ff=1;
    for(unsigned j=0;j<6;j++){any|=peer[j];all_ff&=peer[j]==255;}
    if(!any || all_ff)return false;
    memcpy(r->peer,peer,6);r->opened_at=now;r->local_window=true;return true;
}
bool sv_radio_window(const sv_radio_core *r,uint32_t now){
    return r->local_window && !r->faults && now-r->opened_at<60000;
}
bool sv_radio_peer(const sv_radio_core *r,const uint8_t peer[6]){
    return peer && r->local_window && !memcmp(r->peer,peer,6);
}
void sv_radio_quiesce(sv_radio_core *r){
    r->local_window=false;r->connected=false;r->classic_authenticated=false;r->encrypted=false;
    memset(r->peer,0,sizeof(r->peer));
}
void sv_radio_tick(sv_radio_core *r,uint32_t now){
    if(r->local_window && !sv_radio_window(r,now))sv_radio_quiesce(r);
}
sv_result sv_radio_command(sv_radio_core *r,const sv_frame *f,uint32_t now){
    sv_radio_tick(r,now);
    if(f->type!=0x20 && f->type!=0x21)return SV_AUTH;
    if(f->length)return SV_LENGTH;
    if(f->type==0x21)sv_radio_quiesce(r);
    return SV_OK;
}
int32_t sv_radio_silence(uint8_t *out,int32_t length){
    if(length==-1)return 0;
    if(!out || length<=0 || length>4096 || length%4)return 0;
    memset(out,0,(size_t)length);return length;
}
