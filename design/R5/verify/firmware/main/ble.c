/*
 * BLE GATT server (NimBLE, ESP-IDF built-in), modelled on the IDF example
 * examples/bluetooth/nimble/bleprph.
 *   Battery Service 0x180F / Battery Level 0x2A19 (read, notify) - fake value
 *   R5 service (128-bit):
 *     output mode  (read/write/notify) uint8: 0 hp, 1 spk, 2 bt, 3 spk+bt
 *     parameters   (read/write/notify) 4 x uint8: vol, tone, fx, mix (0..100)
 */
#include <stdio.h>
#include <string.h>
#include "sdkconfig.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "ble.h"
#include "params.h"

#if CONFIG_R5_BLE_ENABLE
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_uuid.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *TAG = "ble";
#define DEV_NAME "SmartVio-R5-bench"

/* 5a0e5000-7e4b-4c1e-9c2a-52355f425231 ("R5_BR1" in the tail) */
static const ble_uuid128_t k_svc_uuid = BLE_UUID128_INIT(
    0x31, 0x52, 0x42, 0x5f, 0x35, 0x52, 0x2a, 0x9c, 0x1e, 0x4c, 0x4b, 0x7e, 0x00, 0x50, 0x0e, 0x5a);
static const ble_uuid128_t k_out_uuid = BLE_UUID128_INIT(
    0x31, 0x52, 0x42, 0x5f, 0x35, 0x52, 0x2a, 0x9c, 0x1e, 0x4c, 0x4b, 0x7e, 0x01, 0x50, 0x0e, 0x5a);
static const ble_uuid128_t k_par_uuid = BLE_UUID128_INIT(
    0x31, 0x52, 0x42, 0x5f, 0x35, 0x52, 0x2a, 0x9c, 0x1e, 0x4c, 0x4b, 0x7e, 0x02, 0x50, 0x0e, 0x5a);

static uint16_t s_bat_h, s_out_h, s_par_h;
static uint8_t s_battery = 87;
static volatile bool s_synced;
static volatile int s_conns;
static uint8_t s_own_addr_type;
static esp_timer_handle_t s_bat_timer, s_notify_timer;

static void advertise(void);

static int chr_access(uint16_t conn, uint16_t attr, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    int which = (int)(intptr_t)arg;
    r5_params_t p;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        params_get(&p);
        if (which == 0) {
            return os_mbuf_append(ctxt->om, &s_battery, 1) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        } else if (which == 1) {
            uint8_t v = (uint8_t)p.out;
            return os_mbuf_append(ctxt->om, &v, 1) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        } else {
            uint8_t v[4] = {(uint8_t)p.vol_pct, (uint8_t)p.tone_pct, (uint8_t)p.fx_pct, (uint8_t)p.mix_pct};
            return os_mbuf_append(ctxt->om, v, 4) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        }
    }
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t buf[4];
        uint16_t len = 0;
        if (ble_hs_mbuf_to_flat(ctxt->om, buf, sizeof(buf), &len) != 0) return BLE_ATT_ERR_UNLIKELY;
        if (which == 1) {
            if (len != 1 || buf[0] > 3) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            r5_params_t *pp = params_lock();
            pp->out = (r5_out_t)buf[0];
            params_unlock(true);
            return 0;
        }
        if (which == 2) {
            if (len != 4) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            for (int i = 0; i < 4; i++) if (buf[i] > 100) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            r5_params_t *pp = params_lock();
            pp->vol_pct = buf[0];
            pp->wired_db = pp->spk_db = params_vol_db(buf[0]);
            params_set_tone_pct(pp, buf[1]);
            pp->fx_pct = buf[2];
            pp->mix_pct = buf[3];
            params_unlock(true);
            return 0;
        }
        return BLE_ATT_ERR_WRITE_NOT_PERMITTED;
    }
    return BLE_ATT_ERR_UNLIKELY;
}

static const struct ble_gatt_svc_def k_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(0x180F),
        .characteristics = (struct ble_gatt_chr_def[]){
            {
                .uuid = BLE_UUID16_DECLARE(0x2A19),
                .access_cb = chr_access,
                .arg = (void *)0,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &s_bat_h,
            },
            {0},
        },
    },
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &k_svc_uuid.u,
        .characteristics = (struct ble_gatt_chr_def[]){
            {
                .uuid = &k_out_uuid.u,
                .access_cb = chr_access,
                .arg = (void *)1,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &s_out_h,
            },
            {
                .uuid = &k_par_uuid.u,
                .access_cb = chr_access,
                .arg = (void *)2,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &s_par_h,
            },
            {0},
        },
    },
    {0},
};

static int gap_event(struct ble_gap_event *ev, void *arg)
{
    switch (ev->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (ev->connect.status == 0) {
            s_conns++;
            ESP_LOGI(TAG, "connected (handle %d)", ev->connect.conn_handle);
        } else {
            advertise();
        }
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        if (s_conns > 0) s_conns--;
        ESP_LOGI(TAG, "disconnected (reason 0x%x)", ev->disconnect.reason);
        advertise();
        break;
    case BLE_GAP_EVENT_ADV_COMPLETE:
        advertise();
        break;
    default:
        break;
    }
    return 0;
}

static void advertise(void)
{
    struct ble_hs_adv_fields f;
    memset(&f, 0, sizeof(f));
    f.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    f.name = (uint8_t *)DEV_NAME;
    f.name_len = strlen(DEV_NAME);
    f.name_is_complete = 1;
    static ble_uuid16_t bas = BLE_UUID16_INIT(0x180F);
    f.uuids16 = &bas;
    f.num_uuids16 = 1;
    f.uuids16_is_complete = 0;
    int rc = ble_gap_adv_set_fields(&f);
    if (rc) {
        ESP_LOGE(TAG, "adv fields rc=%d", rc);
        return;
    }
    struct ble_gap_adv_params ap;
    memset(&ap, 0, sizeof(ap));
    ap.conn_mode = BLE_GAP_CONN_MODE_UND;
    ap.disc_mode = BLE_GAP_DISC_MODE_GEN;
    rc = ble_gap_adv_start(s_own_addr_type, NULL, BLE_HS_FOREVER, &ap, gap_event, NULL);
    if (rc && rc != BLE_HS_EALREADY) ESP_LOGE(TAG, "adv start rc=%d", rc);
}

static void on_sync(void)
{
    ble_hs_id_infer_auto(0, &s_own_addr_type);
    s_synced = true;
    advertise();
    ESP_LOGI(TAG, "advertising as %s", DEV_NAME);
}

static void on_reset(int reason)
{
    s_synced = false;
    ESP_LOGW(TAG, "host reset, reason %d", reason);
}

static void host_task(void *param)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
}

/* runs in the esp_timer task: no params lock held, so no lock-order issue
 * between the params mutex and the NimBLE host lock */
static void notify_tick(void *arg)
{
    if (!s_synced) return;
    ble_gatts_chr_updated(s_out_h);
    ble_gatts_chr_updated(s_par_h);
}

static void bat_tick(void *arg)
{
    s_battery = (s_battery <= 20) ? 100 : (uint8_t)(s_battery - 1);   /* fake */
    if (s_synced) ble_gatts_chr_updated(s_bat_h);
}

esp_err_t ble_start(void)
{
    esp_err_t e = nimble_port_init();
    if (e != ESP_OK) {
        ESP_LOGE(TAG, "nimble_port_init: %s", esp_err_to_name(e));
        return e;
    }
    ble_hs_cfg.sync_cb = on_sync;
    ble_hs_cfg.reset_cb = on_reset;
    ble_svc_gap_init();
    ble_svc_gatt_init();
    int rc = ble_gatts_count_cfg(k_svcs);
    if (rc == 0) rc = ble_gatts_add_svcs(k_svcs);
    if (rc) {
        ESP_LOGE(TAG, "gatt cfg rc=%d", rc);
        return ESP_FAIL;
    }
    ble_svc_gap_device_name_set(DEV_NAME);
    nimble_port_freertos_init(host_task);

    const esp_timer_create_args_t ta = {.callback = bat_tick, .name = "bat"};
    esp_timer_create(&ta, &s_bat_timer);
    const esp_timer_create_args_t tn = {.callback = notify_tick, .name = "blentf"};
    esp_timer_create(&tn, &s_notify_timer);
    esp_timer_start_periodic(s_bat_timer, 60ULL * 1000 * 1000);
    return ESP_OK;
}

void ble_params_changed(void)
{
    /* debounce: one notification 50 ms after the last change */
    if (!s_synced || !s_notify_timer) return;
    esp_timer_stop(s_notify_timer);
    esp_timer_start_once(s_notify_timer, 50 * 1000);
}

void ble_status_print(void)
{
    uint8_t addr[6] = {0};
    ble_hs_id_copy_addr(s_own_addr_type, addr, NULL);
    printf("BLE: %s, name %s, addr %02x:%02x:%02x:%02x:%02x:%02x, connections %d, battery %u%% (fake)\n",
           s_synced ? "advertising/connected" : "not synced", DEV_NAME, addr[5], addr[4], addr[3],
           addr[2], addr[1], addr[0], s_conns, s_battery);
}

#else  /* !CONFIG_R5_BLE_ENABLE */
esp_err_t ble_start(void) { return ESP_OK; }
void ble_params_changed(void) {}
void ble_status_print(void) { printf("BLE disabled in menuconfig\n"); }
#endif
