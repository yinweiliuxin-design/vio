/* Isolated V27 native diagnostics. Execution on hardware has not been tested.
 * R4: first-time headset pairing (inquiry for A2DP sinks on a 0x40 with an
 * all-zero/absent or all-FF peer), bonded peer kept in NVS, Bluetooth stack
 * started at boot with a bounded deferred 0x40 reply, streaming window kept
 * open while the link is up and the MCU session is alive. Not hardware-tested. */
#include <string.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "esp_task_wdt.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_bt_api.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_a2dp_api.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "pcm_rx.h"
#include "sv_radio_core.h"
#include "sv_retry.h"
#include "sv_pair.h"

enum {EV_LOCAL,EV_PROFILE,EV_A2DP,EV_AUTH,EV_ENCRYPT,EV_CONFIRM,EV_PIN,
      EV_GATT_TABLE,EV_BLE_CONNECT,EV_BLE_DISCONNECT,EV_READ,EV_WRITE,EV_ADV,EV_MEDIA,EV_BLE_AUTH,EV_DISC};
typedef struct {
    uint8_t type,peer[6],value;bool ok,need_response,prepared;
    uint16_t connection,handle,offset,interface;uint32_t transaction,issued_at;
} event;
static QueueHandle_t events,uart_events;
static sv_radio_core radio;
static sv_parser parser;
static bool stack_ready,adv_ready,advertising,ble_connected;
static bool media_check_requested;
static bool pcm_ready,ble_authenticated;
static sv_retry retry;
static sv_session mcu_session;
static uint32_t mcu_at;
static uint16_t ble_connection,value_handle;
static esp_gatt_if_t gatt_interface;
static uint32_t queue_overflows;
static uint8_t tx[270];static size_t tx_length,tx_at;static uint32_t tx_started;
/* R4 pairing state. found is written by the Bluedroid GAP callback (BTC task)
 * under found_lock while collecting; everything else is app_main-only. */
static sv_pair pair;
static sv_pair_cand found;static bool collecting;
static portMUX_TYPE found_lock=portMUX_INITIALIZER_UNLOCKED;
static uint8_t stored_peer[6];static bool have_stored,saved;
/* R4 early start: init_task publishes init_state once (release); app_main reads (acquire). */
enum {SV_INIT_STACK=1,SV_INIT_PCM=2,SV_INIT_DONE=0x80,SV_INIT_REPLY_MS=1200 /* < MCU 1500 ms reply timeout */};
static uint8_t init_state;static bool init_seen;
static sv_frame deferred;static bool deferred_valid;static uint32_t deferred_at;
static uint32_t now_ms(void){return (uint32_t)(esp_timer_get_time()/1000);}
static TickType_t ticks_ms(unsigned ms){return (TickType_t)(((uint64_t)ms*configTICK_RATE_HZ+999)/1000);}
static void post(event *e){if(!events || xQueueSend(events,e,0)!=pdTRUE)__atomic_fetch_add(&queue_overflows,1,__ATOMIC_RELAXED);}
/* Local test adapter; native MCU UART dispatch below issues the same event. */
bool sv_esp_factory_pair(const uint8_t peer[6],bool power_qualified,bool physical_window){
    if(!stack_ready || !peer || !power_qualified || !physical_window)return false;
    event e={.type=EV_LOCAL,.ok=true,.issued_at=now_ms()};memcpy(e.peer,peer,6);
    return xQueueSend(events,&e,0)==pdTRUE;
}
static void status_bytes(uint8_t out[8]){
    out[0]=1;out[1]=stack_ready;out[2]=radio.profile_ready;out[3]=radio.connected;
    out[4]=radio.classic_authenticated;out[5]=radio.encrypted;out[6]=pcm_ready;out[7]=radio.faults?1:0;
}
static void collect(bool on){
    portENTER_CRITICAL(&found_lock);if(on)memset(&found,0,sizeof(found));collecting=on;portEXIT_CRITICAL(&found_lock);
}
static void quiesce(void){
    uint8_t peer[6];memcpy(peer,radio.peer,6);bool had_peer=radio.local_window;
    bool inquiring=pair.phase==SV_PAIR_INQUIRY;memset(&pair,0,sizeof(pair));collect(false);
    saved=false;deferred_valid=false;
    sv_radio_quiesce(&radio);sv_parser_reset(&parser);
    sv_retry_stop(&retry,now_ms());
    media_check_requested=false;ble_authenticated=false;sv_esp_pcm_gate(false);sv_session_end(&mcu_session);
    if(!stack_ready)return;
    esp_bt_gap_set_scan_mode(ESP_BT_NON_CONNECTABLE,ESP_BT_NON_DISCOVERABLE);
    if(inquiring)esp_bt_gap_cancel_discovery();
    if(advertising){esp_ble_gap_stop_advertising();advertising=false;}
    if(had_peer && radio.profile_ready){esp_a2d_media_ctrl(ESP_A2D_MEDIA_CTRL_SUSPEND);esp_a2d_source_disconnect(peer);}
    if(ble_connected)esp_ble_gatts_close(gatt_interface,ble_connection);
}
static int32_t pcm_callback(uint8_t *out,int32_t n){
    if(!out || n<=0 || n>4096 || n%4)return 0;
    return sv_esp_pcm_read(out,n);
}
static void a2dp_callback(esp_a2d_cb_event_t kind,esp_a2d_cb_param_t *p){
    event e={0};
    if(kind==ESP_A2D_PROF_STATE_EVT){e.type=EV_PROFILE;e.ok=p->a2d_prof_stat.init_state==ESP_A2D_INIT_SUCCESS;}
    else if(kind==ESP_A2D_CONNECTION_STATE_EVT){e.type=EV_A2DP;e.value=(uint8_t)p->conn_stat.state;e.ok=p->conn_stat.state==ESP_A2D_CONNECTION_STATE_CONNECTED;memcpy(e.peer,p->conn_stat.remote_bda,6);}
    else if(kind==ESP_A2D_MEDIA_CTRL_ACK_EVT){e.type=EV_MEDIA;e.ok=p->media_ctrl_stat.status==ESP_A2D_MEDIA_CTRL_ACK_SUCCESS;e.value=(uint8_t)p->media_ctrl_stat.cmd;}
    else return;
    post(&e);
}
static void classic_callback(esp_bt_gap_cb_event_t kind,esp_bt_gap_cb_param_t *p){
    event e={0};
    if(kind==ESP_BT_GAP_AUTH_CMPL_EVT){e.type=EV_AUTH;e.ok=p->auth_cmpl.stat==ESP_BT_STATUS_SUCCESS;memcpy(e.peer,p->auth_cmpl.bda,6);}
    else if(kind==ESP_BT_GAP_ENC_CHG_EVT){e.type=EV_ENCRYPT;e.ok=p->enc_chg.enc_mode!=0;memcpy(e.peer,p->enc_chg.bda,6);}
    else if(kind==ESP_BT_GAP_CFM_REQ_EVT){e.type=EV_CONFIRM;memcpy(e.peer,p->cfm_req.bda,6);}
    else if(kind==ESP_BT_GAP_PIN_REQ_EVT){e.type=EV_PIN;e.value=p->pin_req.min_16_digit;memcpy(e.peer,p->pin_req.bda,6);}
    else if(kind==ESP_BT_GAP_DISC_RES_EVT){
        /* Filter in the callback: only A2DP-sink CoDs touch the shared best
         * candidate, so a crowded inquiry cannot overflow the event queue. */
        uint32_t cod=0;bool has_cod=false,has_rssi=false;int8_t rssi=0;
        for(int i=0;i<p->disc_res.num_prop;i++){
            const esp_bt_gap_dev_prop_t *q=&p->disc_res.prop[i];
            if(q->type==ESP_BT_GAP_DEV_PROP_COD && q->val && q->len>=4){memcpy(&cod,q->val,4);has_cod=true;}
            else if(q->type==ESP_BT_GAP_DEV_PROP_RSSI && q->val && q->len>=1){rssi=*(const int8_t*)q->val;has_rssi=true;}
        }
        if(has_cod && sv_pair_is_sink(cod)){
            portENTER_CRITICAL(&found_lock);if(collecting)sv_pair_offer(&found,p->disc_res.bda,has_rssi,rssi);portEXIT_CRITICAL(&found_lock);
        }
        return;
    }
    else if(kind==ESP_BT_GAP_DISC_STATE_CHANGED_EVT){e.type=EV_DISC;e.ok=p->disc_st_chg.state==ESP_BT_GAP_DISCOVERY_STARTED;}
    else return;
    post(&e);
}
static void ble_callback(esp_gap_ble_cb_event_t kind,esp_ble_gap_cb_param_t *p){
    if(kind==ESP_GAP_BLE_ADV_DATA_RAW_SET_COMPLETE_EVT){event e={.type=EV_ADV,.ok=p->adv_data_raw_cmpl.status==ESP_BT_STATUS_SUCCESS};post(&e);}
    /* JustWorks factory pairing only during the MCU-issued physical window;
     * this does not provide MITM protection and is not production security. */
    else if(kind==ESP_GAP_BLE_SEC_REQ_EVT)esp_ble_gap_security_rsp(p->ble_security.ble_req.bd_addr,sv_radio_window(&radio,now_ms()));
    else if(kind==ESP_GAP_BLE_AUTH_CMPL_EVT){event e={.type=EV_BLE_AUTH,.ok=p->ble_security.auth_cmpl.success};post(&e);}
}
static const uint8_t uuid[16]={0x52,0x46,0x48,0x4f,0x4c,0x44,0x25,0x00,0xa1,0x37,0x88,0x50,0x00,0x00,0x56,0x53};
static uint16_t primary_uuid=ESP_GATT_UUID_PRI_SERVICE,declare_uuid=ESP_GATT_UUID_CHAR_DECLARE;
static uint8_t properties=ESP_GATT_CHAR_PROP_BIT_READ|ESP_GATT_CHAR_PROP_BIT_WRITE;
static uint8_t char_uuid[16]={0x52,0x46,0x48,0x4f,0x4c,0x44,0x25,0x00,0xa1,0x37,0x88,0x50,0x01,0x00,0x56,0x53};
static esp_gatts_attr_db_t attributes[3]={
    {{ESP_GATT_AUTO_RSP},{ESP_UUID_LEN_16,(uint8_t*)&primary_uuid,ESP_GATT_PERM_READ,16,16,(uint8_t*)uuid}},
    {{ESP_GATT_AUTO_RSP},{ESP_UUID_LEN_16,(uint8_t*)&declare_uuid,ESP_GATT_PERM_READ,1,1,&properties}},
    {{ESP_GATT_RSP_BY_APP},{ESP_UUID_LEN_128,char_uuid,ESP_GATT_PERM_READ_ENCRYPTED|ESP_GATT_PERM_WRITE_ENCRYPTED,8,0,NULL}}
};
static void gatt_callback(esp_gatts_cb_event_t kind,esp_gatt_if_t interface,esp_ble_gatts_cb_param_t *p){
    event e={.interface=interface};
    if(kind==ESP_GATTS_REG_EVT){
        if(p->reg.status!=ESP_GATT_OK)return;
        gatt_interface=interface;
        esp_ble_gatts_create_attr_tab(attributes,interface,3,0);return;
    }
    if(kind==ESP_GATTS_CREAT_ATTR_TAB_EVT){
        if(p->add_attr_tab.status!=ESP_GATT_OK || p->add_attr_tab.num_handle!=3)return;
        e.type=EV_GATT_TABLE;e.handle=p->add_attr_tab.handles[2];e.connection=p->add_attr_tab.handles[0];
    }else if(kind==ESP_GATTS_CONNECT_EVT){e.type=EV_BLE_CONNECT;e.connection=p->connect.conn_id;memcpy(e.peer,p->connect.remote_bda,6);}
    else if(kind==ESP_GATTS_DISCONNECT_EVT){e.type=EV_BLE_DISCONNECT;e.connection=p->disconnect.conn_id;}
    else if(kind==ESP_GATTS_READ_EVT){e.type=EV_READ;e.connection=p->read.conn_id;e.transaction=p->read.trans_id;e.handle=p->read.handle;e.offset=p->read.offset;e.need_response=p->read.need_rsp;}
    else if(kind==ESP_GATTS_WRITE_EVT){e.type=EV_WRITE;e.connection=p->write.conn_id;e.transaction=p->write.trans_id;e.handle=p->write.handle;e.offset=p->write.offset;e.need_response=p->write.need_rsp;e.prepared=p->write.is_prep;e.value=p->write.len==1?p->write.value[0]:255;}
    else if(kind==ESP_GATTS_EXEC_WRITE_EVT){esp_ble_gatts_send_response(interface,p->exec_write.conn_id,p->exec_write.trans_id,ESP_GATT_REQ_NOT_SUPPORTED,NULL);return;}
    else return;
    post(&e);
}
static bool radio_stack_init(void){
    /* Preserve bond storage: never erase NVS to recover an initialization error. */
    if(nvs_flash_init()!=ESP_OK)return false;
    esp_bt_controller_config_t config=BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    if(esp_bt_controller_init(&config)!=ESP_OK || esp_bt_controller_enable(ESP_BT_MODE_BTDM)!=ESP_OK ||
       esp_bluedroid_init()!=ESP_OK || esp_bluedroid_enable()!=ESP_OK)return false;
    if(esp_bt_gap_register_callback(classic_callback)!=ESP_OK || esp_ble_gap_register_callback(ble_callback)!=ESP_OK ||
       esp_ble_gatts_register_callback(gatt_callback)!=ESP_OK || esp_a2d_register_callback(a2dp_callback)!=ESP_OK ||
       esp_a2d_source_register_data_callback(pcm_callback)!=ESP_OK)return false;
    uint8_t io=ESP_BT_IO_CAP_NONE;
    if(esp_bt_gap_set_security_param(ESP_BT_SP_IOCAP_MODE,&io,sizeof(io))!=ESP_OK ||
       esp_bt_gap_set_scan_mode(ESP_BT_NON_CONNECTABLE,ESP_BT_NON_DISCOVERABLE)!=ESP_OK ||
       esp_ble_gatts_app_register(0)!=ESP_OK || esp_a2d_source_init()!=ESP_OK)return false;
    uint8_t ble_io=ESP_IO_CAP_NONE,auth=ESP_LE_AUTH_BOND,key_size=16;
    if(esp_ble_gap_set_security_param(ESP_BLE_SM_IOCAP_MODE,&ble_io,1)!=ESP_OK ||
       esp_ble_gap_set_security_param(ESP_BLE_SM_AUTHEN_REQ_MODE,&auth,1)!=ESP_OK ||
       esp_ble_gap_set_security_param(ESP_BLE_SM_MAX_KEY_SIZE,&key_size,1)!=ESP_OK)return false;
    uint8_t adv[30]={2,1,6,17,7};memcpy(adv+5,uuid,16);adv[21]=8;adv[22]=8;memcpy(adv+23,"SV-DIAG",7);
    return esp_ble_gap_config_adv_data_raw(adv,sizeof(adv))==ESP_OK;
}
/* Bonded headset address (Bluedroid keeps the link key itself in its own NVS
 * namespace). Written only when it changes, after an authenticated connect. */
static void load_peer(void){
    nvs_handle_t h;uint8_t p[6];size_t n=sizeof(p);
    if(nvs_open("sv_rf",NVS_READONLY,&h)!=ESP_OK)return;
    if(nvs_get_blob(h,"peer",p,&n)==ESP_OK && n==6 && sv_pair_valid_addr(p)){memcpy(stored_peer,p,6);have_stored=true;}
    nvs_close(h);
}
static void store_peer(const uint8_t p[6]){
    nvs_handle_t h;
    if(nvs_open("sv_rf",NVS_READWRITE,&h)!=ESP_OK)return;
    if(nvs_set_blob(h,"peer",p,6)==ESP_OK && nvs_commit(h)==ESP_OK){memcpy(stored_peer,p,6);have_stored=true;
        ESP_LOGI("SV_RF","stored peer %02x:%02x:%02x:%02x:%02x:%02x",p[0],p[1],p[2],p[3],p[4],p[5]);}
    nvs_close(h);
}
static void pair_cancel(void){
    if(pair.phase==SV_PAIR_INQUIRY && stack_ready)esp_bt_gap_cancel_discovery();
    collect(false);if(pair.phase)pair.phase=SV_PAIR_DONE;
}
static void pair_action(unsigned a,uint32_t now){
    if(a==SV_PAIR_DO_STOP){ESP_LOGI("SV_RF","pairing window over");quiesce();return;}
    if(a==SV_PAIR_DO_INQUIRY){
        /* Nothing is in flight here (fresh start, or SV_PAIR_ATTEMPTS pages over):
         * close the page window, keep the MCU session and the 60 s deadline. */
        sv_radio_quiesce(&radio);sv_retry_stop(&retry,now);
        media_check_requested=false;sv_esp_pcm_gate(false);collect(true);
        esp_err_t r=esp_bt_gap_start_discovery(ESP_BT_INQ_MODE_GENERAL_INQUIRY,SV_PAIR_INQ_UNITS,0);
        ESP_LOGI("SV_RF","inquiry %u start %d",pair.inquiries,(int)r); /* on error the inquiry guard moves on */
    }else if(a==SV_PAIR_DO_CONNECT){
        bool from_inquiry=pair.phase==SV_PAIR_NEW;
        collect(false);if(from_inquiry && !pair.inq_done)esp_bt_gap_cancel_discovery();
        if(!sv_radio_open_local(&radio,pair.target,true,true,now) || !sv_retry_open(&retry,pair.target,now)){quiesce();return;}
        radio.opened_at=pair.started; /* one 60 s window, counted from the MCU's 0x40 */
        saved=false;
        ESP_LOGI("SV_RF","%s peer %02x:%02x:%02x:%02x:%02x:%02x",from_inquiry?"found":"stored",
            pair.target[0],pair.target[1],pair.target[2],pair.target[3],pair.target[4],pair.target[5]);
    }
}
static void init_task(void *unused){
    (void)unused;uint8_t s=0;
    if(radio_stack_init()){s|=SV_INIT_STACK;load_peer();if(sv_esp_pcm_start())s|=SV_INIT_PCM;}
    __atomic_store_n(&init_state,(uint8_t)(s|SV_INIT_DONE),__ATOMIC_RELEASE);
    vTaskDelete(NULL);
}
static void process(event *e,uint32_t now){
    bool grant=sv_radio_window(&radio,now);
    switch(e->type){
    case EV_LOCAL:
        if(now-e->issued_at>100 || !sv_retry_idle(&retry))break;
        quiesce();
        if(sv_radio_open_local(&radio,e->peer,true,true,now) && !sv_retry_open(&retry,e->peer,now))quiesce();
        break;
    case EV_PROFILE:radio.profile_ready=e->ok;if(!e->ok)radio.faults|=2;break;
    case EV_A2DP:
        if(e->value==ESP_A2D_CONNECTION_STATE_CONNECTED){
            if(grant && sv_radio_peer(&radio,e->peer) && sv_retry_connected(&retry,e->peer,grant,now))radio.connected=true;
            else {sv_retry_connected(&retry,e->peer,false,now);esp_a2d_source_disconnect(e->peer);}
        }else if(e->value==ESP_A2D_CONNECTION_STATE_DISCONNECTED && sv_retry_peer(&retry,e->peer)){
            sv_retry_disconnected(&retry,e->peer,now);
            radio.connected=false;radio.classic_authenticated=false;radio.encrypted=false;
            media_check_requested=false;sv_esp_pcm_gate(false);
        }
        break;
    case EV_AUTH:
        if(grant && sv_radio_peer(&radio,e->peer) && retry.enabled && !retry.draining && (retry.inflight || retry.connected)){
            radio.classic_authenticated=e->ok;if(!e->ok)quiesce();
        }
        break;
    case EV_ENCRYPT:
        if(grant && sv_radio_peer(&radio,e->peer)){
            radio.encrypted=e->ok && retry.enabled && !retry.draining && (retry.inflight || retry.connected);
            if(!e->ok){
                /* Encryption-off accompanies ordinary link loss. Mute now,
                 * but await DISCONNECTED before the bounded retry. */
                radio.classic_authenticated=false;media_check_requested=false;sv_esp_pcm_gate(false);
                if(sv_retry_close_connection(&retry,now))esp_a2d_source_disconnect(retry.peer);
                radio.connected=false;
            }
        }
        break;
    case EV_CONFIRM:esp_bt_gap_ssp_confirm_reply(e->peer,grant && sv_radio_peer(&radio,e->peer));break;
    case EV_PIN:{
        /* R4: pre-2.1 (legacy PIN) headsets: fixed "0000", only for the windowed peer. */
        esp_bt_pin_code_t pin={'0','0','0','0'};bool ok=grant && !e->value && sv_radio_peer(&radio,e->peer);
        esp_bt_gap_pin_reply(e->peer,ok,ok?4:0,pin);break;}
    case EV_DISC:sv_pair_disc_event(&pair,e->ok);break;
    case EV_GATT_TABLE:value_handle=e->handle;esp_ble_gatts_start_service(e->connection);break;
    case EV_ADV:adv_ready=e->ok;break;
    case EV_MEDIA:
        if(e->value==ESP_A2D_MEDIA_CTRL_CHECK_SRC_RDY && e->ok && grant && radio.connected && radio.classic_authenticated && radio.encrypted)
            if(esp_a2d_media_ctrl(ESP_A2D_MEDIA_CTRL_START)!=ESP_OK){radio.faults|=16;quiesce();}
        break;
    case EV_BLE_CONNECT:
        if(ble_connected || !grant){esp_ble_gatts_close(e->interface,e->connection);break;}
        ble_connected=true;ble_connection=e->connection;
        advertising=false;ble_authenticated=false;
        if(esp_ble_set_encryption(e->peer,ESP_BLE_SEC_ENCRYPT)!=ESP_OK)esp_ble_gatts_close(e->interface,e->connection);
        break;
    case EV_BLE_AUTH:ble_authenticated=e->ok && grant;if(!ble_authenticated)quiesce();break;
    case EV_BLE_DISCONNECT:ble_connected=false;quiesce();break;
    case EV_READ:case EV_WRITE:{
        esp_gatt_status_t result=ESP_GATT_OK;esp_gatt_rsp_t response={0};
        response.attr_value.handle=e->handle;response.attr_value.offset=e->offset;
        if(e->handle!=value_handle)result=ESP_GATT_INVALID_HANDLE;
        else if(!ble_authenticated || !grant)result=ESP_GATT_INSUF_AUTHENTICATION;
        else if(e->offset || e->prepared)result=ESP_GATT_REQ_NOT_SUPPORTED;
        else if(e->type==EV_READ){response.attr_value.len=8;status_bytes(response.attr_value.value);}
        else if(e->value==0)quiesce();else result=ESP_GATT_INSUF_AUTHENTICATION;
        if(e->need_response)esp_ble_gatts_send_response(e->interface,e->connection,e->transaction,result,e->type==EV_READ?&response:NULL);
        break;}
    }
    if(pair.phase){
        sv_pair_cand snapshot;portENTER_CRITICAL(&found_lock);snapshot=found;portEXIT_CRITICAL(&found_lock);
        bool failed=retry.attempts>=SV_PAIR_ATTEMPTS && !retry.inflight && !retry.connected && !retry.draining && !radio.connected;
        pair_action(sv_pair_poll(&pair,now,failed,radio.connected,&snapshot),now);
    }
    if(!saved && radio.local_window && radio.connected && radio.classic_authenticated){
        saved=true;if(!have_stored || memcmp(stored_peer,radio.peer,6))store_peer(radio.peer);
    }
    /* R4: the 60 s window bounds pairing/connecting only. While the link is fully
     * up and the MCU keeps its session alive (0x41 every 1 s, 2 s timeout) the
     * window slides, so A2DP streaming is not cut 60 s after the 0x40. */
    if(radio.connected && radio.classic_authenticated && radio.encrypted && mcu_session.authorized && sv_radio_window(&radio,now))
        radio.opened_at=now;
    grant=sv_radio_window(&radio,now);
    unsigned retry_action=sv_retry_poll(&retry,grant,radio.profile_ready,now);
    if(retry_action==SV_RETRY_CONNECT){
        radio.connected=false;radio.classic_authenticated=false;radio.encrypted=false;media_check_requested=false;
        ESP_LOGI("SV_RF","known peer attempt %lu/%u",(unsigned long)retry.attempts,SV_RETRY_MAX_ATTEMPTS);
        if(esp_a2d_source_connect(retry.peer)!=ESP_OK)sv_retry_failed(&retry,now);
    }else if(retry_action==SV_RETRY_DISCONNECT){
        sv_esp_pcm_gate(false);radio.connected=false;radio.classic_authenticated=false;radio.encrypted=false;
        media_check_requested=false;esp_a2d_source_disconnect(retry.peer);
    }else if(retry_action==SV_RETRY_ABORT){radio.faults|=64;quiesce();}
    sv_esp_pcm_gate(grant && pcm_ready && radio.connected && radio.classic_authenticated && radio.encrypted);
    if(grant && radio.connected && radio.classic_authenticated && radio.encrypted && !media_check_requested){
        media_check_requested=esp_a2d_media_ctrl(ESP_A2D_MEDIA_CTRL_CHECK_SRC_RDY)==ESP_OK;
        if(!media_check_requested){radio.faults|=16;quiesce();}
    }
    if(stack_ready && grant && adv_ready && value_handle && !advertising && !ble_connected){
        esp_ble_adv_params_t params={.adv_int_min=0x40,.adv_int_max=0x80,.adv_type=ADV_TYPE_IND,
            .own_addr_type=BLE_ADDR_TYPE_PUBLIC,.channel_map=ADV_CHNL_ALL,.adv_filter_policy=ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY};
        if(esp_ble_gap_start_advertising(&params)==ESP_OK)advertising=true;
    }
}
static void uart_reply(const sv_frame *request,sv_result result){
    if(tx_length)return;
    sv_frame f={.type=0xA0,.seq=request->seq,.session_id=request->session_id,.length=9};
    f.payload[0]=(uint8_t)result;status_bytes(f.payload+1);
    if(request->type==0x22 && result==SV_OK){
        sv_esp_pcm_stats stats;sv_esp_pcm_snapshot(&stats);
        _Static_assert(sizeof(stats)==32,"fixed telemetry wire layout");
        f.type=0xa1;f.length=sizeof(stats);memcpy(f.payload,&stats,sizeof(stats));
    }
    tx_length=sv_frame_encode(&f,tx,sizeof(tx));tx_at=0;tx_started=now_ms();
}
/* 0x40: explicit peer = R3 path; zero/absent/FF peer = R4 pairing. */
static sv_result open_request(const sv_frame *f){
    quiesce();
    if(!stack_ready || !pcm_ready){radio.faults|=4;return SV_NOT_READY;}
    uint32_t now=now_ms();unsigned kind=sv_pair_kind(f->payload,f->length);
    if(kind==SV_PAIR_KIND_EXPLICIT){event local={.type=EV_LOCAL,.ok=true,.issued_at=now};memcpy(local.peer,f->payload,6);process(&local,now);}
    else pair_action(sv_pair_begin(&pair,now,have_stored?stored_peer:NULL,kind==SV_PAIR_KIND_NEW),now);
    sv_session_begin_trusted(&mcu_session,f->session_id);mcu_session.have_seq=true;mcu_session.last_seq=f->seq;mcu_at=now_ms();
    return radio.local_window || pair.phase==SV_PAIR_INQUIRY?SV_OK:SV_RANGE;
}
void app_main(void){
    sv_radio_init(&radio);sv_parser_reset(&parser);
    events=xQueueCreate(16,sizeof(event));if(!events)return;
    uart_config_t config={.baud_rate=115200,.data_bits=UART_DATA_8_BITS,.parity=UART_PARITY_DISABLE,
        .stop_bits=UART_STOP_BITS_1,.flow_ctrl=UART_HW_FLOWCTRL_DISABLE,.source_clk=UART_SCLK_APB};
    if(uart_param_config(UART_NUM_2,&config)!=ESP_OK || uart_set_pin(UART_NUM_2,33,32,UART_PIN_NO_CHANGE,UART_PIN_NO_CHANGE)!=ESP_OK ||
       uart_driver_install(UART_NUM_2,512,0,16,&uart_events,0)!=ESP_OK)return;
    /* R4: start the Bluetooth stack now (still non-connectable, non-discoverable,
     * no advertising until a grant) instead of inside the first 0x40, whose
     * reply could otherwise miss the MCU's 1.5 s timeout. */
    if(xTaskCreate(init_task,"sv_bt_init",4096,NULL,2,NULL)!=pdPASS)__atomic_store_n(&init_state,(uint8_t)SV_INIT_DONE,__ATOMIC_RELEASE);
    /* Additional delay after ROM/app startup; MCU owns physical30ms LOW/5ms HIGH. */
    vTaskDelay(ticks_ms(5));
    if(esp_task_wdt_add(NULL)!=ESP_OK){radio.faults|=32;return;}
    ESP_LOGI("SV_RF","DIAG: radio disabled until bounded MCU factory grant; hardware untested");
    for(;;){
        uint32_t now=now_ms();
        if(!init_seen){uint8_t s=__atomic_load_n(&init_state,__ATOMIC_ACQUIRE);
            if(s&SV_INIT_DONE){init_seen=true;stack_ready=(s&SV_INIT_STACK)!=0;pcm_ready=(s&SV_INIT_PCM)!=0;}}
        if(deferred_valid && (init_seen || now-deferred_at>=SV_INIT_REPLY_MS)){
            sv_frame d=deferred;deferred_valid=false;uart_reply(&d,init_seen?open_request(&d):SV_NOT_READY);
        }
        if(__atomic_exchange_n(&queue_overflows,0,__ATOMIC_RELAXED)){radio.faults|=8;quiesce();}
        if(radio.local_window && !sv_radio_window(&radio,now))quiesce();
        if(mcu_session.authorized && now-mcu_at>=2000)quiesce();
        event e;for(unsigned k=0;k<8 && xQueueReceive(events,&e,0)==pdTRUE;k++)process(&e,now);
        uart_event_t u;bool bad=false;
        for(unsigned k=0;k<16 && xQueueReceive(uart_events,&u,0)==pdTRUE;k++)if(u.type==UART_FIFO_OVF || u.type==UART_BUFFER_FULL || u.type==UART_FRAME_ERR || u.type==UART_PARITY_ERR || u.type==UART_BREAK)bad=true;
        if(bad){uart_flush_input(UART_NUM_2);xQueueReset(uart_events);tx_length=0;quiesce();}
        uint8_t bytes[128];int n=uart_read_bytes(UART_NUM_2,bytes,sizeof(bytes),0);
        for(int k=0;k<n;k++){
            sv_frame f;
            if(sv_parser_byte(&parser,bytes[k],now,&f)){
                if(f.type==0x80 || f.type==0xA0)continue;
                if(f.type==0x21 && !f.length)quiesce();
                sv_result result;
                if(f.type==0x22){result=f.length?SV_LENGTH:SV_OK;}
                else if(f.type==0x40 && !sv_retry_idle(&retry)){result=SV_NOT_READY;}
                else if(f.type==0x40 && sv_pair_kind(f.payload,f.length)!=SV_PAIR_KIND_BAD && f.session_id && !radio.faults){
                    /* Internal trusted-MCU link only; external UART access can
                     * bypass this diagnostic assumption, so never release. */
                    if(init_seen)result=open_request(&f);
                    else if(deferred_valid)result=SV_NOT_READY;
                    else {deferred=f;deferred_valid=true;deferred_at=now;continue;} /* reply when init ends, <=1.2 s */
                }else if(f.type==0x41 || f.type==0x42 || f.type==0x43){
                    uint16_t delta=(uint16_t)(f.seq-mcu_session.last_seq);
                    if(f.length)result=SV_LENGTH;
                    else if(!mcu_session.authorized || f.session_id!=mcu_session.session_id)result=SV_AUTH;
                    else if(!delta || delta>=32768)result=SV_REPLAY;
                    else {mcu_session.last_seq=f.seq;mcu_at=now;result=SV_OK;
                        if(f.type==0x42){
                            pair_cancel();
                            bool active=sv_retry_stop(&retry,now);sv_esp_pcm_gate(false);
                            radio.connected=false;radio.classic_authenticated=false;radio.encrypted=false;media_check_requested=false;
                            if(active)esp_a2d_source_disconnect(retry.peer);
                        }
                        if(f.type==0x43 && !sv_retry_resume(&retry,sv_radio_window(&radio,now),now))result=SV_NOT_READY;}
                }else result=sv_radio_command(&radio,&f,now);
                uart_reply(&f,result);
            }
        }
        sv_parser_poll(&parser,now);
        if(tx_length){
            int sent=uart_tx_chars(UART_NUM_2,(const char*)tx+tx_at,tx_length-tx_at);
            if(sent>0)tx_at+=(size_t)sent;
            if(tx_at==tx_length)tx_length=0;
            else if(now-tx_started>=250){tx_length=0;quiesce();}
        }
        event poll={.type=255};process(&poll,now_ms());
        esp_task_wdt_reset();vTaskDelay(ticks_ms(5));
    }
}
