/*
 * Everest ES8388 driver for the R5 bench (I2C, codec = I2S slave).
 *
 * Register meanings and sequences re-implemented from (no code copied):
 *   [L]  Linux sound/soc/codecs/es8328.c / es8328.h (torvalds/master)
 *   [A]  Espressif esp-adf components/audio_hal/driver/es8388/es8388.c (v2.7)
 *        and components/esp_codec_dev/device/es8388/es8388.c (master)
 *
 * Input pin map chosen for the bench (see CODEC-FINDINGS.md):
 *   LINPUT1 <- pickup buffer           -> Left PGA (LINSEL = Line 1)  -> ADC-L
 *   LINPUT2 <- AUX L                   -> Left Line Mux (Line 2) -> LI2LO bypass
 *   RINPUT2 <- AUX R                   -> Right Line Mux (Line 2) -> RI2RO bypass
 *   RINPUT1 <- AUX L+R external sum    -> Right PGA (RINSEL = Line 1) -> ADC-R
 * The ES8388 ADC input is a selector, not a mixer ([L] "Left/Right PGA Mux"),
 * so the mono sum is made outside the chip (2 resistors or an op-amp).
 * Left/right output mixers drive OUT1 (headphone) and OUT2 (line) together.
 */
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "sdkconfig.h"
#include "codec.h"
#include "i2c_bus.h"

static const char *TAG = "es8388";

/* register addresses ([L] es8328.h, [A] es8388_reg.h agree) */
#define ES_CONTROL1    0x00
#define ES_CONTROL2    0x01
#define ES_CHIPPOWER   0x02
#define ES_ADCPOWER    0x03
#define ES_DACPOWER    0x04
#define ES_MASTERMODE  0x08
#define ES_ADCCONTROL1 0x09
#define ES_ADCCONTROL2 0x0a
#define ES_ADCCONTROL3 0x0b
#define ES_ADCCONTROL4 0x0c
#define ES_ADCCONTROL5 0x0d
#define ES_ADCCONTROL8 0x10
#define ES_ADCCONTROL9 0x11
#define ES_DACCONTROL1 0x17
#define ES_DACCONTROL2 0x18
#define ES_DACCONTROL3 0x19
#define ES_LDACVOL     0x1a   /* DACCONTROL4 */
#define ES_RDACVOL     0x1b   /* DACCONTROL5 */
#define ES_DACCONTROL6 0x1c
#define ES_DACCONTROL16 0x26
#define ES_DACCONTROL17 0x27
#define ES_DACCONTROL18 0x28
#define ES_DACCONTROL19 0x29
#define ES_DACCONTROL20 0x2a
#define ES_DACCONTROL21 0x2b
#define ES_DACCONTROL23 0x2d
#define ES_LOUT1VOL    0x2e
#define ES_ROUT1VOL    0x2f
#define ES_LOUT2VOL    0x30
#define ES_ROUT2VOL    0x31

static i2c_master_dev_handle_t s_dev;
static SemaphoreHandle_t s_mtx;

static esp_err_t es_w(uint16_t a, uint8_t v)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    esp_err_t e = r5_i2c_wr(s_dev, (uint8_t)a, v);
    xSemaphoreGive(s_mtx);
    if (e != ESP_OK) ESP_LOGW(TAG, "write 0x%02x failed: %s", a, esp_err_to_name(e));
    return e;
}

static esp_err_t es_r(uint16_t a, uint8_t *v)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    esp_err_t e = r5_i2c_rd(s_dev, (uint8_t)a, v);
    xSemaphoreGive(s_mtx);
    return e;
}

#define W(a, v) do { esp_err_t _e = es_w((a), (v)); if (_e != ESP_OK) return _e; } while (0)

static esp_err_t es_init(void)
{
    if (!s_mtx) s_mtx = xSemaphoreCreateMutex();
    if (!s_dev) {
        esp_err_t e = r5_i2c_add(CONFIG_R5_ES_I2C_ADDR, &s_dev);
        if (e != ESP_OK) return e;
    }

    /* 1. [A] es8388_open(): mute DAC, CONTROL2 = 0x50, CHIPPOWER = 0 (all on). */
    W(ES_DACCONTROL3, 0x04);
    W(ES_CONTROL2, 0x50);
    W(ES_CHIPPOWER, 0x00);
    /* 2. Slave serial port: MASTERMODE.MSC (bit7) = 0 ([L] set_dai_fmt CBC_CFC). */
    W(ES_MASTERMODE, 0x00);
    /* 3. DAC and outputs off while configuring ([A] DACPOWER = 0xC0). */
    W(ES_DACPOWER, 0xC0);
    /* 4. Reference: [L] set_bias_level: from OFF use VMIDSEL 5k + ENREF and wait
     *    100 ms to charge the caps, then 50k + ENREF for normal operation.
     *    SAMEFS (bit4, ADC and DAC same rate) as in [A] (CONTROL1 = 0x12). */
    W(ES_CONTROL1, 0x10 | 0x04 | 0x03);
    vTaskDelay(pdMS_TO_TICKS(100));
    W(ES_CONTROL1, 0x10 | 0x04 | 0x01);
    /* 5. DAC data: I2S, 24-bit ([L] hw_params wl=0 for 24 bit, DACWL bits 5:3;
     *    [A] comment "0x00:24"). S3 sends 32-bit slots, LSBs ignored. */
    W(ES_DACCONTROL1, 0x00);
    /* 6. DAC single speed, MCLK/LRCK = 256 ([A] DACCONTROL2 = 0x02). */
    W(ES_DACCONTROL2, 0x02);
    /* 7. De-emphasis off, click-free on ([L] ES8328_DACCONTROL6_CLICKFREE). */
    W(ES_DACCONTROL6, 0x08);
    /* 8. Bypass sources: LIN2 -> left mixer, RIN2 -> right mixer
     *    ([A] DACCONTROL16 = 0x09 "LIN2&RIN2 by pass"; [L] LMIXSEL bits 5:3,
     *    RMIXSEL bits 2:0, value 1 = "Line 2"). */
    W(ES_DACCONTROL16, 0x09);
    /* 9. Output mixers: DAC on (LD2LO / RD2RO bit7), bypass off for now,
     *    no cross terms (DACCONTROL18/19 = 0). [A] uses 0x90 = DAC only 0 dB. */
    W(ES_DACCONTROL17, 0x90);
    W(ES_DACCONTROL18, 0x00);
    W(ES_DACCONTROL19, 0x00);
    W(ES_DACCONTROL20, 0x90);
    /* 10. ADC and DAC share LRCK ([A] DACCONTROL21 = 0x80), VROI = 0 ([A]). */
    W(ES_DACCONTROL21, 0x80);
    W(ES_DACCONTROL23, 0x00);
    /* 11. Output volumes start at -30 dB (code 0), DAC digital volume 0 dB. */
    W(ES_LOUT1VOL, 0x00);
    W(ES_ROUT1VOL, 0x00);
    W(ES_LOUT2VOL, 0x00);
    W(ES_ROUT2VOL, 0x00);
    W(ES_LDACVOL, 0x00);
    W(ES_RDACVOL, 0x00);
    /* 12. Power DACs and LOUT1/ROUT1/LOUT2/ROUT2 ([A] DAC_OUTPUT_ALL = 0x3c). */
    W(ES_DACPOWER, 0x3C);

    /* 13. ADC: power down while configuring ([A] ADCPOWER = 0xFF). */
    W(ES_ADCPOWER, 0xFF);
    W(ES_ADCCONTROL1, 0x00);   /* MicAmp L/R 0 dB, set later */
    /* LINSEL = Line 1 (pickup), RINSEL = Line 1 (AUX mono sum)
     * ([A] ADC_INPUT_LINPUT1_RINPUT1 = 0x00; [L] PGA mux bits 7:6 / 5:4). */
    W(ES_ADCCONTROL2, 0x00);
    W(ES_ADCCONTROL3, 0x02);   /* [A] value; bits 4:3 = 00 -> "Stereo" ([L] monomux) */
    W(ES_ADCCONTROL4, 0x00);   /* I2S, 24-bit ([L] ADCWL = 0) */
    W(ES_ADCCONTROL5, 0x02);   /* single speed, 256 fs ([A]) */
    W(ES_ADCCONTROL8, 0x00);   /* ADC digital volume 0 dB */
    W(ES_ADCCONTROL9, 0x00);
    W(ES_ADCPOWER, 0x09);      /* ADC + inputs on, mic bias off ([A] 0x09) */

    /* 14. Restart the state machines ([A] es8388_start: CHIPPOWER 0xF0 -> 0x00). */
    W(ES_CHIPPOWER, 0xF0);
    W(ES_CHIPPOWER, 0x00);
    W(ES_ADCPOWER, 0x09);
    /* 15. Unmute DAC ([A] set_voice_mute(false): DACCONTROL3 bit2 = 0). */
    W(ES_DACCONTROL3, 0x00);

    ESP_LOGI(TAG, "initialised (LIN1 pickup, LIN2/RIN2 AUX bypass, RIN1 AUX mono)");
    return ESP_OK;
}

static esp_err_t es_apply_wired(const r5_wired_plan_t *p)
{
    /* DACCONTROL17: LD2LO b7 | LI2LO b6 | LI2LOVOL b5:3 ([L] es8328.h) */
    W(ES_DACCONTROL17, 0x80 | (p->mute[0] ? 0 : 0x40) | (uint8_t)(p->es_byp_code[0] << 3));
    /* DACCONTROL20: RD2RO b7 | RI2RO b6 | RI2ROVOL b5:3 */
    W(ES_DACCONTROL20, 0x80 | (p->mute[1] ? 0 : 0x40) | (uint8_t)(p->es_byp_code[1] << 3));
    W(ES_LDACVOL, p->es_dacvol[0]);
    W(ES_RDACVOL, p->es_dacvol[1]);
    W(ES_LOUT1VOL, p->es_outvol[0]);
    W(ES_ROUT1VOL, p->es_outvol[1]);
    W(ES_LOUT2VOL, p->es_outvol[0]);
    W(ES_ROUT2VOL, p->es_outvol[1]);
    return ESP_OK;
}

static esp_err_t es_set_pga(const float db[2], float real[2])
{
    uint8_t l = r5_es_pga_code(db[0], &real[0]);
    uint8_t r = r5_es_pga_code(db[1], &real[1]);
    return es_w(ES_ADCCONTROL1, (uint8_t)((l << 4) | r));   /* [A] set_mic_gain layout */
}

static esp_err_t es_dac_mute(bool mute)
{
    uint8_t v = 0;
    esp_err_t e = es_r(ES_DACCONTROL3, &v);
    if (e != ESP_OK) return e;
    v = (uint8_t)((v & ~0x04) | (mute ? 0x04 : 0x00));
    return es_w(ES_DACCONTROL3, v);
}

static void es_dump(void)
{
    for (int a = 0; a <= 0x34; a++) {
        uint8_t v = 0;
        esp_err_t e = es_r((uint16_t)a, &v);
        printf("  0x%02x = 0x%02x%s", a, v, e == ESP_OK ? "" : "(err)");
        printf((a % 4 == 3) ? "\n" : "   ");
    }
    printf("\n");
}

const r5_codec_t r5_codec_es8388 = {
    .name = "ES8388",
    .kind = R5_CODEC_ES8388,
    .addr = CONFIG_R5_ES_I2C_ADDR,
    .init = es_init,
    .apply_wired = es_apply_wired,
    .set_pga = es_set_pga,
    .dac_mute = es_dac_mute,
    .reg_read = es_r,
    .reg_write = es_w,
    .dump = es_dump,
    .input_map = "LINPUT1=pickup; LINPUT2=AUX L; RINPUT2=AUX R; RINPUT1=AUX L+R (external sum); "
                 "LOUT1/ROUT1=headphone, LOUT2/ROUT2=line (both DAC+bypass)",
    .limits = "ADC input is a selector: AUX mono sum must be made externally; "
              "PGA max +24 dB (3 dB steps); bypass -15..+6 dB in 3 dB steps",
};
