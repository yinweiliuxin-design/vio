/* Codec selection: Kconfig default, optional NVS override (console `codec use`). */
#include <string.h>
#include "esp_log.h"
#include "nvs.h"
#include "sdkconfig.h"
#include "codec.h"
#include "i2c_bus.h"

static const char *TAG = "codec";
static const r5_codec_t *s_codec;
static bool s_ok;

static const r5_codec_t *kconfig_default(void)
{
#if CONFIG_R5_CODEC_AIC3204
    return &r5_codec_aic3204;
#else
    return &r5_codec_es8388;
#endif
}

const r5_codec_t *codec_get(void) { return s_codec ? s_codec : kconfig_default(); }
bool codec_ok(void) { return s_ok; }

esp_err_t codec_set_override(const char *which)
{
#if CONFIG_R5_CODEC_RUNTIME_SWITCH
    nvs_handle_t h;
    esp_err_t e = nvs_open("r5", NVS_READWRITE, &h);
    if (e != ESP_OK) return e;
    if (strcmp(which, "default") == 0) {
        nvs_erase_key(h, "codec");
    } else {
        e = nvs_set_str(h, "codec", which);
    }
    if (e == ESP_OK) e = nvs_commit(h);
    nvs_close(h);
    return e;
#else
    (void)which;
    return ESP_ERR_NOT_SUPPORTED;
#endif
}

esp_err_t codec_select_and_init(void)
{
    s_codec = kconfig_default();
#if CONFIG_R5_CODEC_RUNTIME_SWITCH
    nvs_handle_t h;
    if (nvs_open("r5", NVS_READONLY, &h) == ESP_OK) {
        char buf[8] = {0};
        size_t len = sizeof(buf);
        if (nvs_get_str(h, "codec", buf, &len) == ESP_OK) {
            if (strcmp(buf, "aic") == 0) s_codec = &r5_codec_aic3204;
            if (strcmp(buf, "es") == 0) s_codec = &r5_codec_es8388;
            ESP_LOGI(TAG, "NVS override: %s", buf);
        }
        nvs_close(h);
    }
#endif
    ESP_LOGI(TAG, "selected %s at I2C 0x%02x", s_codec->name, s_codec->addr);
    esp_err_t e = r5_i2c_probe(s_codec->addr);
    if (e != ESP_OK) {
        ESP_LOGE(TAG, "%s not answering at 0x%02x (%s). Audio runs, codec not configured.",
                 s_codec->name, s_codec->addr, esp_err_to_name(e));
        r5_i2c_scan();
        s_ok = false;
        return e;
    }
    e = s_codec->init();
    s_ok = (e == ESP_OK);
    if (!s_ok) ESP_LOGE(TAG, "init failed: %s", esp_err_to_name(e));
    return e;
}
