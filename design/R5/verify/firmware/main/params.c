#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "nvs.h"
#include "sdkconfig.h"
#include "params.h"
#include "codec.h"
#include "audio.h"
#include "ble.h"

static const char *TAG = "params";
static r5_params_t s_p;
static SemaphoreHandle_t s_mtx;

#define NVS_VER 1
typedef struct {
    uint32_t ver;
    float spk_w, spk_ohm, spk_vfs, mix_cal_db, pga[2], pickup_gain_db;
} persist_t;

float params_vol_db(int pct)
{
    if (pct <= 0) return -200.0f;
    if (pct > 100) pct = 100;
    return -40.0f + 0.4f * (float)pct;
}

void params_set_tone_pct(r5_params_t *p, int pct)
{
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    p->tone_pct = pct;
    float tilt = (float)(pct - 50) / 50.0f * 9.0f;   /* +/-9 dB tilt */
    p->treble_db = tilt;
    p->bass_db = -tilt;
}

const char *params_out_name(r5_out_t o)
{
    switch (o) {
    case R5_OUT_HP: return "hp";
    case R5_OUT_SPK: return "spk";
    case R5_OUT_BT: return "bt";
    case R5_OUT_SPK_BT: return "spk+bt";
    }
    return "?";
}

static void spk_sd_init(void)
{
#if CONFIG_R5_PIN_SPK_SD >= 0
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << CONFIG_R5_PIN_SPK_SD,
        .mode = GPIO_MODE_OUTPUT_OD,          /* never drive high: keep the board's */
        .pull_up_en = GPIO_PULLUP_DISABLE,    /* SD_MODE divider for (L+R)/2 */
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    gpio_config(&io);
    gpio_set_level(CONFIG_R5_PIN_SPK_SD, 0);
#endif
}

static void spk_sd_set(bool on)
{
#if CONFIG_R5_PIN_SPK_SD >= 0
    gpio_set_level(CONFIG_R5_PIN_SPK_SD, on ? 1 : 0);   /* 1 = released (high-Z) */
#else
    (void)on;
#endif
}

void params_init(void)
{
    s_mtx = xSemaphoreCreateRecursiveMutex();
    memset(&s_p, 0, sizeof(s_p));
    s_p.vol_pct = 85;
    s_p.wired_db = s_p.spk_db = params_vol_db(s_p.vol_pct);
    s_p.mix_pct = 50;
    s_p.pga_db[0] = 12.0f;     /* pickup: set with `level` */
    s_p.pga_db[1] = 0.0f;      /* AUX line level */
    s_p.pickup_gain_db = 0.0f;
    params_set_tone_pct(&s_p, 50);
    s_p.fx_pct = 30;
    s_p.fx_on = true;
    s_p.out = R5_OUT_SPK;
    s_p.spk_limit_w = CONFIG_R5_SPK_LIMIT_MW / 1000.0f;
    s_p.spk_ohm = (float)CONFIG_R5_SPK_OHMS;
    s_p.spk_vrms_fs = CONFIG_R5_SPK_VRMS_FS_MV / 1000.0f;
    s_p.spk_limit_on = true;

    nvs_handle_t h;
    if (nvs_open("r5", NVS_READONLY, &h) == ESP_OK) {
        persist_t ps;
        size_t len = sizeof(ps);
        if (nvs_get_blob(h, "cal", &ps, &len) == ESP_OK && len == sizeof(ps) && ps.ver == NVS_VER) {
            s_p.spk_limit_w = ps.spk_w;
            s_p.spk_ohm = ps.spk_ohm;
            s_p.spk_vrms_fs = ps.spk_vfs;
            s_p.mix_cal_db = ps.mix_cal_db;
            s_p.pga_db[0] = ps.pga[0];
            s_p.pga_db[1] = ps.pga[1];
            s_p.pickup_gain_db = ps.pickup_gain_db;
            ESP_LOGI(TAG, "calibration loaded from NVS");
        }
        nvs_close(h);
    }
    s_p.pga_real_db[0] = s_p.pga_db[0];
    s_p.pga_real_db[1] = s_p.pga_db[1];
    spk_sd_init();
}

esp_err_t params_save(void)
{
    persist_t ps = {
        .ver = NVS_VER,
        .spk_w = s_p.spk_limit_w, .spk_ohm = s_p.spk_ohm, .spk_vfs = s_p.spk_vrms_fs,
        .mix_cal_db = s_p.mix_cal_db, .pga = {s_p.pga_db[0], s_p.pga_db[1]},
        .pickup_gain_db = s_p.pickup_gain_db,
    };
    nvs_handle_t h;
    esp_err_t e = nvs_open("r5", NVS_READWRITE, &h);
    if (e != ESP_OK) return e;
    e = nvs_set_blob(h, "cal", &ps, sizeof(ps));
    if (e == ESP_OK) e = nvs_commit(h);
    nvs_close(h);
    return e;
}

/* Compute everything derived and push it to codec + engine. Lock held. */
static esp_err_t commit(void)
{
    r5_params_t *p = &s_p;
    bool mm;
    p->mix_db = r5_mix_pct_to_db(p->mix_pct, &mm);
    p->mix_mute = mm;
    bool vol_mute = p->vol_pct <= 0;
    bool quiet = p->standby || p->test_mute || vol_mute;

    r5_wired_req_t *rq = &p->req;
    rq->vol_db = vol_mute ? -60.0f : p->wired_db;
    rq->dac_trim_db = p->dac_trim_db;
    rq->mix_db = p->mix_db;
    for (int s = 0; s < 2; s++) {
        rq->side_trim_db[s] = p->side_trim_db[s];
        rq->mute[s] = mm || p->byp_mute[s] || quiet;
    }
    const r5_codec_t *c = codec_get();
    r5_plan_wired(c->kind, rq, &p->plan);
    esp_err_t err = ESP_OK;
    if (codec_ok()) {
        err = c->apply_wired(&p->plan);
        if (err == ESP_OK) err = c->set_pga(p->pga_db, p->pga_real_db);
        if (err == ESP_OK) err = c->dac_mute(p->standby || vol_mute);
    } else {
        p->pga_real_db[0] = p->pga_db[0];
        p->pga_real_db[1] = p->pga_db[1];
    }

    /* internal mono accompaniment follows the REALISED bypass; -PGA_R removes
     * the right-channel analog gain so ADC-R is referred back to the AUX input */
    float cal = p->mix_cal_db - p->pga_real_db[1];
    p->internal_accomp_db = r5_plan_internal_accomp_db(&p->plan, rq, mm, cal);
    p->spk_ceiling = r5_spk_ceiling(p->spk_limit_w, p->spk_ohm, p->spk_vrms_fs);

    bool speaker_on = (p->out == R5_OUT_SPK || p->out == R5_OUT_SPK_BT) && !p->standby;
    bool i2s1_on = p->out != R5_OUT_HP && !quiet;
    r5_engine_params_t e = {
        .pickup_gain_db = p->pickup_gain_db,
        .bass_db = p->bass_db,
        .treble_db = p->treble_db,
        .fx_depth = (float)p->fx_pct / 100.0f,
        .fx_on = p->fx_on,
        .spk_vol_db = i2s1_on ? p->spk_db : -200.0f,
        .accomp_db = p->internal_accomp_db,
        .spk_limit_on = speaker_on && p->spk_limit_on,
        .spk_ceiling = p->spk_ceiling,
        .violin_mute = p->standby,
    };
    audio_set_engine(&e);
    spk_sd_set(speaker_on);
    ble_params_changed();
    return err;
}

void params_engine_initial(r5_engine_params_t *out)
{
    memset(out, 0, sizeof(*out));
    out->pickup_gain_db = s_p.pickup_gain_db;
    out->bass_db = s_p.bass_db;
    out->treble_db = s_p.treble_db;
    out->fx_depth = (float)s_p.fx_pct / 100.0f;
    out->fx_on = s_p.fx_on;
    out->spk_vol_db = -200.0f;         /* silent until codec + params are applied */
    out->accomp_db = -200.0f;
    out->spk_ceiling = 1.0f;
    out->violin_mute = true;
}

r5_params_t *params_lock(void)
{
    xSemaphoreTakeRecursive(s_mtx, portMAX_DELAY);
    return &s_p;
}

void params_unlock(bool do_commit)
{
    if (do_commit) commit();
    xSemaphoreGiveRecursive(s_mtx);
}

void params_get(r5_params_t *out)
{
    xSemaphoreTakeRecursive(s_mtx, portMAX_DELAY);
    *out = s_p;
    xSemaphoreGiveRecursive(s_mtx);
}

esp_err_t params_commit_now(void)
{
    xSemaphoreTakeRecursive(s_mtx, portMAX_DELAY);
    esp_err_t e = commit();
    xSemaphoreGiveRecursive(s_mtx);
    return e;
}
