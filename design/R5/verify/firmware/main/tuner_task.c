#include <math.h>
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "audio.h"
#include "r5dsp.h"
#include "tuner_task.h"

#define W      512                       /* 42.7 ms at 12 kHz */
#define TMIN   5                         /* 2.4 kHz */
#define TMAX   92                        /* 130 Hz */
#define LEN    R5_YIN_LEN(W, TMAX)
#define HOP    256                       /* new estimate every 21 ms */

static volatile bool s_run = true;
static volatile int64_t s_show_until;
static r5_decim4_t s_dec;
static float s_buf[LEN];
static float s_scr[R5_YIN_SCRATCH(W, TMAX)];

static void tuner_task(void *arg)
{
    float in[256], out[64 + 4];
    int fill = 0, since = 0;
    int64_t last_print = 0;
    r5_decim4_init(&s_dec, (float)R5_FS);
    for (;;) {
        size_t n = audio_tuner_read(in, 256, pdMS_TO_TICKS(100));
        if (!n || !s_run) continue;
        int nd = r5_decim4_process(&s_dec, in, (int)n, out);
        if (fill + nd > LEN) {
            int drop = fill + nd - LEN;
            memmove(s_buf, s_buf + drop, (size_t)(fill - drop) * sizeof(float));
            fill -= drop;
        }
        memcpy(s_buf + fill, out, (size_t)nd * sizeof(float));
        fill += nd;
        since += nd;
        if (fill < LEN || since < HOP) continue;
        since = 0;

        double ss = 0;
        for (int i = LEN - W; i < LEN; i++) ss += (double)s_buf[i] * s_buf[i];
        float rms_db = r5_lin2db((float)sqrt(ss / W));
        r5_pitch_t p = {0};
        bool voiced = rms_db > -60.0f && r5_yin(s_buf, W, TMIN, TMAX, 0.15f, R5_FS / 4.0f, s_scr, &p);

        int64_t now = esp_timer_get_time();
        if (now < s_show_until && now - last_print > 250000) {
            last_print = now;
            if (voiced) {
                int midi;
                float cents;
                char nb[8];
                r5_note_from_freq(p.f0, 440.0f, &midi, &cents);
                printf("tuner: %-4s %+6.1f cents  (%.2f Hz, level %.0f dBFS, aperiodicity %.2f)\n",
                       r5_note_name(midi, nb, sizeof nb), cents, p.f0, rms_db, p.aperiodicity);
            } else {
                printf("tuner: --   (level %.0f dBFS)\n", rms_db);
            }
        }
    }
}

esp_err_t tuner_start(void)
{
    return xTaskCreatePinnedToCore(tuner_task, "tuner", 4096, NULL, 3, NULL, 0) == pdPASS ? ESP_OK : ESP_FAIL;
}

void tuner_enable(bool on) { s_run = on; }
bool tuner_enabled(void) { return s_run; }
void tuner_show(int seconds) { s_show_until = esp_timer_get_time() + (int64_t)seconds * 1000000; }
