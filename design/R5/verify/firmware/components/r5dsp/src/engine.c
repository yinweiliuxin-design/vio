/*
 * Per-block audio engine.
 *
 *   ADC-L (pickup) -> pickup gain -> low shelf -> high shelf -> reverb  = violin
 *   DAC   (codec)  <- violin only              (never the accompaniment)
 *   I2S1  (spk/BT) <- spk_vol * (violin + accomp_gain * ADC-R) -> ceiling
 *
 * Parameters are published by the control thread through a small seqlock so
 * the audio thread never blocks.
 */
#include <math.h>
#include <string.h>
#include "r5dsp.h"

#define BASS_F0   200.0f
#define TREBLE_F0 3000.0f
#define SHELF_S   0.9f

static void barrier(void) { __sync_synchronize(); }

static float gain_or_zero(float db, float floor_db)
{
    return db <= floor_db ? 0.0f : r5_db2lin(db);
}

static void apply(r5_engine_t *e)
{
    const r5_engine_params_t *p = &e->p;
    r5_bq_lowshelf(&e->low.c, e->fs, BASS_F0, p->bass_db, SHELF_S);
    r5_bq_highshelf(&e->high.c, e->fs, TREBLE_F0, p->treble_db, SHELF_S);
    r5_reverb_set(&e->rv, p->fx_depth, 0.5f);
    r5_limiter_set_ceiling(&e->lim, p->spk_ceiling);
    e->t_pick = p->violin_mute ? 0.0f : r5_db2lin(p->pickup_gain_db);
    e->t_spk = gain_or_zero(p->spk_vol_db, -100.0f);
    e->t_acc = gain_or_zero(p->accomp_db, -150.0f);
}

void r5_engine_init(r5_engine_t *e, float fs, const r5_engine_params_t *p)
{
    memset(e, 0, sizeof(*e));
    e->fs = fs;
    e->p = *p;
    e->pend = *p;
    r5_bq_reset(&e->low);
    r5_bq_reset(&e->high);
    r5_reverb_init(&e->rv, fs);
    r5_limiter_init(&e->lim, fs, p->spk_ceiling, 80.0f);
    apply(e);
    e->g_pick = e->t_pick;
    e->g_spk = e->t_spk;
    e->g_acc = e->t_acc;
    e->smooth = 1.0f - expf(-1.0f / (0.005f * fs));   /* 5 ms gain smoothing */
    e->last_min_lim_gain = 1.0f;
}

void r5_engine_set_params(r5_engine_t *e, const r5_engine_params_t *p)
{
    e->seq++;            /* odd: write in progress */
    barrier();
    e->pend = *p;
    barrier();
    e->seq++;            /* even: stable */
}

void r5_engine_get_params(const r5_engine_t *e, r5_engine_params_t *p)
{
    *p = e->pend;
}

static void maybe_update(r5_engine_t *e)
{
    uint32_t s1 = e->seq;
    if ((s1 & 1u) || s1 == e->seq_applied) {
        return;
    }
    barrier();
    r5_engine_params_t tmp = e->pend;
    barrier();
    if (e->seq != s1) {
        return;          /* writer raced us; pick it up next block */
    }
    e->p = tmp;
    e->seq_applied = s1;
    apply(e);
}

void r5_engine_process(r5_engine_t *e, const float *adc_l, const float *adc_r,
                       float *dac, float *spk, float *scratch, int n)
{
    maybe_update(e);
    const float k = e->smooth;

    /* violin chain */
    float g = e->g_pick;
    const float tp = e->t_pick;
    for (int i = 0; i < n; i++) {
        g += (tp - g) * k;
        scratch[i] = adc_l[i] * g;
    }
    e->g_pick = g;
    r5_bq_process(&e->low, scratch, scratch, n);
    r5_bq_process(&e->high, scratch, scratch, n);
    if (e->p.fx_on && e->p.fx_depth > 0.0f) {
        r5_reverb_process(&e->rv, scratch, dac, n);
    } else {
        memcpy(dac, scratch, (size_t)n * sizeof(float));
    }

    /* I2S1 mix: violin + mono accompaniment */
    float gs = e->g_spk, ga = e->g_acc;
    const float ts = e->t_spk, ta = e->t_acc;
    for (int i = 0; i < n; i++) {
        gs += (ts - gs) * k;
        ga += (ta - ga) * k;
        spk[i] = gs * (dac[i] + ga * adc_r[i]);
    }
    e->g_spk = gs;
    e->g_acc = ga;

    if (e->p.spk_limit_on) {
        e->last_min_lim_gain = r5_limiter_process(&e->lim, spk, n);
    } else {
        for (int i = 0; i < n; i++) {
            if (spk[i] > 1.0f) spk[i] = 1.0f;
            if (spk[i] < -1.0f) spk[i] = -1.0f;
        }
        e->last_min_lim_gain = 1.0f;
    }
}
