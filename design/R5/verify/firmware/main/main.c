/*
 * SmartVio R5 bench-verification firmware (ESP32-S3-DevKitC-1).
 * Boot order matters: I2S (MCLK) must run before the codec is initialised.
 */
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "sdkconfig.h"
#include "audio.h"
#include "ble.h"
#include "btmod.h"
#include "codec.h"
#include "console_cmds.h"
#include "i2c_bus.h"
#include "params.h"
#include "tuner_task.h"
#include "ui.h"

static const char *TAG = "r5";

typedef struct {
    const char *name;
    int pin;
} pin_use_t;

/* Report pins used twice and pins that need care on the DevKitC-1. */
static void check_pins(void)
{
    const pin_use_t pins[] = {
        {"I2S0_MCLK", CONFIG_R5_PIN_I2S0_MCLK}, {"I2S0_BCLK", CONFIG_R5_PIN_I2S0_BCLK},
        {"I2S0_WS", CONFIG_R5_PIN_I2S0_WS},     {"I2S0_DOUT", CONFIG_R5_PIN_I2S0_DOUT},
        {"I2S0_DIN", CONFIG_R5_PIN_I2S0_DIN},   {"I2S1_DOUT", CONFIG_R5_PIN_I2S1_DOUT},
#if !CONFIG_R5_I2S1_CLK_SHARED_BCLK
        {"I2S1_BCLK", CONFIG_R5_PIN_I2S1_BCLK}, {"I2S1_WS", CONFIG_R5_PIN_I2S1_WS},
#endif
        {"I2C_SDA", CONFIG_R5_PIN_I2C_SDA},     {"I2C_SCL", CONFIG_R5_PIN_I2C_SCL},
        {"BT_TX", CONFIG_R5_PIN_BT_TX},         {"BT_RX", CONFIG_R5_PIN_BT_RX},
        {"SPK_SD", CONFIG_R5_PIN_SPK_SD},       {"ENC_VOL_A", CONFIG_R5_PIN_ENC_VOL_A},
        {"ENC_VOL_B", CONFIG_R5_PIN_ENC_VOL_B}, {"ENC_VOL_SW", CONFIG_R5_PIN_ENC_VOL_SW},
        {"ENC_TONE_A", CONFIG_R5_PIN_ENC_TONE_A}, {"ENC_TONE_B", CONFIG_R5_PIN_ENC_TONE_B},
        {"ENC_TONE_SW", CONFIG_R5_PIN_ENC_TONE_SW}, {"ENC_FX_A", CONFIG_R5_PIN_ENC_FX_A},
        {"ENC_FX_B", CONFIG_R5_PIN_ENC_FX_B},   {"ENC_FX_SW", CONFIG_R5_PIN_ENC_FX_SW},
        {"BTN_PWR", CONFIG_R5_PIN_BTN_PWR},     {"BTN_BT", CONFIG_R5_PIN_BTN_BT},
        {"BTN_MODE", CONFIG_R5_PIN_BTN_MODE},   {"BTN_FX", CONFIG_R5_PIN_BTN_FX},
        {"BTN_MIX", CONFIG_R5_PIN_BTN_MIX},     {"LED_PWR", CONFIG_R5_PIN_LED_PWR},
        {"LED_BT", CONFIG_R5_PIN_LED_BT},       {"LED_OUT", CONFIG_R5_PIN_LED_OUT},
    };
    const int n = sizeof(pins) / sizeof(pins[0]);
    for (int i = 0; i < n; i++) {
        int g = pins[i].pin;
        if (g < 0) continue;
        for (int j = i + 1; j < n; j++) {
            if (pins[j].pin == g) ESP_LOGE(TAG, "PIN CLASH: GPIO%d used by %s and %s", g, pins[i].name, pins[j].name);
        }
        if (g == 19 || g == 20) ESP_LOGE(TAG, "%s on GPIO%d = USB D-/D+ (console!)", pins[i].name, g);
        if (g >= 35 && g <= 37) ESP_LOGE(TAG, "%s on GPIO%d = octal PSRAM", pins[i].name, g);
        if (g == 38 || g == 48) ESP_LOGW(TAG, "%s on GPIO%d = on-board RGB LED (v1.0/v1.1)", pins[i].name, g);
        if (g == 0 || g == 3 || g == 45 || g == 46) ESP_LOGW(TAG, "%s on strapping GPIO%d (see WIRING.md)", pins[i].name, g);
        if (g == 43 || g == 44) ESP_LOGW(TAG, "%s on GPIO%d = UART0 to the USB-UART bridge", pins[i].name, g);
    }
}

void app_main(void)
{
    esp_err_t e = nvs_flash_init();
    if (e == ESP_ERR_NVS_NO_FREE_PAGES || e == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
    printf("\nSmartVio R5 bench firmware - compiled %s %s - NOT verified on hardware yet\n", __DATE__, __TIME__);
    check_pins();

    params_init();
    r5_engine_params_t ep;
    params_engine_initial(&ep);
    ESP_ERROR_CHECK(r5_i2c_init(CONFIG_R5_PIN_I2C_SDA, CONFIG_R5_PIN_I2C_SCL, 100000));
    ESP_ERROR_CHECK(audio_start(&ep));          /* MCLK/BCLK/WS running from here */
    vTaskDelay(pdMS_TO_TICKS(20));
    codec_select_and_init();                    /* logs and continues if absent */
    params_commit_now();                        /* writes codec gains, unmutes engine */

    btmod_start(CONFIG_R5_PIN_BT_TX, CONFIG_R5_PIN_BT_RX, CONFIG_R5_BT_UART_BAUD);
    ui_start();
    tuner_start();
    ble_start();
    vTaskDelay(pdMS_TO_TICKS(500));
    audio_reset_stats();                        /* ignore start-up transients */
    ESP_LOGI(TAG, "ready - type `help`");
    console_start();
}
