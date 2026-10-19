/*
 * Host-side unit tests for the r5dsp library (no ESP-IDF needed).
 * Build and run: tests/run_host_tests.sh
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "r5dsp.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static int g_fail = 0, g_pass = 0;

#define CHECK(cond, ...)                                              \
    do {                                                              \
        if (cond) {                                                   \
            g_pass++;                                                 \
        } else {                                                      \
            g_fail++;                                                 \
            printf("  FAIL %s:%d: ", __FILE__, __LINE__);             \
            printf(__VA_ARGS__);                                      \
            printf("\n");                                             \
        }                                                             \
    } while (0)

#define NEAR(a, b, tol) (fabs((double)(a) - (double)(b)) <= (double)(tol))

static const float FS = 48000.0f;

/* deterministic pseudo-random gaussian (LCG + Box-Muller) */
static unsigned long long g_lcg = 0x12345678ULL;
static double urand(void)
{
    g_lcg = g_lcg * 6364136223846793005ULL + 1442695040888963407ULL;
    return ((g_lcg >> 11) + 0.5) / 9007199254740992.0;
}
static double grand(void)
{
    double u1 = urand(), u2 = urand();
    return sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
}

static double rms(const float *x, int n)
{
    double s = 0;
    for (int i = 0; i < n; i++) s += (double)x[i] * x[i];
    return sqrt(s / n);
}

static float maxabs(const float *x, int n)
{
    float m = 0;
    for (int i = 0; i < n; i++) if (fabsf(x[i]) > m) m = fabsf(x[i]);
    return m;
}

/* ------------------------------------------------------------ biquad */
static void test_biquad(void)
{
    printf("[biquad] RBJ shelving coefficients\n");
    r5_bq_coef_t c;

    r5_bq_lowshelf(&c, FS, 200.0f, 6.0f, 0.9f);
    float dc = r5_bq_mag_db(&c, FS, 0.01f), ny = r5_bq_mag_db(&c, FS, 23999.0f), mid = r5_bq_mag_db(&c, FS, 200.0f);
    printf("  lowshelf +6dB@200Hz: DC %.3f dB, f0 %.3f dB, Nyq %.3f dB\n", dc, mid, ny);
    CHECK(NEAR(dc, 6.0, 0.01), "lowshelf DC %.4f", dc);
    CHECK(NEAR(ny, 0.0, 0.01), "lowshelf Nyquist %.4f", ny);
    CHECK(NEAR(mid, 3.0, 0.05), "lowshelf f0 %.4f (expect half gain)", mid);

    r5_bq_lowshelf(&c, FS, 200.0f, -9.0f, 0.9f);
    dc = r5_bq_mag_db(&c, FS, 0.01f);
    mid = r5_bq_mag_db(&c, FS, 200.0f);
    CHECK(NEAR(dc, -9.0, 0.01), "lowshelf -9 DC %.4f", dc);
    CHECK(NEAR(mid, -4.5, 0.05), "lowshelf -9 f0 %.4f", mid);

    r5_bq_highshelf(&c, FS, 3000.0f, 8.0f, 0.9f);
    dc = r5_bq_mag_db(&c, FS, 0.01f);
    ny = r5_bq_mag_db(&c, FS, 23999.0f);
    mid = r5_bq_mag_db(&c, FS, 3000.0f);
    printf("  highshelf +8dB@3kHz: DC %.3f dB, f0 %.3f dB, Nyq %.3f dB\n", dc, mid, ny);
    CHECK(NEAR(dc, 0.0, 0.01), "highshelf DC %.4f", dc);
    CHECK(NEAR(ny, 8.0, 0.02), "highshelf Nyquist %.4f", ny);
    CHECK(NEAR(mid, 4.0, 0.05), "highshelf f0 %.4f", mid);

    r5_bq_highshelf(&c, FS, 3000.0f, 0.0f, 0.9f);
    CHECK(NEAR(r5_bq_mag_db(&c, FS, 1000.0f), 0.0, 1e-4) && NEAR(c.b0, 1.0, 1e-6),
          "0 dB shelf must be identity (b0=%f)", c.b0);

    r5_bq_peaking(&c, FS, 1000.0f, 5.0f, 1.0f);
    CHECK(NEAR(r5_bq_mag_db(&c, FS, 1000.0f), 5.0, 0.01), "peaking centre gain");

    /* time-domain check of the processing routine against the analytic response */
    r5_bq_t bq;
    r5_bq_lowshelf(&bq.c, FS, 200.0f, 6.0f, 0.9f);
    r5_bq_reset(&bq);
    enum { N = 48000 };
    static float in[N], out[N];
    const float f = 100.0f;
    for (int i = 0; i < N; i++) in[i] = 0.25f * sinf(2.0f * (float)M_PI * f * i / FS);
    for (int i = 0; i < N; i += 64) r5_bq_process(&bq, in + i, out + i, 64);
    double g = 20.0 * log10(rms(out + N / 2, N / 2) / rms(in + N / 2, N / 2));
    double ga = r5_bq_mag_db(&bq.c, FS, f);
    printf("  process(): 100 Hz gain %.3f dB, analytic %.3f dB\n", g, ga);
    CHECK(NEAR(g, ga, 0.02), "time-domain gain %.4f vs %.4f", g, ga);
}

/* ------------------------------------------------------------ mix law */
static void test_mixlaw_pct(void)
{
    printf("[mix] MIX percent -> dB\n");
    bool mute = false;
    r5_mix_pct_to_db(0, &mute);
    CHECK(mute, "MIX 0 must mute");
    CHECK(NEAR(r5_mix_pct_to_db(1, &mute), -15.0, 1e-5) && !mute, "MIX 1 = -15 dB");
    CHECK(NEAR(r5_mix_pct_to_db(50, &mute), 0.0, 1e-5), "MIX 50 = 0 dB");
    CHECK(NEAR(r5_mix_pct_to_db(100, &mute), 6.0, 1e-5), "MIX 100 = +6 dB");
    float prev = -100;
    int mono = 1;
    for (int p = 1; p <= 100; p++) {
        float d = r5_mix_pct_to_db(p, &mute);
        if (d < prev) mono = 0;
        prev = d;
    }
    CHECK(mono, "MIX law must be monotonic");
}

static void test_codec_codes(void)
{
    printf("[mix] codec register codes vs. source-documented values\n");
    float r;
    /* esp-adf es8388.c: DACCONTROL17 = 0x90 "only left DAC to left mixer enable 0db"
       and 0x50 "LIN signal to left mixer ... 0db" -> bits 5:3 = 010 at 0 dB */
    uint8_t code = r5_es_byp_code(0.0f, &r);
    CHECK(code == 2 && NEAR(r, 0.0, 1e-6), "ES bypass 0 dB code %d", code);
    CHECK((uint8_t)(0x80 | 0x40 | (code << 3)) == 0xD0, "DACCONTROL17 DAC+bypass @0dB = 0xD0");
    CHECK(r5_es_byp_code(6.0f, &r) == 0 && r5_es_byp_code(-15.0f, &r) == 7, "ES bypass range +6..-15");
    CHECK(r5_es_byp_code(-40.0f, &r) == 7 && NEAR(r, -15, 1e-6), "ES bypass clamps at -15");
    /* esp-adf comment: 0x1E = 0 dB, 0x21 = +3 dB, 0x00 = -30 dB */
    CHECK(r5_es_outvol_code(0.0f, &r) == 0x1E, "ES OUT vol 0 dB = 0x1E");
    CHECK(r5_es_outvol_code(3.0f, &r) == 0x21, "ES OUT vol +3 dB = 0x21");
    CHECK(r5_es_outvol_code(-30.0f, &r) == 0x00, "ES OUT vol -30 dB = 0x00");
    /* esp-adf comment: 0xC0 = -96 dB, 0x64 = -50 dB, 0x00 = 0 dB */
    CHECK(r5_es_dacvol_code(-96.0f, &r) == 0xC0 && r5_es_dacvol_code(-50.0f, &r) == 0x64 &&
          r5_es_dacvol_code(0.0f, &r) == 0x00, "ES DAC vol codes");
    CHECK(r5_es_pga_code(24.0f, &r) == 8 && r5_es_pga_code(0.0f, &r) == 0, "ES PGA 0..24 dB");
    /* Linux tlv320aic32x4.c: driver gain signed 6-bit -6..+29; DAC vol -0x7f..0x30 */
    CHECK(r5_aic_drv_reg(-6, false) == 0x3A, "AIC drv -6 dB = 0x3A");
    CHECK(r5_aic_drv_reg(29, false) == 0x1D, "AIC drv +29 dB = 0x1D");
    CHECK(r5_aic_drv_reg(0, true) == 0x40, "AIC drv mute bit6");
    CHECK(r5_aic_dac_reg(-127) == 0x81 && r5_aic_dac_reg(48) == 0x30 && r5_aic_dac_reg(0) == 0,
          "AIC DAC vol range");
    CHECK(r5_aic_pga_reg(47.5f, &r) == 0x5F && r5_aic_pga_reg(24.0f, &r) == 48, "AIC PGA 0..47.5");
}

static void test_mixlaw_consistency(r5_codec_kind_t kind, const char *name, float vol_db)
{
    printf("[mix] %s: MIX moves codec bypass and internal mono path together (vol %.0f dB)\n",
           name, vol_db);
    float step = kind == R5_CODEC_ES8388 ? 3.0f : 1.0f;
    float prev_wired = -1000, prev_int = -1000;
    int ok_mono = 1, ok_eq = 1, ok_q = 1, ok_mute = 1, ok_violin = 1;
    for (int pct = 0; pct <= 100; pct++) {
        bool mute;
        r5_wired_req_t req = {0};
        req.vol_db = vol_db;
        req.mix_db = r5_mix_pct_to_db(pct, &mute);
        req.mute[0] = req.mute[1] = mute;
        r5_wired_plan_t plan;
        r5_plan_wired(kind, &req, &plan);
        float internal = r5_plan_internal_accomp_db(&plan, &req, mute, 0.0f);
        if (mute) {
            if (!(plan.mute[0] && plan.mute[1] && internal <= -150.0f)) ok_mute = 0;
            continue;
        }
        if (!NEAR(plan.mix_real_db[0], plan.mix_real_db[1], 1e-6)) ok_eq = 0;
        if (!NEAR(internal, plan.mix_real_db[0], 1e-4)) ok_eq = 0;
        /* violin level on the wired outputs must not move with MIX */
        if (!NEAR(plan.violin_db[0], vol_db, kind == R5_CODEC_ES8388 ? 0.51 : 0.26)) ok_violin = 0;
        /* realised value within half a step of the request when in range */
        float lo = kind == R5_CODEC_ES8388 ? -15.0f : (-6.0f - vol_db);
        if (req.mix_db >= lo && !NEAR(plan.mix_real_db[0], req.mix_db, step / 2 + 0.01)) ok_q = 0;
        if (plan.mix_real_db[0] < prev_wired - 1e-6 || internal < prev_int - 1e-6) ok_mono = 0;
        prev_wired = plan.mix_real_db[0];
        prev_int = internal;
    }
    CHECK(ok_mute, "MIX=0 must mute bypass L/R and internal accompaniment");
    CHECK(ok_eq, "internal accompaniment gain must equal realised codec bypass (both sides)");
    CHECK(ok_violin, "violin level must not depend on MIX");
    CHECK(ok_q, "realised bypass within half a codec step of the MIX law");
    CHECK(ok_mono, "wired and internal accompaniment must both be monotonic in MIX");
}

static void test_mix_trims(void)
{
    printf("[mix] per-side bypass trims do not shift the internal mono path\n");
    r5_wired_req_t req = {0};
    req.vol_db = 0;
    req.mix_db = 0;
    req.side_trim_db[0] = -3;
    req.side_trim_db[1] = +3;
    r5_wired_plan_t plan;
    r5_plan_wired(R5_CODEC_ES8388, &req, &plan);
    CHECK(NEAR(plan.accomp_db[0], -3, 1e-6) && NEAR(plan.accomp_db[1], 3, 1e-6), "ES side trims");
    float internal = r5_plan_internal_accomp_db(&plan, &req, false, -6.0f);
    CHECK(NEAR(internal, -6.0, 1e-5), "internal = MIX(0 dB) + cal(-6 dB), got %.3f", internal);
}

/* --------------------------------------------------------- engine path */
static r5_engine_params_t base_params(void)
{
    r5_engine_params_t p;
    memset(&p, 0, sizeof(p));
    p.pickup_gain_db = 3.0f;
    p.bass_db = 4.0f;
    p.treble_db = -2.0f;
    p.fx_depth = 0.5f;
    p.fx_on = true;
    p.spk_vol_db = -6.0f;
    p.accomp_db = -3.0f;
    p.spk_limit_on = false;
    p.spk_ceiling = 1.0f;
    return p;
}

static r5_engine_t g_eng;   /* large (reverb buffers) -> static */

static void test_engine_routing(void)
{
    printf("[engine] DAC = violin only; I2S1 = violin + mono accompaniment\n");
    enum { N = 48000, B = 64 };
    static float l[N], rr[N], dac[N], spk[N], scratch[B], zero[N];
    r5_engine_params_t p = base_params();

    /* 1) accompaniment only -> DAC must stay silent */
    r5_engine_init(&g_eng, FS, &p);
    for (int i = 0; i < N; i++) {
        l[i] = 0.0f;
        rr[i] = 0.5f * sinf(2.0f * (float)M_PI * 220.0f * i / FS);
    }
    for (int i = 0; i < N; i += B) r5_engine_process(&g_eng, l + i, rr + i, dac + i, spk + i, scratch, B);
    float leak = maxabs(dac, N);
    printf("  accompaniment leakage into DAC: %.3g (%.1f dBFS)\n", leak, r5_lin2db(leak));
    CHECK(leak < 1e-12f, "accompaniment leaked into DAC (%g)", leak);
    double g_acc = 20 * log10(rms(spk + N / 2, N / 2) / rms(rr + N / 2, N / 2));
    printf("  I2S1 accompaniment gain %.3f dB (expect spk_vol + accomp = %.1f dB)\n", g_acc,
           p.spk_vol_db + p.accomp_db);
    CHECK(NEAR(g_acc, p.spk_vol_db + p.accomp_db, 0.01), "I2S1 accompaniment gain");

    /* 2) both inputs: I2S1 must equal spk_vol*(DAC + accomp*R) sample by sample */
    r5_engine_init(&g_eng, FS, &p);
    for (int i = 0; i < N; i++) l[i] = 0.3f * sinf(2.0f * (float)M_PI * 440.0f * i / FS);
    for (int i = 0; i < N; i += B) r5_engine_process(&g_eng, l + i, rr + i, dac + i, spk + i, scratch, B);
    float gs = r5_db2lin(p.spk_vol_db), ga = r5_db2lin(p.accomp_db);
    double err = 0;
    for (int i = 0; i < N; i++) {
        double e = fabs(spk[i] - gs * (dac[i] + ga * rr[i]));
        if (e > err) err = e;
    }
    CHECK(err < 1e-6, "I2S1 != spk_vol*(violin + accomp*R), max err %g", err);

    /* 3) DAC with violin+accompaniment equals DAC with violin alone */
    static float dac2[N];
    r5_engine_init(&g_eng, FS, &p);
    for (int i = 0; i < N; i += B) r5_engine_process(&g_eng, l + i, zero + i, dac2 + i, spk + i, scratch, B);
    double d = 0;
    for (int i = 0; i < N; i++) if (fabs(dac[i] - dac2[i]) > d) d = fabs(dac[i] - dac2[i]);
    CHECK(d == 0.0, "DAC output depends on ADC-R (max diff %g)", d);
    printf("  violin-only DAC vs violin+accomp DAC: max diff %g\n", d);
}

static void test_engine_mix_follow(void)
{
    printf("[engine] I2S1 accompaniment level follows realised codec bypass for every MIX\n");
    enum { N = 9600, B = 64 };
    static float l[N], rr[N], dac[N], spk[N], scratch[B];
    for (int i = 0; i < N; i++) {
        l[i] = 0;
        rr[i] = 0.25f * sinf(2.0f * (float)M_PI * 330.0f * i / FS);
    }
    int ok = 1;
    for (int k = 0; k < 2; k++) {
        r5_codec_kind_t kind = k ? R5_CODEC_ES8388 : R5_CODEC_AIC3204;
        for (int pct = 0; pct <= 100; pct += 7) {
            bool mute;
            r5_wired_req_t req = {0};
            req.mix_db = r5_mix_pct_to_db(pct, &mute);
            req.mute[0] = req.mute[1] = mute;
            r5_wired_plan_t plan;
            r5_plan_wired(kind, &req, &plan);
            r5_engine_params_t p = base_params();
            p.spk_vol_db = 0;
            p.accomp_db = r5_plan_internal_accomp_db(&plan, &req, mute, 0.0f);
            r5_engine_init(&g_eng, FS, &p);
            for (int i = 0; i < N; i += B) r5_engine_process(&g_eng, l + i, rr + i, dac + i, spk + i, scratch, B);
            double out = rms(spk + N / 2, N / 2);
            if (mute) {
                if (out > 1e-9) ok = 0;
                continue;
            }
            double g = 20 * log10(out / rms(rr + N / 2, N / 2));
            if (!NEAR(g, plan.mix_real_db[0], 0.01)) {
                ok = 0;
                printf("  %s MIX %d: internal %.3f dB vs wired %.3f dB\n",
                       k ? "ES8388" : "AIC3204", pct, g, plan.mix_real_db[0]);
            }
        }
    }
    CHECK(ok, "internal accompaniment level must match realised wired bypass level");
}

/* ------------------------------------------------------ speaker ceiling */
static void test_ceiling(void)
{
    printf("[spk] speaker power ceiling\n");
    float c = r5_spk_ceiling(1.0f, 4.0f, 3.0f);
    printf("  1 W / 4 ohm / 3.0 Vrms@0dBFS -> ceiling %.4f (%.2f dBFS)\n", c, r5_lin2db(c));
    CHECK(NEAR(c, 2.0 / 3.0, 1e-5), "ceiling %f", c);
    float p = (c * 3.0f) * (c * 3.0f) / 4.0f;
    CHECK(NEAR(p, 1.0, 1e-4), "sine at ceiling must give 1 W (got %f)", p);
    CHECK(NEAR(r5_spk_ceiling(1.0f, 8.0f, 2.0f), 1.0, 1e-6), "ceiling clamps to full scale");

    r5_limiter_t lim;
    enum { N = 48000 };
    static float x[N], y[N];
    r5_limiter_init(&lim, FS, 0.5f, 80.0f);
    for (int i = 0; i < N; i++) x[i] = y[i] = sinf(2.0f * (float)M_PI * 1000.0f * i / FS);
    for (int i = 0; i < N; i += 64) r5_limiter_process(&lim, y + i, 64);
    CHECK(maxabs(y, N) <= 0.5f + 1e-7f, "loud signal exceeds ceiling: %f", maxabs(y, N));
    printf("  0 dBFS sine through 0.5 ceiling -> peak %.6f\n", maxabs(y, N));

    r5_limiter_init(&lim, FS, 0.5f, 80.0f);
    for (int i = 0; i < N; i++) x[i] = y[i] = 0.3f * sinf(2.0f * (float)M_PI * 1000.0f * i / FS);
    for (int i = 0; i < N; i += 64) r5_limiter_process(&lim, y + i, 64);
    double d = 0;
    for (int i = 0; i < N; i++) if (fabs(x[i] - y[i]) > d) d = fabs(x[i] - y[i]);
    CHECK(d == 0.0, "signal below ceiling must pass unchanged (max diff %g)", d);

    /* through the engine, with violin + accompaniment, limit enabled */
    static float l[N], rr[N], dac[N], spk[N], scratch[64];
    r5_engine_params_t pp = base_params();
    pp.spk_vol_db = +6.0f;
    pp.spk_limit_on = true;
    pp.spk_ceiling = c;
    r5_engine_init(&g_eng, FS, &pp);
    for (int i = 0; i < N; i++) {
        l[i] = 0.9f * sinf(2.0f * (float)M_PI * 440.0f * i / FS);
        rr[i] = 0.9f * sinf(2.0f * (float)M_PI * 110.0f * i / FS);
    }
    for (int i = 0; i < N; i += 64) r5_engine_process(&g_eng, l + i, rr + i, dac + i, spk + i, scratch, 64);
    CHECK(maxabs(spk, N) <= c + 1e-6f, "engine speaker output above ceiling: %f > %f", maxabs(spk, N), c);
    printf("  engine I2S1 peak %.4f with ceiling %.4f\n", maxabs(spk, N), c);
}

/* ---------------------------------------------------------------- tuner */
static double tuner_measure(double f, int harmonics, double noise, float *cents_out, int *midi_out)
{
    enum { NIN = 48000 * 2 / 5, W = 512, TMAX = 92 };
    static float in[NIN], dec[NIN / 4 + 8], scratch[R5_YIN_SCRATCH(W, TMAX)];
    static r5_decim4_t d;
    r5_decim4_init(&d, FS);
    for (int i = 0; i < NIN; i++) {
        double s = 0;
        for (int h = 1; h <= harmonics; h++) {
            s += (0.3 / h) * sin(2.0 * M_PI * f * h * i / FS + 0.3 * h);
        }
        in[i] = (float)(s + noise * grand());
    }
    int nd = 0;
    for (int i = 0; i < NIN; i += 64) nd += r5_decim4_process(&d, in + i, 64, dec + nd);
    r5_pitch_t p;
    bool ok = r5_yin(dec + nd - R5_YIN_LEN(W, TMAX), W, 5, TMAX, 0.15f, FS / 4.0f, scratch, &p);
    if (!ok) return 1e9;
    float cents;
    int midi;
    r5_note_from_freq(p.f0, 440.0f, &midi, &cents);
    if (cents_out) *cents_out = cents;
    if (midi_out) *midi_out = midi;
    return 1200.0 * log2(p.f0 / f);
}

static void test_tuner(void)
{
    printf("[tuner] YIN on 4:1 decimated pickup, open strings (+/-2 cents)\n");
    const double fr[4] = {196.0, 293.66, 440.0, 659.25};
    const char *names[4] = {"G3", "D4", "A4", "E5"};
    for (int k = 0; k < 4; k++) {
        for (int h = 1; h <= 6; h += 5) {
            float cents;
            int midi;
            double err = tuner_measure(fr[k], h, 0.0, &cents, &midi);
            char nb[8];
            r5_note_name(midi, nb, sizeof nb);
            printf("  %7.2f Hz (%d harm): error %+.3f cents -> %s %+.2f\n", fr[k], h, err, nb, cents);
            CHECK(fabs(err) <= 2.0, "%.2f Hz error %.3f cents", fr[k], err);
            CHECK(strcmp(nb, names[k]) == 0, "note name %s != %s", nb, names[k]);
        }
    }
    /* detuned input: 442 Hz must read A4 +7.85 cents */
    float cents;
    int midi;
    tuner_measure(442.0, 3, 0.0, &cents, &midi);
    CHECK(midi == 69 && NEAR(cents, 1200.0 * log2(442.0 / 440.0), 2.0), "442 Hz -> A4 %+.2f cents", cents);
    printf("  442.00 Hz -> A4 %+.2f cents (expect +7.85)\n", cents);
    /* with white noise 30 dB below the tone */
    for (int k = 0; k < 4; k++) {
        double err = tuner_measure(fr[k], 6, 0.3 / sqrt(2.0) * 0.0316, &cents, &midi);
        printf("  %7.2f Hz + noise (-30 dB): error %+.3f cents\n", fr[k], err);
        CHECK(fabs(err) <= 2.0, "noisy %.2f Hz error %.3f cents", fr[k], err);
    }
}

/* -------------------------------------------------------------- clickdet */
static void test_clickdet(void)
{
    printf("[lat] click detector on synthetic delayed / filtered / inverted signal\n");
    enum { N = 8192, M = 16 };
    static float tmpl[M], rec[N];
    r5_click_make(tmpl, M, 0.7f);
    const int delays[3] = {37, 312, 4000};
    for (int t = 0; t < 3; t++) {
        int D = delays[t];
        memset(rec, 0, sizeof rec);
        for (int k = 0; k < M; k++) rec[D + k] = -0.2f * tmpl[k];   /* inverted, -14 dB */
        /* analog path model: 1-pole HPF 20 Hz (AC coupling) + 2x 1-pole LPF 15 kHz */
        float a_hp = expf(-2.0f * (float)M_PI * 20.0f / FS);
        float a_lp = expf(-2.0f * (float)M_PI * 15000.0f / FS);
        float xp = 0, yp = 0, l1 = 0, l2 = 0;
        for (int i = 0; i < N; i++) {
            float x = rec[i];
            float hp = a_hp * (yp + x - xp);
            xp = x;
            yp = hp;
            l1 = (1 - a_lp) * hp + a_lp * l1;
            l2 = (1 - a_lp) * l1 + a_lp * l2;
            rec[i] = l2 + 0.05f + (float)(1e-3 * grand());  /* DC offset + noise */
        }
        float snr;
        int lag = r5_click_detect(rec, N, tmpl, M, 8.0f, &snr);
        printf("  delay %4d samples -> detected %4d (snr %.1f), %.3f ms\n", D, lag, snr, lag / 48.0);
        CHECK(lag >= D && lag <= D + 3, "delay %d detected %d", D, lag);
    }
    for (int i = 0; i < N; i++) rec[i] = (float)(1e-3 * grand());
    float snr;
    int lag = r5_click_detect(rec, N, tmpl, M, 8.0f, &snr);
    printf("  noise only -> %d (snr %.1f)\n", lag, snr);
    CHECK(lag == -1, "noise-only recording must not produce a detection (got %d)", lag);
}

int main(void)
{
    test_biquad();
    test_mixlaw_pct();
    test_codec_codes();
    test_mixlaw_consistency(R5_CODEC_ES8388, "ES8388", 0.0f);
    test_mixlaw_consistency(R5_CODEC_AIC3204, "AIC3204", 0.0f);
    test_mixlaw_consistency(R5_CODEC_AIC3204, "AIC3204", 9.0f);
    test_mix_trims();
    test_engine_routing();
    test_engine_mix_follow();
    test_ceiling();
    test_tuner();
    test_clickdet();
    printf("\n%d checks passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
