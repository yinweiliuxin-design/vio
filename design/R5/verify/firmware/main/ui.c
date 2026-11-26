/*
 * Encoders: ESP-IDF pulse counter (PCNT), 2 channels per unit in x4
 * quadrature mode as in examples/peripherals/pcnt/rotary_encoder. One EC11
 * detent = 4 counts. Buttons and encoder push switches: polled every 5 ms,
 * 20 ms debounce, active low with internal pull-ups.
 */
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/pulse_cnt.h"
#include "esp_log.h"
#include "sdkconfig.h"
#include "ui.h"
#include "params.h"
#include "btmod.h"

static const char *TAG = "ui";

typedef struct {
    const char *name;
    int a, b, sw;
    pcnt_unit_handle_t unit;
    int last;
    int acc;
} enc_t;

static enc_t s_enc[3] = {
    {"VOL", CONFIG_R5_PIN_ENC_VOL_A, CONFIG_R5_PIN_ENC_VOL_B, CONFIG_R5_PIN_ENC_VOL_SW, NULL, 0, 0},
    {"TONE", CONFIG_R5_PIN_ENC_TONE_A, CONFIG_R5_PIN_ENC_TONE_B, CONFIG_R5_PIN_ENC_TONE_SW, NULL, 0, 0},
    {"FX", CONFIG_R5_PIN_ENC_FX_A, CONFIG_R5_PIN_ENC_FX_B, CONFIG_R5_PIN_ENC_FX_SW, NULL, 0, 0},
};

enum { B_PWR, B_BT, B_MODE, B_FX, B_MIX, B_ENC_VOL, B_ENC_TONE, B_ENC_FX, B_COUNT };
static const char *k_btn_name[B_COUNT] = {"PWR", "BT", "MODE", "FX", "MIX", "VOL-push", "TONE-push", "FX-push"};
static int s_btn_pin[B_COUNT] = {
    CONFIG_R5_PIN_BTN_PWR, CONFIG_R5_PIN_BTN_BT, CONFIG_R5_PIN_BTN_MODE, CONFIG_R5_PIN_BTN_FX,
    CONFIG_R5_PIN_BTN_MIX, CONFIG_R5_PIN_ENC_VOL_SW, CONFIG_R5_PIN_ENC_TONE_SW, CONFIG_R5_PIN_ENC_FX_SW,
};
static uint8_t s_btn_hist[B_COUNT];
static bool s_btn_down[B_COUNT];
static uint32_t s_btn_t0[B_COUNT];
static const int k_led_pin[3] = {CONFIG_R5_PIN_LED_PWR, CONFIG_R5_PIN_LED_BT, CONFIG_R5_PIN_LED_OUT};
static int s_vol_before_mute = 85;

#define PCNT_LIM 30000

static esp_err_t enc_init(enc_t *e)
{
    if (e->a < 0 || e->b < 0) return ESP_OK;
    pcnt_unit_config_t uc = {.high_limit = PCNT_LIM, .low_limit = -PCNT_LIM};
    ESP_ERROR_CHECK(pcnt_new_unit(&uc, &e->unit));
    pcnt_glitch_filter_config_t fc = {.max_glitch_ns = 1000};
    ESP_ERROR_CHECK(pcnt_unit_set_glitch_filter(e->unit, &fc));
    pcnt_chan_config_t ca = {.edge_gpio_num = e->a, .level_gpio_num = e->b};
    pcnt_chan_config_t cb = {.edge_gpio_num = e->b, .level_gpio_num = e->a};
    pcnt_channel_handle_t ha, hb;
    ESP_ERROR_CHECK(pcnt_new_channel(e->unit, &ca, &ha));
    ESP_ERROR_CHECK(pcnt_new_channel(e->unit, &cb, &hb));
    ESP_ERROR_CHECK(pcnt_channel_set_edge_action(ha, PCNT_CHANNEL_EDGE_ACTION_DECREASE, PCNT_CHANNEL_EDGE_ACTION_INCREASE));
    ESP_ERROR_CHECK(pcnt_channel_set_level_action(ha, PCNT_CHANNEL_LEVEL_ACTION_KEEP, PCNT_CHANNEL_LEVEL_ACTION_INVERSE));
    ESP_ERROR_CHECK(pcnt_channel_set_edge_action(hb, PCNT_CHANNEL_EDGE_ACTION_INCREASE, PCNT_CHANNEL_EDGE_ACTION_DECREASE));
    ESP_ERROR_CHECK(pcnt_channel_set_level_action(hb, PCNT_CHANNEL_LEVEL_ACTION_KEEP, PCNT_CHANNEL_LEVEL_ACTION_INVERSE));
    gpio_pullup_en(e->a);
    gpio_pullup_en(e->b);
    ESP_ERROR_CHECK(pcnt_unit_enable(e->unit));
    ESP_ERROR_CHECK(pcnt_unit_clear_count(e->unit));
    ESP_ERROR_CHECK(pcnt_unit_start(e->unit));
    return ESP_OK;
}

/* returns whole detents since last call */
static int enc_detents(enc_t *e)
{
    if (!e->unit) return 0;
    int c = 0;
    pcnt_unit_get_count(e->unit, &c);
    int d = c - e->last;
    e->last = c;
    if (d > PCNT_LIM / 2) d -= PCNT_LIM;      /* counter wrapped at a limit */
    if (d < -PCNT_LIM / 2) d += PCNT_LIM;
    e->acc += d;
    int det = e->acc / 4;
    e->acc -= det * 4;
    return det;
}

static int clamp100(int v) { return v < 0 ? 0 : (v > 100 ? 100 : v); }

static void on_press(int b, uint32_t held_ms)
{
    r5_params_t *p = params_lock();
    bool commit = true;
    switch (b) {
    case B_PWR:
        if (held_ms >= 1000) {
            p->standby = !p->standby;
            printf("[UI] PWR long: %s\n", p->standby ? "standby (muted)" : "on");
        } else {
            commit = false;
            printf("[UI] PWR: vol %d mix %d fx %d%s tone %d out %s\n", p->vol_pct, p->mix_pct, p->fx_pct,
                   p->fx_on ? "" : "(off)", p->tone_pct, params_out_name(p->out));
        }
        break;
    case B_BT:
        p->bt_led = !p->bt_led;
        params_unlock(false);
        btmod_button_pressed();
        return;
    case B_MODE:
        p->out = (r5_out_t)(((int)p->out + 1) % 4);
        printf("[UI] output mode: %s\n", params_out_name(p->out));
        break;
    case B_FX:
        p->fx_on = !p->fx_on;
        printf("[UI] FX %s\n", p->fx_on ? "on" : "off");
        break;
    case B_MIX: {
        static const int presets[5] = {0, 25, 50, 75, 100};
        int i = 0;
        while (i < 5 && presets[i] <= p->mix_pct) i++;
        p->mix_pct = presets[i % 5];
        printf("[UI] MIX %d%%\n", p->mix_pct);
        break;
    }
    case B_ENC_VOL:
        if (p->vol_pct > 0) {
            s_vol_before_mute = p->vol_pct;
            p->vol_pct = 0;
        } else {
            p->vol_pct = s_vol_before_mute;
        }
        p->wired_db = p->spk_db = params_vol_db(p->vol_pct);
        printf("[UI] VOL %s\n", p->vol_pct ? "unmuted" : "muted");
        break;
    case B_ENC_TONE:
        params_set_tone_pct(p, 50);
        printf("[UI] tone flat\n");
        break;
    case B_ENC_FX:
        p->fx_pct = 30;
        printf("[UI] FX depth reset to 30%%\n");
        break;
    default:
        commit = false;
    }
    params_unlock(commit);
}

static void leds(uint32_t t_ms)
{
    r5_params_t p;
    params_get(&p);
    int pwr = p.standby ? ((t_ms % 1000) < 100) : 1;
    int out = 0;
    switch (p.out) {
    case R5_OUT_HP: out = 0; break;
    case R5_OUT_SPK: out = 1; break;
    case R5_OUT_BT: out = (t_ms % 500) < 250; break;
    case R5_OUT_SPK_BT: out = (t_ms % 200) < 100; break;
    }
    int v[3] = {pwr, p.bt_led ? 1 : 0, p.standby ? 0 : out};
    for (int i = 0; i < 3; i++) {
        if (k_led_pin[i] >= 0) gpio_set_level(k_led_pin[i], v[i]);
    }
}

static void ui_task(void *arg)
{
    uint32_t t = 0;
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(5));
        t += 5;
        for (int b = 0; b < B_COUNT; b++) {
            if (s_btn_pin[b] < 0) continue;
            int lvl = gpio_get_level(s_btn_pin[b]);
            s_btn_hist[b] = (uint8_t)((s_btn_hist[b] << 1) | (lvl ? 0 : 1));   /* 1 = pressed */
            uint8_t h = s_btn_hist[b] & 0x0F;
            if (!s_btn_down[b] && h == 0x0F) {
                s_btn_down[b] = true;
                s_btn_t0[b] = t;
            } else if (s_btn_down[b] && h == 0x00) {
                s_btn_down[b] = false;
                on_press(b, t - s_btn_t0[b]);
            }
        }
        if (t % 10 == 0) {
            int d[3];
            bool any = false;
            for (int i = 0; i < 3; i++) {
                d[i] = enc_detents(&s_enc[i]);
                any |= d[i] != 0;
            }
            if (any) {
                r5_params_t *p = params_lock();
                if (d[0]) {
                    p->vol_pct = clamp100(p->vol_pct + 2 * d[0]);
                    p->wired_db = p->spk_db = params_vol_db(p->vol_pct);
                }
                if (d[1]) params_set_tone_pct(p, p->tone_pct + 2 * d[1]);
                if (d[2]) p->fx_pct = clamp100(p->fx_pct + 5 * d[2]);
                printf("[UI] vol %d tone %d fx %d\n", p->vol_pct, p->tone_pct, p->fx_pct);
                params_unlock(true);
            }
        }
        if (t % 50 == 0) leds(t);
    }
}

esp_err_t ui_start(void)
{
    for (int i = 0; i < 3; i++) {
        if (enc_init(&s_enc[i]) != ESP_OK) ESP_LOGW(TAG, "encoder %s init failed", s_enc[i].name);
    }
    for (int b = 0; b < B_COUNT; b++) {
        if (s_btn_pin[b] < 0) continue;
        gpio_config_t io = {
            .pin_bit_mask = 1ULL << s_btn_pin[b],
            .mode = GPIO_MODE_INPUT,
            .pull_up_en = GPIO_PULLUP_ENABLE,
        };
        gpio_config(&io);
        s_btn_hist[b] = 0;
    }
    for (int i = 0; i < 3; i++) {
        if (k_led_pin[i] < 0) continue;
        gpio_config_t io = {.pin_bit_mask = 1ULL << k_led_pin[i], .mode = GPIO_MODE_OUTPUT};
        gpio_config(&io);
        gpio_set_level(k_led_pin[i], 0);
    }
    xTaskCreatePinnedToCore(ui_task, "ui", 3584, NULL, 5, NULL, 0);
    return ESP_OK;
}

void ui_print_state(void)
{
    for (int i = 0; i < 3; i++) {
        int c = 0;
        if (s_enc[i].unit) pcnt_unit_get_count(s_enc[i].unit, &c);
        printf("  enc %-4s A=%d B=%d SW=%d count=%d\n", s_enc[i].name, s_enc[i].a, s_enc[i].b, s_enc[i].sw, c);
    }
    for (int b = 0; b < B_COUNT; b++) {
        int lvl = s_btn_pin[b] >= 0 ? gpio_get_level(s_btn_pin[b]) : -1;
        printf("  btn %-9s GPIO%-2d level=%d%s\n", k_btn_name[b], s_btn_pin[b], lvl, lvl == 0 ? " (pressed)" : "");
    }
}
