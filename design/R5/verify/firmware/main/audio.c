/*
 * Audio task (core 1).
 *
 * I2S0  master, full duplex with the codec: 48 kHz, Philips I2S, 2 x 32-bit
 *       slots (codec uses 24-bit words), MCLK = 256 fs = 12.288 MHz output.
 * I2S1  TX only, 48 kHz stereo (L = R = mix) to MAX98357A DIN and the BT
 *       module I2S input on the same lines. Clock domain shared with I2S0,
 *       selected in menuconfig (R5_I2S1_CLK):
 *   SHARED_BCLK  I2S1 is an I2S SLAVE whose BCLK/WS inputs are the very pads
 *                driven by I2S0 (GPIO matrix input + output on one pad). Same
 *                edges as the codec; only the DOUT pin is extra. Frame format
 *                therefore equals I2S0 (32-bit slots, 64 fs BCLK).
 *   EXT_MCLK     I2S1 master, clock source I2S_CLK_SRC_EXTERNAL fed from the
 *                I2S0 MCLK pad (12.288 MHz), integer division to BCLK.
 *   SAME_PLL     I2S1 master from PLL_F160M with the same divider settings as
 *                I2S0: same average rate, not phase locked.
 * The ESP32-S3 has no APLL (soc_caps: I2S clocks are PLL_F240M, PLL_F160M,
 * XTAL, EXTERNAL), so "same APLL" is realised as above.
 */
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/stream_buffer.h"
#include "driver/i2s_std.h"
#include "driver/gpio.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "sdkconfig.h"
#include "audio.h"

static const char *TAG = "audio";

#define N     CONFIG_R5_AUDIO_BLOCK_FRAMES
#define DESC  CONFIG_R5_AUDIO_DMA_DESC
#define LAT_CLICK_LEN 16
#define LAT_QUIET_MS  200

#if CONFIG_R5_I2S1_16BIT
typedef int16_t i2s1_sample_t;
#else
typedef int32_t i2s1_sample_t;
#endif

static i2s_chan_handle_t s_tx0, s_rx0, s_tx1;
static r5_engine_t s_eng;
static int32_t s_rx[N * 2], s_tx0b[N * 2];
static i2s1_sample_t s_tx1b[N * 2];
static float s_l[N], s_r[N], s_dac[N], s_spk[N], s_scr[N];

static volatile uint32_t s_rx_ovf, s_tx0_ovf, s_tx1_ovf;
static audio_stats_t s_st;
static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static struct {
    float peak[2];
    double sumsq[2];
    uint32_t clips[2];
    uint32_t frames;
} s_lev;

static StreamBufferHandle_t s_tuner_sb;
static SemaphoreHandle_t s_ready;

/* latency test state */
enum { LAT_IDLE, LAT_QUIET, LAT_REC, LAT_DONE };
static volatile int s_lat_state = LAT_IDLE;
static int s_lat_quiet, s_lat_pos, s_lat_len;
static float *s_lat_buf;
static float s_click[LAT_CLICK_LEN];
static TaskHandle_t s_lat_waiter;

/* test tone */
static volatile int s_tone_target;
static volatile float s_tone_amp, s_tone_inc;
static float s_tone_ph;

/* ------------------------------------------------------------- callbacks */
static IRAM_ATTR bool cb_rx_ovf(i2s_chan_handle_t h, i2s_event_data_t *e, void *ctx)
{
    s_rx_ovf++;
    return false;
}
static IRAM_ATTR bool cb_tx0_ovf(i2s_chan_handle_t h, i2s_event_data_t *e, void *ctx)
{
    s_tx0_ovf++;
    return false;
}
static IRAM_ATTR bool cb_tx1_ovf(i2s_chan_handle_t h, i2s_event_data_t *e, void *ctx)
{
    s_tx1_ovf++;
    return false;
}

/* ------------------------------------------------------------- I2S setup */
static i2s_std_config_t std_cfg_32(int mclk, int bclk, int ws, int dout, int din)
{
    i2s_std_config_t c = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(R5_FS),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .mclk = mclk, .bclk = bclk, .ws = ws, .dout = dout, .din = din,
            .invert_flags = {.mclk_inv = false, .bclk_inv = false, .ws_inv = false},
        },
    };
    c.clk_cfg.clk_src = I2S_CLK_SRC_PLL_160M;
    c.clk_cfg.mclk_multiple = I2S_MCLK_MULTIPLE_256;
    return c;
}

static esp_err_t i2s1_create(void)
{
    i2s_chan_config_t cc;
#if CONFIG_R5_I2S1_CLK_SHARED_BCLK
    cc = (i2s_chan_config_t)I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_SLAVE);
#else
    cc = (i2s_chan_config_t)I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
#endif
    cc.dma_desc_num = DESC + 1;
    cc.dma_frame_num = N;
    cc.auto_clear = true;
    ESP_ERROR_CHECK(i2s_new_channel(&cc, &s_tx1, NULL));

#if CONFIG_R5_I2S1_CLK_SHARED_BCLK
    i2s_std_config_t c = std_cfg_32(I2S_GPIO_UNUSED, CONFIG_R5_PIN_I2S0_BCLK, CONFIG_R5_PIN_I2S0_WS,
                                    CONFIG_R5_PIN_I2S1_DOUT, I2S_GPIO_UNUSED);
#else
#if CONFIG_R5_I2S1_16BIT
    i2s_std_config_t c = std_cfg_32(I2S_GPIO_UNUSED, CONFIG_R5_PIN_I2S1_BCLK, CONFIG_R5_PIN_I2S1_WS,
                                    CONFIG_R5_PIN_I2S1_DOUT, I2S_GPIO_UNUSED);
    c.slot_cfg = (i2s_std_slot_config_t)I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                                            I2S_SLOT_MODE_STEREO);
#else
    i2s_std_config_t c = std_cfg_32(I2S_GPIO_UNUSED, CONFIG_R5_PIN_I2S1_BCLK, CONFIG_R5_PIN_I2S1_WS,
                                    CONFIG_R5_PIN_I2S1_DOUT, I2S_GPIO_UNUSED);
#endif
#if CONFIG_R5_I2S1_CLK_EXT_MCLK
    c.clk_cfg.clk_src = I2S_CLK_SRC_EXTERNAL;
    c.clk_cfg.ext_clk_freq_hz = R5_FS * 256;
    c.gpio_cfg.mclk = CONFIG_R5_PIN_I2S0_MCLK;      /* input from the I2S0 MCLK pad */
#endif
#endif
    return i2s_channel_init_std_mode(s_tx1, &c);
}

static esp_err_t i2s_setup(void)
{
    /* I2S1 first: its shared pads are configured as inputs; I2S0 then turns the
     * same pads into outputs (which clears the pad input enable). */
    ESP_ERROR_CHECK(i2s1_create());

    i2s_chan_config_t cc = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    cc.dma_desc_num = DESC;
    cc.dma_frame_num = N;
    cc.auto_clear = true;
    ESP_ERROR_CHECK(i2s_new_channel(&cc, &s_tx0, &s_rx0));
    i2s_std_config_t c0 = std_cfg_32(CONFIG_R5_PIN_I2S0_MCLK, CONFIG_R5_PIN_I2S0_BCLK, CONFIG_R5_PIN_I2S0_WS,
                                     CONFIG_R5_PIN_I2S0_DOUT, CONFIG_R5_PIN_I2S0_DIN);
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(s_tx0, &c0));
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(s_rx0, &c0));

    /* Re-enable the input buffer of shared pads so I2S1 sees I2S0's clocks.
     * gpio_input_enable() only sets IE; the I2S0 output routing stays. */
#if CONFIG_R5_I2S1_CLK_SHARED_BCLK
    gpio_input_enable(CONFIG_R5_PIN_I2S0_BCLK);
    gpio_input_enable(CONFIG_R5_PIN_I2S0_WS);
#elif CONFIG_R5_I2S1_CLK_EXT_MCLK
    gpio_input_enable(CONFIG_R5_PIN_I2S0_MCLK);
#endif

    i2s_event_callbacks_t cb_rx = {.on_recv_q_ovf = cb_rx_ovf};
    i2s_event_callbacks_t cb_t0 = {.on_send_q_ovf = cb_tx0_ovf};
    i2s_event_callbacks_t cb_t1 = {.on_send_q_ovf = cb_tx1_ovf};
    ESP_ERROR_CHECK(i2s_channel_register_event_callback(s_rx0, &cb_rx, NULL));
    ESP_ERROR_CHECK(i2s_channel_register_event_callback(s_tx0, &cb_t0, NULL));
    ESP_ERROR_CHECK(i2s_channel_register_event_callback(s_tx1, &cb_t1, NULL));

    /* Preload silence so each TX ring starts full (steady-state TX delay is
     * then (DESC-1)..DESC blocks), then start: I2S1 (slave waits for clocks),
     * TX0, RX0. */
    static int32_t zeros[N * 2];
    size_t loaded;
    for (int i = 0; i < DESC + 1; i++) {
        i2s_channel_preload_data(s_tx1, zeros, sizeof(s_tx1b), &loaded);
        if (!loaded) break;
    }
    for (int i = 0; i < DESC; i++) {
        i2s_channel_preload_data(s_tx0, zeros, sizeof(zeros), &loaded);
        if (!loaded) break;
    }
    ESP_ERROR_CHECK(i2s_channel_enable(s_tx1));
    ESP_ERROR_CHECK(i2s_channel_enable(s_tx0));
    ESP_ERROR_CHECK(i2s_channel_enable(s_rx0));
    return ESP_OK;
}

/* -------------------------------------------------------------- helpers */
static inline float s2f(int32_t v)
{
    return (float)(v & (int32_t)0xFFFFFF00) * (1.0f / 2147483648.0f);   /* 24-bit data */
}

static inline int32_t f2s32(float x)
{
    if (x > 0.99999988f) x = 0.99999988f;
    if (x < -1.0f) x = -1.0f;
    return (int32_t)(x * 2147483648.0f) & (int32_t)0xFFFFFF00;
}

static inline i2s1_sample_t f2s1(float x)
{
#if CONFIG_R5_I2S1_16BIT
    if (x > 0.99997f) x = 0.99997f;
    if (x < -1.0f) x = -1.0f;
    return (int16_t)lrintf(x * 32767.0f);
#else
    return f2s32(x);
#endif
}

static void meter(void)
{
    float pk[2] = {0, 0};
    float ss[2] = {0, 0};          /* float per block (double is soft-float on the S3) */
    uint32_t cl[2] = {0, 0};
    for (int i = 0; i < N; i++) {
        float a = fabsf(s_l[i]), b = fabsf(s_r[i]);
        if (a > pk[0]) pk[0] = a;
        if (b > pk[1]) pk[1] = b;
        ss[0] += s_l[i] * s_l[i];
        ss[1] += s_r[i] * s_r[i];
        if (a >= 0.999f) cl[0]++;
        if (b >= 0.999f) cl[1]++;
    }
    taskENTER_CRITICAL(&s_mux);
    for (int c = 0; c < 2; c++) {
        if (pk[c] > s_lev.peak[c]) s_lev.peak[c] = pk[c];
        s_lev.sumsq[c] += ss[c];
        s_lev.clips[c] += cl[c];
    }
    s_lev.frames += N;
    taskEXIT_CRITICAL(&s_mux);
}

static void lat_step(void)
{
    int st = s_lat_state;
    if (st == LAT_QUIET) {
        memset(s_dac, 0, sizeof(s_dac));
        memset(s_spk, 0, sizeof(s_spk));
        if (++s_lat_quiet >= (LAT_QUIET_MS * R5_FS / 1000) / N) {
            memcpy(s_dac, s_click, sizeof(s_click));   /* click at the start of this TX block */
            s_lat_pos = 0;
            s_lat_state = st = LAT_REC;
        }
    } else if (st == LAT_REC) {
        memset(s_dac, 0, sizeof(s_dac));
        memset(s_spk, 0, sizeof(s_spk));
    }
    if (st == LAT_REC) {
        /* reference: first sample of the RX block read in the click iteration */
        int n = s_lat_len - s_lat_pos;
        if (n > N) n = N;
        memcpy(&s_lat_buf[s_lat_pos], s_l, (size_t)n * sizeof(float));
        s_lat_pos += n;
        if (s_lat_pos >= s_lat_len) {
            s_lat_state = LAT_DONE;
            if (s_lat_waiter) xTaskNotifyGive(s_lat_waiter);
        }
    }
}

static void tone_step(void)
{
    int t = s_tone_target;
    if (!t) return;
    float *dst = (t == 1) ? s_dac : s_spk;
    float a = s_tone_amp, inc = s_tone_inc, ph = s_tone_ph;
    for (int i = 0; i < N; i++) {
        dst[i] = a * sinf(ph);
        ph += inc;
        if (ph > 6.28318531f) ph -= 6.28318531f;
    }
    s_tone_ph = ph;
}

/* ----------------------------------------------------------------- task */
static void audio_task(void *arg)
{
    const r5_engine_params_t *p0 = (const r5_engine_params_t *)arg;
    r5_engine_init(&s_eng, (float)R5_FS, p0);
    r5_click_make(s_click, LAT_CLICK_LEN, 0.7f);
    ESP_ERROR_CHECK(i2s_setup());
    s_st.period_us = (uint32_t)((uint64_t)N * 1000000ULL / R5_FS);
    xSemaphoreGive(s_ready);

    for (;;) {
        size_t got = 0;
        esp_err_t e = i2s_channel_read(s_rx0, s_rx, sizeof(s_rx), &got, 100);
        if (e != ESP_OK || got != sizeof(s_rx)) {
            s_st.rd_err++;
            continue;
        }
        int64_t t0 = esp_timer_get_time();

        for (int i = 0; i < N; i++) {
            s_l[i] = s2f(s_rx[2 * i]);
            s_r[i] = s2f(s_rx[2 * i + 1]);
        }
        meter();
        if (s_tuner_sb) xStreamBufferSend(s_tuner_sb, s_l, sizeof(s_l), 0);

        r5_engine_process(&s_eng, s_l, s_r, s_dac, s_spk, s_scr, N);
        if (s_lat_state != LAT_IDLE && s_lat_state != LAT_DONE) lat_step();
        tone_step();

        for (int i = 0; i < N; i++) {
            int32_t d = f2s32(s_dac[i]);          /* DAC: violin only, L = R */
            s_tx0b[2 * i] = d;
            s_tx0b[2 * i + 1] = d;
            i2s1_sample_t m = f2s1(s_spk[i]);     /* I2S1: mix, L = R */
            s_tx1b[2 * i] = m;
            s_tx1b[2 * i + 1] = m;
        }

        uint32_t us = (uint32_t)(esp_timer_get_time() - t0);
        s_st.proc_last_us = us;
        if (us > s_st.proc_max_us) s_st.proc_max_us = us;
        s_st.proc_avg_us += 0.01f * ((float)us - s_st.proc_avg_us);
        s_st.blocks++;

        size_t w;
        if (i2s_channel_write(s_tx0, s_tx0b, sizeof(s_tx0b), &w, 100) != ESP_OK) s_st.wr0_err++;
        /* I2S1 shares the clock, so a buffer frees every block; never stall the
         * codec loop for it (1 tick max), count a drop instead. */
        if (i2s_channel_write(s_tx1, s_tx1b, sizeof(s_tx1b), &w, 1) != ESP_OK) s_st.wr1_err++;
    }
}

esp_err_t audio_start(const r5_engine_params_t *initial)
{
    static r5_engine_params_t p0;
    p0 = *initial;
    s_ready = xSemaphoreCreateBinary();
    s_tuner_sb = xStreamBufferCreate(sizeof(float) * N * 32, sizeof(float) * N);
    BaseType_t ok = xTaskCreatePinnedToCore(audio_task, "audio", 6144, &p0,
                                            configMAX_PRIORITIES - 3, NULL, 1);
    if (ok != pdPASS) return ESP_ERR_NO_MEM;
    if (xSemaphoreTake(s_ready, pdMS_TO_TICKS(2000)) != pdTRUE) {
        ESP_LOGE(TAG, "I2S did not start");
        return ESP_ERR_TIMEOUT;
    }
    ESP_LOGI(TAG, "I2S running: 48 kHz, %d frames x %d DMA buffers, I2S1 %s", N, DESC, audio_i2s1_mode());
    return ESP_OK;
}

void audio_set_engine(const r5_engine_params_t *p) { r5_engine_set_params(&s_eng, p); }
void audio_get_engine(r5_engine_params_t *p) { r5_engine_get_params(&s_eng, p); }

void audio_get_stats(audio_stats_t *s)
{
    *s = s_st;
    s->rx_ovf = s_rx_ovf;
    s->tx0_ovf = s_tx0_ovf;
    s->tx1_ovf = s_tx1_ovf;
}

void audio_reset_stats(void)
{
    s_st.proc_max_us = 0;
    s_st.rd_err = s_st.wr0_err = s_st.wr1_err = 0;
    s_st.blocks = 0;
    s_rx_ovf = s_tx0_ovf = s_tx1_ovf = 0;
}

void audio_levels_snapshot(audio_levels_t *out)
{
    taskENTER_CRITICAL(&s_mux);
    uint32_t n = s_lev.frames;
    for (int c = 0; c < 2; c++) {
        out->peak[c] = s_lev.peak[c];
        out->rms[c] = n ? (float)sqrt(s_lev.sumsq[c] / n) : 0.0f;
        out->clips[c] = s_lev.clips[c];
    }
    out->frames = n;
    memset(&s_lev, 0, sizeof(s_lev));
    taskEXIT_CRITICAL(&s_mux);
}

esp_err_t audio_lat_measure(int *lag, float *snr, int rec_len)
{
    if (s_lat_state == LAT_QUIET || s_lat_state == LAT_REC) return ESP_ERR_INVALID_STATE;
    if (!s_lat_buf || s_lat_len != rec_len) {
        free(s_lat_buf);
        s_lat_buf = malloc(sizeof(float) * (size_t)rec_len);
        if (!s_lat_buf) return ESP_ERR_NO_MEM;
        s_lat_len = rec_len;
    }
    s_tone_target = 0;                 /* a test tone would hide the click */
    s_lat_waiter = xTaskGetCurrentTaskHandle();
    ulTaskNotifyTake(pdTRUE, 0);
    s_lat_quiet = 0;
    s_lat_state = LAT_QUIET;
    uint32_t to_ms = LAT_QUIET_MS + (uint32_t)rec_len * 1000u / R5_FS + 500u;
    if (!ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(to_ms))) {
        s_lat_state = LAT_IDLE;
        return ESP_ERR_TIMEOUT;
    }
    *lag = r5_click_detect(s_lat_buf, s_lat_len, s_click, LAT_CLICK_LEN, 8.0f, snr);
    s_lat_state = LAT_IDLE;
    return *lag >= 0 ? ESP_OK : ESP_ERR_NOT_FOUND;
}

void audio_tone(int target, float dbfs, float hz)
{
    s_tone_target = 0;
    if (target) {
        s_tone_amp = r5_db2lin(dbfs);
        s_tone_inc = 6.28318531f * hz / (float)R5_FS;
        s_tone_target = target;
    }
}

size_t audio_tuner_read(float *buf, size_t max, TickType_t to)
{
    return xStreamBufferReceive(s_tuner_sb, buf, max * sizeof(float), to) / sizeof(float);
}

int audio_block_frames(void) { return N; }
int audio_dma_desc(void) { return DESC; }
float audio_min_limiter_gain(void) { return s_eng.last_min_lim_gain; }

const char *audio_i2s1_mode(void)
{
#if CONFIG_R5_I2S1_CLK_SHARED_BCLK
    return "slave on I2S0 BCLK/WS pads (32-bit slots)";
#elif CONFIG_R5_I2S1_CLK_EXT_MCLK && CONFIG_R5_I2S1_16BIT
    return "master, ext clock = I2S0 MCLK pad (16-bit slots)";
#elif CONFIG_R5_I2S1_CLK_EXT_MCLK
    return "master, ext clock = I2S0 MCLK pad (32-bit slots)";
#elif CONFIG_R5_I2S1_16BIT
    return "master, PLL_F160M like I2S0 (16-bit slots)";
#else
    return "master, PLL_F160M like I2S0 (32-bit slots)";
#endif
}
