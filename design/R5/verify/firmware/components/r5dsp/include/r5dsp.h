/*
 * r5dsp.h - Pure C DSP / math library for the SmartVio R5 bench firmware.
 *
 * Nothing in this library depends on ESP-IDF: it is compiled both into the
 * firmware (as an IDF component) and on the host by tests/run_host_tests.sh.
 *
 * Contents
 *   - biquad      : RBJ low-shelf / high-shelf / peaking biquads (tone control)
 *   - reverb      : small Schroeder/Freeverb-style mono reverb (FX, "depth")
 *   - limiter     : speaker output ceiling (power limit -> digital peak ceiling)
 *   - mix law     : MIX percent -> accompaniment dB, codec gain quantisers and
 *                   the "wired plan" that keeps codec bypass and internal mono
 *                   accompaniment consistent
 *   - engine      : per-block processing (violin chain, DAC feed, I2S1 mix)
 *   - tuner       : 4:1 decimator + YIN pitch detector + note naming
 *   - clickdet    : latency click template + correlation detector
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ utils */
float r5_db2lin(float db);
float r5_lin2db(float lin);           /* returns -200 for lin <= 1e-10 */

/* ----------------------------------------------------------------- biquad */
typedef struct {
    float b0, b1, b2, a1, a2;         /* a0 normalised to 1 */
} r5_bq_coef_t;

typedef struct {
    r5_bq_coef_t c;
    float z1, z2;                     /* transposed direct form II state */
} r5_bq_t;

void  r5_bq_identity(r5_bq_coef_t *c);
/* RBJ audio-EQ-cookbook shelving filters, slope S (1.0 = steepest monotonic) */
void  r5_bq_lowshelf(r5_bq_coef_t *c, float fs, float f0, float gain_db, float S);
void  r5_bq_highshelf(r5_bq_coef_t *c, float fs, float f0, float gain_db, float S);
void  r5_bq_peaking(r5_bq_coef_t *c, float fs, float f0, float gain_db, float Q);
void  r5_bq_lowpass(r5_bq_coef_t *c, float fs, float f0, float Q);
float r5_bq_mag_db(const r5_bq_coef_t *c, float fs, float f);
void  r5_bq_reset(r5_bq_t *bq);
void  r5_bq_process(r5_bq_t *bq, const float *in, float *out, int n);

/* ----------------------------------------------------------------- reverb */
#define R5_RV_NCOMB 4
#define R5_RV_NAP   2
/* Buffer lengths sized for fs <= 48 kHz (Freeverb tunings scaled 48/44.1) */
#define R5_RV_COMB_MAX 1480
#define R5_RV_AP_MAX   608

typedef struct {
    float comb_buf[R5_RV_NCOMB][R5_RV_COMB_MAX];
    int   comb_len[R5_RV_NCOMB];
    int   comb_idx[R5_RV_NCOMB];
    float comb_filt[R5_RV_NCOMB];
    float ap_buf[R5_RV_NAP][R5_RV_AP_MAX];
    int   ap_len[R5_RV_NAP];
    int   ap_idx[R5_RV_NAP];
    float feedback;                   /* comb feedback (decay) */
    float damp;                       /* comb damping */
    float depth;                      /* 0..1 wet amount */
} r5_reverb_t;

void r5_reverb_init(r5_reverb_t *rv, float fs);
void r5_reverb_set(r5_reverb_t *rv, float depth, float decay);
void r5_reverb_process(r5_reverb_t *rv, const float *in, float *out, int n);

/* ---------------------------------------------------------------- limiter */
/*
 * Speaker ceiling: a sine with sample peak 1.0 (0 dBFS) gives vrms_fs volts RMS
 * across the speaker (measured once with `spk tone`). For a power limit P into
 * R ohms the allowed sine peak is sqrt(P*R)/vrms_fs (clamped to 1.0).
 */
float r5_spk_ceiling(float p_watt, float r_ohm, float vrms_fs);

typedef struct {
    float ceiling;                    /* linear peak ceiling, 0 < c <= 1 */
    float gain;                       /* current gain */
    float rel;                        /* release coefficient per sample */
} r5_limiter_t;

void r5_limiter_init(r5_limiter_t *l, float fs, float ceiling, float release_ms);
void r5_limiter_set_ceiling(r5_limiter_t *l, float ceiling);
/* Output is guaranteed |y| <= ceiling. Signals below ceiling pass unchanged
 * once the gain has recovered to 1.0. Returns the minimum gain in the block. */
float r5_limiter_process(r5_limiter_t *l, float *buf, int n);

/* --------------------------------------------------------------- mix law */
typedef enum {
    R5_CODEC_AIC3204 = 0,
    R5_CODEC_ES8388  = 1,
} r5_codec_kind_t;

/* MIX 0..100 %. 0 = accompaniment muted on every path.
 * 1..50 maps linearly in dB to -15..0 dB, 50..100 maps to 0..+6 dB. */
#define R5_MIX_DB_MIN (-15.0f)
#define R5_MIX_DB_MAX (6.0f)
float r5_mix_pct_to_db(int pct, bool *mute);

/* Requested wired-output state (headphone + line outputs of the codec). */
typedef struct {
    float vol_db;            /* wired master: violin level on HP/LINE */
    float dac_trim_db;       /* extra violin trim (console `dac`) */
    float mix_db;            /* accompaniment relative to violin (from MIX) */
    float side_trim_db[2];   /* per-side bypass trim (console `byp L/R`) */
    bool  mute[2];           /* per-side bypass mute */
} r5_wired_req_t;

/* What the codec can actually do with that request (quantised / clamped). */
typedef struct {
    float violin_db[2];      /* realised violin level per side */
    float accomp_db[2];      /* realised accompaniment (bypass) level per side */
    float mix_real_db[2];    /* accomp - violin per side */
    bool  mute[2];
    /* ES8388 register codes (Linux es8328.c / esp-adf scales) */
    uint8_t es_outvol[2];    /* LOUT1/ROUT1 and LOUT2/ROUT2: 0x00=-30dB, 1dB step */
    uint8_t es_dacvol[2];    /* DACCONTROL4/5: 0=0dB, 0.5dB attenuation step */
    uint8_t es_byp_code[2];  /* LI2LOVOL/RI2ROVOL: 0=+6dB .. 7=-15dB, 3dB step */
    /* TLV320AIC3204 values (Linux tlv320aic32x4.c scales) */
    int8_t  aic_drv_db[2];   /* HPL/HPR and LOL/LOR driver gain, -6..+29 dB */
    int16_t aic_dac_halfdb[2]; /* DAC digital volume in 0.5 dB, -127..+48 */
} r5_wired_plan_t;

void  r5_plan_wired(r5_codec_kind_t kind, const r5_wired_req_t *req, r5_wired_plan_t *plan);
/* Internal mono-accompaniment gain (dB, relative to violin) for the I2S1 mix,
 * derived from the REALISED codec bypass so both paths move together.
 * Returns -200 (mute) when both sides are muted by MIX=0. cal_db aligns the
 * ADC-R level with the analog bypass level (default -PGA_R). */
float r5_plan_internal_accomp_db(const r5_wired_plan_t *plan, const r5_wired_req_t *req,
                                 bool mix_mute, float cal_db);

/* Individual quantisers (exposed for tests and console printouts) */
uint8_t r5_es_byp_code(float db, float *real_db);
uint8_t r5_es_outvol_code(float db, float *real_db);
uint8_t r5_es_dacvol_code(float db, float *real_db);
uint8_t r5_es_pga_code(float db, float *real_db);
uint8_t r5_aic_drv_reg(int db, bool mute);           /* P1 R16..R19 value */
uint8_t r5_aic_dac_reg(int halfdb);                  /* P0 R65/R66 value  */
uint8_t r5_aic_pga_reg(float db, float *real_db);    /* P1 R59/R60 value  */

/* ----------------------------------------------------------------- engine */
typedef struct {
    float pickup_gain_db;    /* digital pickup gain */
    float bass_db;           /* low shelf @ 200 Hz */
    float treble_db;         /* high shelf @ 3 kHz */
    float fx_depth;          /* 0..1 */
    bool  fx_on;
    float spk_vol_db;        /* I2S1 (speaker/BT) master */
    float accomp_db;         /* internal mono accompaniment gain rel. violin; <=-150 => muted */
    bool  spk_limit_on;      /* apply speaker ceiling on I2S1 */
    float spk_ceiling;       /* linear */
    bool  violin_mute;       /* mute violin on all outputs */
} r5_engine_params_t;

typedef struct {
    float fs;
    r5_engine_params_t p;            /* active params (audio thread) */
    r5_engine_params_t pend;         /* pending params (control thread) */
    volatile uint32_t seq;           /* seqlock for pend */
    uint32_t seq_applied;
    r5_bq_t low, high;
    r5_reverb_t rv;
    r5_limiter_t lim;
    float g_pick, g_spk, g_acc;      /* smoothed linear gains */
    float t_pick, t_spk, t_acc;      /* targets */
    float smooth;                    /* one-pole smoothing coefficient */
    float last_min_lim_gain;
} r5_engine_t;

void r5_engine_init(r5_engine_t *e, float fs, const r5_engine_params_t *p);
/* Control thread: publish new params (single writer, must be serialised). */
void r5_engine_set_params(r5_engine_t *e, const r5_engine_params_t *p);
void r5_engine_get_params(const r5_engine_t *e, r5_engine_params_t *p);
/*
 * Audio thread: one block.
 *   adc_l : pickup (codec ADC-L)          adc_r : mono accompaniment (ADC-R)
 *   dac   : processed violin ONLY (goes to codec DAC L and R)
 *   spk   : spk_vol * (violin + accomp_gain * adc_r), then speaker ceiling
 *           (goes to I2S1 L and R: MAX98357A + BT TX module)
 * Buffers may not alias. scratch must hold n floats.
 */
void r5_engine_process(r5_engine_t *e, const float *adc_l, const float *adc_r,
                       float *dac, float *spk, float *scratch, int n);

/* ------------------------------------------------------------------ tuner */
#define R5_DEC_TAPS 63
typedef struct {
    float h[R5_DEC_TAPS];
    float hist[R5_DEC_TAPS * 2];
    int   pos;
    int   phase;
} r5_decim4_t;

void r5_decim4_init(r5_decim4_t *d, float fs_in);
/* returns number of output samples written (about n/4) */
int  r5_decim4_process(r5_decim4_t *d, const float *in, int n, float *out);

typedef struct {
    float f0;           /* Hz, 0 if unvoiced */
    float aperiodicity; /* YIN d' at the chosen lag (lower = cleaner) */
} r5_pitch_t;

/* YIN (de Cheveigne & Kawahara 2002) with sub-sample refinement on an
 * adaptively low-passed copy. x must hold R5_YIN_PRE + W + tau_max + 2 samples;
 * the analysis frame starts at x + R5_YIN_PRE (the pre-roll lets the
 * refinement filters settle). scratch must hold R5_YIN_SCRATCH(W, tau_max). */
#define R5_YIN_PRE 256
#define R5_YIN_LEN(W, tau_max) (R5_YIN_PRE + (W) + (tau_max) + 2)
#define R5_YIN_SCRATCH(W, tau_max) (2 * ((tau_max) + 1) + R5_YIN_LEN(W, tau_max))
bool r5_yin(const float *x, int W, int tau_min, int tau_max, float thresh, float fs,
            float *scratch, r5_pitch_t *out);
void r5_note_from_freq(float f, float a4, int *midi, float *cents);
const char *r5_note_name(int midi, char *buf, int buflen);

/* --------------------------------------------------------------- clickdet */
/* Click used by `lat`: a unipolar Hann pulse of len samples, peak amp. */
void r5_click_make(float *tmpl, int len, float amp);
/* Find the click in rec[0..n). Returns lag (template start) or -1 if no
 * convincing peak. snr_out (optional) = |peak| / rms(correlation). */
int  r5_click_detect(const float *rec, int n, const float *tmpl, int m,
                     float min_snr, float *snr_out);

#ifdef __cplusplus
}
#endif
