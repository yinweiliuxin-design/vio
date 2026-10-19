/* Console commands (esp_console REPL over USB-Serial-JTAG). Type `help`. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_console.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
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

#define LAT_REC_LEN 8192   /* 170 ms of ADC-L after the click */

/* ------------------------------------------------------------- helpers */
static bool parse_f(const char *s, float *out)
{
    char *end;
    float v = strtof(s, &end);
    if (end == s || *end) return false;
    *out = v;
    return true;
}

static bool parse_i(const char *s, long *out)
{
    char *end;
    long v = strtol(s, &end, 0);
    if (end == s || *end) return false;
    *out = v;
    return true;
}

/* side mask from "L" / "R" / "LR" */
static int parse_side(const char *s)
{
    if (!strcasecmp(s, "L")) return 1;
    if (!strcasecmp(s, "R")) return 2;
    if (!strcasecmp(s, "LR") || !strcasecmp(s, "both")) return 3;
    return 0;
}

static int usage(const char *u)
{
    printf("usage: %s\n", u);
    return 1;
}

static void print_plan(const r5_params_t *p)
{
    const r5_codec_t *c = codec_get();
    printf("wired plan (%s):\n", c->name);
    for (int s = 0; s < 2; s++) {
        printf("  %s: violin %+6.1f dB  accomp(bypass) %+6.1f dB  mix %+5.1f dB  bypass %s", s ? "R" : "L",
               p->plan.violin_db[s], p->plan.accomp_db[s], p->plan.mix_real_db[s],
               p->plan.mute[s] ? "MUTED" : "on");
        if (c->kind == R5_CODEC_ES8388) {
            printf("  [OUTVOL 0x%02x DACVOL 0x%02x BYPVOL code %u]\n", p->plan.es_outvol[s],
                   p->plan.es_dacvol[s], p->plan.es_byp_code[s]);
        } else {
            printf("  [HP/LO drv %+d dB, DAC vol %+.1f dB]\n", p->plan.aic_drv_db[s],
                   p->plan.aic_dac_halfdb[s] * 0.5f);
        }
    }
    printf("  I2S1 mono accompaniment gain %+.2f dB rel. violin (MIX %d%% -> %+.1f dB requested%s, cal %+.1f dB, PGA_R %.1f dB)\n",
           p->internal_accomp_db, p->mix_pct, p->mix_db, p->mix_mute ? ", MUTED" : "", p->mix_cal_db,
           p->pga_real_db[1]);
}

/* ------------------------------------------------------------ commands */
static int cmd_status(int argc, char **argv)
{
    r5_params_t p;
    params_get(&p);
    const r5_codec_t *c = codec_get();
    printf("codec: %s @0x%02x  %s\n", c->name, c->addr, codec_ok() ? "OK" : "NOT RESPONDING / not initialised");
    printf("  inputs : %s\n  limits : %s\n", c->input_map, c->limits);
    printf("audio: 48 kHz, block %d frames (%.2f ms), %d DMA buffers; I2S1 %s\n", audio_block_frames(),
           audio_block_frames() * 1000.0f / R5_FS, audio_dma_desc(), audio_i2s1_mode());
    printf("vol %d%% (wired %.1f dB, spk %.1f dB)  dac trim %.1f dB  pickup gain %.1f dB\n", p.vol_pct, p.wired_db,
           p.spk_db, p.dac_trim_db, p.pickup_gain_db);
    printf("PGA L %.1f dB (asked %.1f)  PGA R %.1f dB (asked %.1f)\n", p.pga_real_db[0], p.pga_db[0], p.pga_real_db[1],
           p.pga_db[1]);
    printf("tone %d%% (bass %+.1f dB @200 Hz, treble %+.1f dB @3 kHz)  fx %s depth %d%%\n", p.tone_pct, p.bass_db,
           p.treble_db, p.fx_on ? "on" : "off", p.fx_pct);
    printf("bypass side trims L %+.1f R %+.1f dB, user mutes L %d R %d\n", p.side_trim_db[0], p.side_trim_db[1],
           p.byp_mute[0], p.byp_mute[1]);
    print_plan(&p);
    printf("output %s%s; speaker limit %.2f W into %.1f ohm, Vrms@0dBFS %.2f V -> ceiling %.3f (%.2f dBFS) %s\n",
           params_out_name(p.out), p.standby ? " (STANDBY)" : "", p.spk_limit_w, p.spk_ohm, p.spk_vrms_fs,
           p.spk_ceiling, r5_lin2db(p.spk_ceiling), p.spk_limit_on ? "on" : "OFF");
    printf("tuner %s\n", tuner_enabled() ? "running" : "stopped");
    ble_status_print();
    return 0;
}

static int cmd_codec(int argc, char **argv)
{
    if (argc == 3 && !strcmp(argv[1], "use")) {
        if (strcmp(argv[2], "aic") && strcmp(argv[2], "es") && strcmp(argv[2], "default")) {
            return usage("codec use aic|es|default");
        }
        esp_err_t e = codec_set_override(argv[2]);
        if (e != ESP_OK) {
            printf("failed: %s (runtime switch enabled in menuconfig?)\n", esp_err_to_name(e));
            return 1;
        }
        printf("stored; rebooting...\n");
        vTaskDelay(pdMS_TO_TICKS(200));
        esp_restart();
    }
    const r5_codec_t *c = codec_get();
    printf("%s @0x%02x %s\n", c->name, c->addr, codec_ok() ? "OK" : "not responding");
    printf("probe TLV320AIC3204 @0x%02x: %s\n", CONFIG_R5_AIC_I2C_ADDR,
           r5_i2c_probe(CONFIG_R5_AIC_I2C_ADDR) == ESP_OK ? "ACK" : "no ACK");
    printf("probe ES8388       @0x%02x: %s\n", CONFIG_R5_ES_I2C_ADDR,
           r5_i2c_probe(CONFIG_R5_ES_I2C_ADDR) == ESP_OK ? "ACK" : "no ACK");
    return 0;
}

static int cmd_i2cscan(int argc, char **argv)
{
    r5_i2c_scan();
    return 0;
}

/* AIC: "page:reg" or page*128+reg; ES: plain register number */
static bool parse_reg(const char *s, uint16_t *addr)
{
    const char *colon = strchr(s, ':');
    if (colon) {
        long pg, rg;
        char tmp[8];
        size_t n = (size_t)(colon - s);
        if (n == 0 || n >= sizeof tmp) return false;
        memcpy(tmp, s, n);
        tmp[n] = 0;
        if (!parse_i(tmp, &pg) || !parse_i(colon + 1, &rg) || pg < 0 || pg > 255 || rg < 0 || rg > 127) return false;
        *addr = (uint16_t)(pg * 128 + rg);
        return true;
    }
    long v;
    if (!parse_i(s, &v) || v < 0 || v > 0x7FFF) return false;
    *addr = (uint16_t)v;
    return true;
}

static int cmd_reg(int argc, char **argv)
{
    const r5_codec_t *c = codec_get();
    if (argc == 2 && !strcmp(argv[1], "dump")) {
        c->dump();
        return 0;
    }
    uint16_t a;
    if (argc == 3 && !strcmp(argv[1], "r") && parse_reg(argv[2], &a)) {
        uint8_t v = 0;
        esp_err_t e = c->reg_read(a, &v);
        if (e != ESP_OK) {
            printf("read failed: %s\n", esp_err_to_name(e));
            return 1;
        }
        if (c->kind == R5_CODEC_AIC3204) printf("P%u R%u = 0x%02x (%u)\n", a / 128, a % 128, v, v);
        else printf("0x%02x = 0x%02x (%u)\n", a, v, v);
        return 0;
    }
    long v;
    if (argc == 4 && !strcmp(argv[1], "w") && parse_reg(argv[2], &a) && parse_i(argv[3], &v) && v >= 0 && v <= 255) {
        esp_err_t e = c->reg_write(a, (uint8_t)v);
        printf("%s\n", e == ESP_OK ? "ok (note: next parameter change may overwrite it)" : esp_err_to_name(e));
        return e == ESP_OK ? 0 : 1;
    }
    return usage("reg r <addr> | reg w <addr> <val> | reg dump   (AIC addr: page:reg, e.g. 1:12)");
}

static int cmd_pga(int argc, char **argv)
{
    float db;
    int side = argc == 3 ? parse_side(argv[1]) : 0;
    if (!side || !parse_f(argv[2], &db)) return usage("pga L|R|LR <dB>   (ES8388 0..24/3dB, AIC3204 0..47.5/0.5dB)");
    r5_params_t *p = params_lock();
    if (side & 1) p->pga_db[0] = db;
    if (side & 2) p->pga_db[1] = db;
    params_unlock(true);
    r5_params_t q;
    params_get(&q);
    printf("PGA L %.1f dB, R %.1f dB (realised)\n", q.pga_real_db[0], q.pga_real_db[1]);
    return 0;
}

static int cmd_byp(int argc, char **argv)
{
    if (argc == 4 && !strcmp(argv[1], "mute")) {
        int side = parse_side(argv[2]);
        long m;
        if (!side || !parse_i(argv[3], &m)) return usage("byp mute L|R|LR 0|1");
        r5_params_t *p = params_lock();
        if (side & 1) p->byp_mute[0] = m != 0;
        if (side & 2) p->byp_mute[1] = m != 0;
        params_unlock(true);
    } else if (argc == 3) {
        int side = parse_side(argv[1]);
        float db;
        if (!side || !parse_f(argv[2], &db)) return usage("byp L|R|LR <trim dB> | byp mute L|R|LR 0|1");
        r5_params_t *p = params_lock();
        if (side & 1) p->side_trim_db[0] = db;
        if (side & 2) p->side_trim_db[1] = db;
        params_unlock(true);
    } else if (argc != 1) {
        return usage("byp L|R|LR <trim dB> | byp mute L|R|LR 0|1");
    }
    r5_params_t q;
    params_get(&q);
    print_plan(&q);
    return 0;
}

static int cmd_dac(int argc, char **argv)
{
    float db;
    if (argc != 2 || !parse_f(argv[1], &db)) return usage("dac <violin trim dB>");
    r5_params_t *p = params_lock();
    p->dac_trim_db = db;
    params_unlock(true);
    r5_params_t q;
    params_get(&q);
    print_plan(&q);
    return 0;
}

static int cmd_hp(int argc, char **argv)
{
    float db;
    if (argc != 2 || !parse_f(argv[1], &db)) return usage("hp <wired master dB>");
    r5_params_t *p = params_lock();
    p->wired_db = db;
    params_unlock(true);
    r5_params_t q;
    params_get(&q);
    print_plan(&q);
    return 0;
}

static int cmd_vol(int argc, char **argv)
{
    long v;
    if (argc != 2 || !parse_i(argv[1], &v) || v < 0 || v > 100) return usage("vol <0..100>");
    r5_params_t *p = params_lock();
    p->vol_pct = (int)v;
    p->wired_db = p->spk_db = params_vol_db((int)v);
    params_unlock(true);
    printf("vol %ld%% = %.1f dB (wired and speaker/BT)\n", v, params_vol_db((int)v));
    return 0;
}

static int cmd_mix(int argc, char **argv)
{
    float db;
    long v;
    if (argc == 3 && !strcmp(argv[1], "trim") && parse_f(argv[2], &db)) {
        r5_params_t *p = params_lock();
        p->mix_cal_db = db;
        params_unlock(true);
    } else if (argc == 2 && parse_i(argv[1], &v) && v >= 0 && v <= 100) {
        r5_params_t *p = params_lock();
        p->mix_pct = (int)v;
        params_unlock(true);
    } else if (argc != 1) {
        return usage("mix <0..100> | mix trim <dB>");
    }
    r5_params_t q;
    params_get(&q);
    print_plan(&q);
    return 0;
}

static int cmd_gain(int argc, char **argv)
{
    float db;
    if (argc != 2 || !parse_f(argv[1], &db)) return usage("gain <pickup digital gain dB>");
    r5_params_t *p = params_lock();
    p->pickup_gain_db = db;
    params_unlock(true);
    return 0;
}

static int cmd_tone(int argc, char **argv)
{
    float b, t;
    long v;
    if (argc == 3 && !strcmp(argv[1], "tilt") && parse_i(argv[2], &v)) {
        r5_params_t *p = params_lock();
        params_set_tone_pct(p, (int)v);
        params_unlock(true);
    } else if (argc == 3 && parse_f(argv[1], &b) && parse_f(argv[2], &t)) {
        r5_params_t *p = params_lock();
        p->bass_db = b;
        p->treble_db = t;
        params_unlock(true);
    } else {
        return usage("tone <bass dB> <treble dB> | tone tilt <0..100>");
    }
    return 0;
}

static int cmd_fx(int argc, char **argv)
{
    long v;
    r5_params_t *p = params_lock();
    if (argc == 2 && !strcmp(argv[1], "on")) p->fx_on = true;
    else if (argc == 2 && !strcmp(argv[1], "off")) p->fx_on = false;
    else if (argc == 2 && parse_i(argv[1], &v) && v >= 0 && v <= 100) p->fx_pct = (int)v;
    else {
        params_unlock(false);
        return usage("fx <0..100> | fx on|off");
    }
    params_unlock(true);
    return 0;
}

static int cmd_out(int argc, char **argv)
{
    r5_out_t o;
    if (argc != 2) return usage("out hp|spk|bt|all");
    if (!strcmp(argv[1], "hp")) o = R5_OUT_HP;
    else if (!strcmp(argv[1], "spk")) o = R5_OUT_SPK;
    else if (!strcmp(argv[1], "bt")) o = R5_OUT_BT;
    else if (!strcmp(argv[1], "all")) o = R5_OUT_SPK_BT;
    else return usage("out hp|spk|bt|all");
    r5_params_t *p = params_lock();
    p->out = o;
    params_unlock(true);
    printf("output: %s\n", params_out_name(o));
    return 0;
}

static int cmd_standby(int argc, char **argv)
{
    if (argc != 2) return usage("standby on|off");
    r5_params_t *p = params_lock();
    p->standby = !strcmp(argv[1], "on");
    params_unlock(true);
    return 0;
}

static int cmd_spk(int argc, char **argv)
{
    float v;
    r5_params_t q;
    if (argc >= 2 && !strcmp(argv[1], "tone")) {
        if (argc >= 3 && !strcmp(argv[2], "off")) {
            audio_tone(0, 0, 0);
            printf("tone off\n");
            return 0;
        }
        float dbfs, hz = 1000.0f;
        if (argc < 3 || !parse_f(argv[2], &dbfs) || (argc == 4 && !parse_f(argv[3], &hz))) {
            return usage("spk tone <dBFS> [Hz] | spk tone off");
        }
        params_get(&q);
        float amp = r5_db2lin(dbfs);
        if (q.spk_limit_on && amp > q.spk_ceiling) {
            dbfs = r5_lin2db(q.spk_ceiling);
            amp = q.spk_ceiling;
            printf("clamped to the speaker ceiling (%.2f dBFS)\n", dbfs);
        }
        audio_tone(2, dbfs, hz);
        float vr = amp * q.spk_vrms_fs;
        printf("I2S1 sine %.1f Hz at %.2f dBFS. Expected %.3f Vrms / %.3f W into %.1f ohm (with Vrms@0dBFS=%.2f V)\n",
               hz, dbfs, vr, vr * vr / q.spk_ohm, q.spk_ohm, q.spk_vrms_fs);
        printf("Measure Vrms across the speaker, then: spk cal <measured Vrms> %.1f\n", dbfs);
        return 0;
    }
    r5_params_t *p = params_lock();
    bool changed = true;
    if (argc == 3 && !strcmp(argv[1], "limit") && !strcmp(argv[2], "on")) p->spk_limit_on = true;
    else if (argc == 3 && !strcmp(argv[1], "limit") && !strcmp(argv[2], "off")) p->spk_limit_on = false;
    else if (argc == 3 && !strcmp(argv[1], "limit") && parse_f(argv[2], &v) && v > 0) p->spk_limit_w = v;
    else if (argc == 3 && !strcmp(argv[1], "ohm") && parse_f(argv[2], &v) && v > 0) p->spk_ohm = v;
    else if ((argc == 3 || argc == 4) && !strcmp(argv[1], "cal") && parse_f(argv[2], &v) && v > 0) {
        float at = -20.0f;
        if (argc == 4 && !parse_f(argv[3], &at)) {
            params_unlock(false);
            return usage("spk cal <measured Vrms> [tone dBFS, default -20]");
        }
        p->spk_vrms_fs = v / r5_db2lin(at);
    } else if (argc == 1 || (argc == 2 && !strcmp(argv[1], "show"))) changed = false;
    else {
        params_unlock(false);
        return usage("spk [show] | spk limit <W>|on|off | spk ohm <R> | spk cal <Vrms> [dBFS] | spk tone <dBFS>|off [Hz]");
    }
    params_unlock(changed);
    params_get(&q);
    printf("speaker: limit %.2f W %s, %.1f ohm, Vrms@0dBFS %.3f V -> ceiling %.4f (%.2f dBFS); min limiter gain %.3f\n",
           q.spk_limit_w, q.spk_limit_on ? "on" : "OFF", q.spk_ohm, q.spk_vrms_fs, q.spk_ceiling,
           r5_lin2db(q.spk_ceiling), audio_min_limiter_gain());
    if (changed) printf("(use `save` to keep the calibration)\n");
    return 0;
}

static int cmd_dactone(int argc, char **argv)
{
    float dbfs, hz = 1000.0f;
    if (argc == 2 && !strcmp(argv[1], "off")) {
        audio_tone(0, 0, 0);
        return 0;
    }
    if (argc < 2 || !parse_f(argv[1], &dbfs) || (argc == 3 && !parse_f(argv[2], &hz))) {
        return usage("dactone <dBFS> [Hz] | dactone off   (replaces the violin on the DAC)");
    }
    audio_tone(1, dbfs, hz);
    return 0;
}

static int cmd_tuner(int argc, char **argv)
{
    long s = 10;
    if (argc >= 2 && !strcmp(argv[1], "on")) tuner_enable(true);
    else if (argc >= 2 && !strcmp(argv[1], "off")) tuner_enable(false);
    else if (argc >= 2 && !strcmp(argv[1], "show")) {
        if (argc == 3 && !parse_i(argv[2], &s)) return usage("tuner show [seconds]");
        tuner_enable(true);
        tuner_show((int)s);
    } else return usage("tuner on|off|show [seconds]");
    return 0;
}

static int cmd_level(int argc, char **argv)
{
    long sec = 5;
    if (argc == 2 && (!parse_i(argv[1], &sec) || sec < 1)) return usage("level [seconds]");
    audio_levels_t lv;
    audio_levels_snapshot(&lv);    /* reset */
    float maxpk[2] = {0, 0};
    uint32_t clips[2] = {0, 0};
    int steps = (int)(sec * 4);
    printf("ADC-L = pickup, ADC-R = AUX mono. dBFS, 250 ms windows\n");
    for (int i = 0; i < steps; i++) {
        vTaskDelay(pdMS_TO_TICKS(250));
        audio_levels_snapshot(&lv);
        for (int c = 0; c < 2; c++) {
            if (lv.peak[c] > maxpk[c]) maxpk[c] = lv.peak[c];
            clips[c] += lv.clips[c];
        }
        printf("L pk %6.1f rms %6.1f | R pk %6.1f rms %6.1f %s%s\n", r5_lin2db(lv.peak[0]), r5_lin2db(lv.rms[0]),
               r5_lin2db(lv.peak[1]), r5_lin2db(lv.rms[1]), lv.clips[0] ? " CLIP-L" : "", lv.clips[1] ? " CLIP-R" : "");
    }
    printf("max peak L %.1f dBFS, R %.1f dBFS; clipped samples L %lu, R %lu\n", r5_lin2db(maxpk[0]),
           r5_lin2db(maxpk[1]), (unsigned long)clips[0], (unsigned long)clips[1]);
    return 0;
}

static int cmd_load(int argc, char **argv)
{
    long sec = 5;
    if (argc == 2 && (!parse_i(argv[1], &sec) || sec < 1)) return usage("load [seconds]  (e.g. load 3600)");
    audio_stats_t st;
    audio_reset_stats();
    float max_core[2] = {0, 0}, sum_core[2] = {0, 0};
    int windows = 0;
    long left = sec;
    printf("measuring %ld s; window = min(10 s, rest); limit 70%% per core\n", sec);
    while (left > 0) {
        long w = left > 10 ? 10 : left;
        int64_t t0 = esp_timer_get_time();
        configRUN_TIME_COUNTER_TYPE i0 = ulTaskGetIdleRunTimeCounterForCore(0);
        configRUN_TIME_COUNTER_TYPE i1 = ulTaskGetIdleRunTimeCounterForCore(1);
        vTaskDelay(pdMS_TO_TICKS(w * 1000));
        int64_t dt = esp_timer_get_time() - t0;
        configRUN_TIME_COUNTER_TYPE j0 = ulTaskGetIdleRunTimeCounterForCore(0);
        configRUN_TIME_COUNTER_TYPE j1 = ulTaskGetIdleRunTimeCounterForCore(1);
        float u0 = 100.0f * (1.0f - (float)(j0 - i0) / (float)dt);
        float u1 = 100.0f * (1.0f - (float)(j1 - i1) / (float)dt);
        for (int c = 0; c < 2; c++) {
            float u = c ? u1 : u0;
            if (u > max_core[c]) max_core[c] = u;
            sum_core[c] += u;
        }
        windows++;
        left -= w;
        audio_get_stats(&st);
        printf("[%5ld s] core0 %5.1f%%  core1 %5.1f%%  audio avg %4.0f us max %4lu us / %lu us  "
               "drop rx %lu tx0 %lu tx1 %lu err %lu/%lu/%lu\n",
               sec - left, u0, u1, st.proc_avg_us, (unsigned long)st.proc_max_us, (unsigned long)st.period_us,
               (unsigned long)st.rx_ovf, (unsigned long)st.tx0_ovf, (unsigned long)st.tx1_ovf,
               (unsigned long)st.rd_err, (unsigned long)st.wr0_err, (unsigned long)st.wr1_err);
    }
    audio_get_stats(&st);
    uint32_t drops = st.rx_ovf + st.tx0_ovf + st.tx1_ovf + st.rd_err + st.wr0_err + st.wr1_err;
    printf("---- summary over %ld s (%lu blocks)\n", sec, (unsigned long)st.blocks);
    for (int c = 0; c < 2; c++) {
        printf("core%d: avg %.1f%%  max window %.1f%%  -> %s (limit 70%%)\n", c, sum_core[c] / windows, max_core[c],
               max_core[c] <= 70.0f ? "PASS" : "FAIL");
    }
    printf("audio task: max %lu us = %.0f%% of the %lu us block period (avg %.0f us)\n",
           (unsigned long)st.proc_max_us, 100.0f * st.proc_max_us / st.period_us, (unsigned long)st.period_us,
           st.proc_avg_us);
    printf("dropouts/underruns: %lu -> %s\n", (unsigned long)drops, drops ? "FAIL" : "PASS");

    /* per-task share since boot (FreeRTOS run-time stats) */
    UBaseType_t n = uxTaskGetNumberOfTasks();
    TaskStatus_t *ts = malloc(sizeof(TaskStatus_t) * (n + 4));
    if (ts) {
        configRUN_TIME_COUNTER_TYPE total;
        n = uxTaskGetSystemState(ts, n + 4, &total);
        printf("tasks since boot (run time share of one core):\n");
        for (UBaseType_t i = 0; i < n; i++) {
            float pct = total ? 100.0f * (float)ts[i].ulRunTimeCounter / (float)total : 0;
            if (pct >= 0.5f) {
                printf("  %-16s core %2d prio %2u  %5.1f%%\n", ts[i].pcTaskName,
                       ts[i].xCoreID == tskNO_AFFINITY ? -1 : (int)ts[i].xCoreID, (unsigned)ts[i].uxCurrentPriority,
                       pct);
            }
        }
        free(ts);
    }
    return 0;
}

static int cmd_lat(int argc, char **argv)
{
    long n = 5;
    if (argc == 2 && (!parse_i(argv[1], &n) || n < 1 || n > 50)) return usage("lat [repeats]");
    int N = audio_block_frames(), D = audio_dma_desc();
    printf("Patch HEADPHONE OUT (left) -> PICKUP IN with a cable. Bypass and speaker are muted during the test.\n");
    r5_params_t *p = params_lock();
    p->test_mute = true;
    params_unlock(true);
    vTaskDelay(pdMS_TO_TICKS(100));
    float mn = 1e9f, mx = 0, sum = 0;
    int ok = 0;
    for (int i = 0; i < n; i++) {
        int lag = -1;
        float snr = 0;
        esp_err_t e = audio_lat_measure(&lag, &snr, LAT_REC_LEN);
        if (e == ESP_OK) {
            float ms = lag * 1000.0f / R5_FS;
            printf("  #%d: %d samples = %.3f ms (snr %.0f)\n", i + 1, lag, ms, snr);
            if (ms < mn) mn = ms;
            if (ms > mx) mx = ms;
            sum += ms;
            ok++;
        } else {
            printf("  #%d: no click found (%s, snr %.1f) - check cable / volume / PGA\n", i + 1, esp_err_to_name(e),
                   snr);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    p = params_lock();
    p->test_mute = false;
    params_unlock(true);
    float blk = N * 1000.0f / R5_FS;
    printf("theoretical buffering: RX 1 block + TX ring %d..%d blocks of %d frames = %.2f..%.2f ms "
           "(+ processing jitter; codec ADC/DAC filter delay not included)\n",
           D - 1, D, N, blk * D, blk * (D + 1));
    if (ok) {
        printf("measured round trip: min %.3f  avg %.3f  max %.3f ms  -> %s (limit 10 ms)\n", mn, sum / ok, mx,
               mx <= 10.0f ? "PASS" : "FAIL");
    }
    return ok ? 0 : 1;
}

static int cmd_bt(int argc, char **argv)
{
    char line[200];
    line[0] = 0;
    if (argc >= 3 && (!strcmp(argv[1], "send") || !strcmp(argv[1], "nocr") || !strcmp(argv[1], "btn"))) {
        for (int i = 2; i < argc; i++) {
            strlcat(line, argv[i], sizeof line);
            if (i + 1 < argc) strlcat(line, " ", sizeof line);
        }
        if (!strcmp(argv[1], "btn")) {
            esp_err_t e = btmod_set_button_cmd(strcmp(line, "none") ? line : "");
            printf("BT button command: \"%s\" %s\n", btmod_button_cmd(), e == ESP_OK ? "(saved)" : "(NVS error)");
            return 0;
        }
        return btmod_send(line, !strcmp(argv[1], "send")) == ESP_OK ? 0 : 1;
    }
    if (argc >= 3 && !strcmp(argv[1], "hex")) {
        uint8_t buf[64];
        int k = 0;
        for (int i = 2; i < argc && k < (int)sizeof buf; i++) {
            long v;
            char tmp[8];
            snprintf(tmp, sizeof tmp, "0x%s", argv[i]);
            if (!parse_i(tmp, &v) || v < 0 || v > 255) return usage("bt hex 41 54 0d 0a");
            buf[k++] = (uint8_t)v;
        }
        return btmod_send_raw(buf, (size_t)k) == ESP_OK ? 0 : 1;
    }
    long v;
    if (argc == 3 && !strcmp(argv[1], "baud") && parse_i(argv[2], &v) && v > 0) {
        return btmod_set_baud((int)v) == ESP_OK ? 0 : 1;
    }
    if (argc == 3 && !strcmp(argv[1], "echo")) {
        btmod_set_echo(!strcmp(argv[2], "on"));
        return 0;
    }
    return usage("bt send <text> (adds CR LF) | bt nocr <text> | bt hex <bytes> | bt baud <n> | "
                 "bt echo on|off | bt btn <text>|none");
}

static int cmd_ble(int argc, char **argv)
{
    ble_status_print();
    return 0;
}

static int cmd_ui(int argc, char **argv)
{
    ui_print_state();
    return 0;
}

static int cmd_save(int argc, char **argv)
{
    esp_err_t e = params_save();
    printf("%s\n", e == ESP_OK ? "saved (speaker calibration, mix trim, PGA, pickup gain)" : esp_err_to_name(e));
    return 0;
}

static const esp_console_cmd_t k_cmds[] = {
    {.command = "status", .help = "Show codec, routing plan, levels, speaker limit, BLE", .func = cmd_status},
    {.command = "codec", .help = "codec | codec use aic|es|default (stored in NVS, reboots)", .func = cmd_codec},
    {.command = "i2cscan", .help = "Scan the I2C bus", .func = cmd_i2cscan},
    {.command = "reg", .help = "reg r <addr> | reg w <addr> <val> | reg dump  (AIC3204 addr page:reg)", .func = cmd_reg},
    {.command = "pga", .help = "pga L|R|LR <dB>  codec ADC analog gain", .func = cmd_pga},
    {.command = "byp", .help = "byp L|R|LR <trim dB> | byp mute L|R|LR 0|1  accompaniment analog bypass", .func = cmd_byp},
    {.command = "dac", .help = "dac <dB>  violin trim on the wired outputs", .func = cmd_dac},
    {.command = "hp", .help = "hp <dB>  wired (HP/LINE) master", .func = cmd_hp},
    {.command = "vol", .help = "vol <0..100>  master (wired + speaker/BT)", .func = cmd_vol},
    {.command = "mix", .help = "mix <0..100> | mix trim <dB>  moves codec bypass AND I2S1 accompaniment", .func = cmd_mix},
    {.command = "gain", .help = "gain <dB>  pickup digital gain", .func = cmd_gain},
    {.command = "tone", .help = "tone <bass dB> <treble dB> | tone tilt <0..100>", .func = cmd_tone},
    {.command = "fx", .help = "fx <0..100> | fx on|off  reverb depth", .func = cmd_fx},
    {.command = "out", .help = "out hp|spk|bt|all", .func = cmd_out},
    {.command = "standby", .help = "standby on|off", .func = cmd_standby},
    {.command = "spk", .help = "spk [show] | limit <W>|on|off | ohm <R> | cal <Vrms> [dBFS] | tone <dBFS>|off [Hz]", .func = cmd_spk},
    {.command = "dactone", .help = "dactone <dBFS> [Hz] | off  test sine on the DAC (wired outputs)", .func = cmd_dactone},
    {.command = "tuner", .help = "tuner on|off|show [s]", .func = cmd_tuner},
    {.command = "level", .help = "level [s]  ADC-L/ADC-R peak/RMS dBFS, clip", .func = cmd_level},
    {.command = "load", .help = "load [s]  per-core CPU, audio block time, dropouts", .func = cmd_load},
    {.command = "lat", .help = "lat [n]  round-trip latency with HP->pickup cable", .func = cmd_lat},
    {.command = "bt", .help = "bt send|nocr|hex|baud|echo|btn ...  BT TX module UART", .func = cmd_bt},
    {.command = "ble", .help = "BLE status", .func = cmd_ble},
    {.command = "ui", .help = "Encoder counts and button levels", .func = cmd_ui},
    {.command = "save", .help = "Save calibration to NVS", .func = cmd_save},
};

esp_err_t console_start(void)
{
    esp_console_repl_t *repl = NULL;
    esp_console_repl_config_t rc = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    rc.prompt = "r5> ";
    rc.max_cmdline_length = 256;
    rc.task_stack_size = 8192;
    esp_console_dev_usb_serial_jtag_config_t hw = ESP_CONSOLE_DEV_USB_SERIAL_JTAG_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_console_new_repl_usb_serial_jtag(&hw, &rc, &repl));
    esp_console_register_help_command();
    for (size_t i = 0; i < sizeof(k_cmds) / sizeof(k_cmds[0]); i++) {
        ESP_ERROR_CHECK(esp_console_cmd_register(&k_cmds[i]));
    }
    return esp_console_start_repl(repl);
}
