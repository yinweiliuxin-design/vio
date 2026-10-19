/*
 * Codec abstraction. Both drivers implement the same routing:
 *   ADC-L  = violin pickup (after the external op-amp buffer)
 *   ADC-R  = accompaniment mono (AUX L + AUX R)
 *   bypass = AUX L/R -> output mixers -> HP (and LINE where the chip allows)
 *   DAC    = processed violin only
 * Register sequences are re-implemented from the sources cited in each driver
 * (Linux sound/soc/codecs, Espressif esp-adf); see CODEC-FINDINGS.md.
 */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "r5dsp.h"

typedef struct {
    const char *name;
    r5_codec_kind_t kind;
    uint8_t addr;                 /* 7-bit I2C address */
    esp_err_t (*init)(void);      /* MCLK/BCLK/WS must already be running */
    esp_err_t (*apply_wired)(const r5_wired_plan_t *plan);
    esp_err_t (*set_pga)(const float db[2], float real_db[2]);
    esp_err_t (*dac_mute)(bool mute);
    esp_err_t (*reg_read)(uint16_t addr, uint8_t *val);
    esp_err_t (*reg_write)(uint16_t addr, uint8_t val);
    void (*dump)(void);
    const char *input_map;        /* which codec pin carries what */
    const char *limits;           /* short honest list of known limitations */
} r5_codec_t;

extern const r5_codec_t r5_codec_aic3204;
extern const r5_codec_t r5_codec_es8388;

/* Selected codec (Kconfig default, or NVS override when runtime switch is on). */
const r5_codec_t *codec_get(void);
bool codec_ok(void);              /* probed and initialised */
esp_err_t codec_select_and_init(void);
esp_err_t codec_set_override(const char *which);   /* "aic" / "es" / "default" */
