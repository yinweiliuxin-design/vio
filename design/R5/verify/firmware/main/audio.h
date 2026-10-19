/* Audio I/O: I2S0 full duplex with the codec, I2S1 TX to MAX98357A + BT module. */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "r5dsp.h"

#define R5_FS 48000

typedef struct {
    uint32_t blocks;
    uint32_t proc_last_us, proc_max_us;
    float    proc_avg_us;
    uint32_t period_us;
    uint32_t rx_ovf;        /* RX DMA queue overflow: samples lost (audio task too late) */
    uint32_t tx0_ovf;       /* TX0 DMA queue overflow: codec DAC underrun */
    uint32_t tx1_ovf;       /* TX1 DMA queue overflow: speaker/BT underrun */
    uint32_t rd_err, wr0_err, wr1_err;
} audio_stats_t;

typedef struct {
    float peak[2];          /* linear, since last snapshot */
    float rms[2];
    uint32_t clips[2];      /* samples >= -0.01 dBFS since last snapshot */
    uint32_t frames;
} audio_levels_t;

/* Start I2S (MCLK runs after this returns) and the audio task on core 1. */
esp_err_t audio_start(const r5_engine_params_t *initial);
void audio_set_engine(const r5_engine_params_t *p);
void audio_get_engine(r5_engine_params_t *p);

void audio_get_stats(audio_stats_t *s);
void audio_reset_stats(void);
void audio_levels_snapshot(audio_levels_t *out);

/* Latency: emit a click on the DAC, record ADC-L, return lag in samples. */
esp_err_t audio_lat_measure(int *lag, float *snr, int rec_len);

/* Test tone: target 0 = off, 1 = DAC (wired outputs), 2 = I2S1 (spk/BT). */
void audio_tone(int target, float dbfs, float hz);

/* Tuner feed (ADC-L at 48 kHz). Returns floats read. */
size_t audio_tuner_read(float *buf, size_t max, TickType_t to);

int audio_block_frames(void);
int audio_dma_desc(void);
const char *audio_i2s1_mode(void);
float audio_min_limiter_gain(void);
