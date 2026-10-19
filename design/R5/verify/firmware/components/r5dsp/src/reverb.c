/*
 * Small mono Schroeder reverb: 4 parallel damped feedback combs followed by
 * 2 series allpasses (the Freeverb structure, reduced). Delay lengths are the
 * public-domain Freeverb tunings scaled from 44.1 kHz to the running rate.
 */
#include <string.h>
#include "r5dsp.h"

static const int k_comb_44k[R5_RV_NCOMB] = {1116, 1188, 1277, 1356};
static const int k_ap_44k[R5_RV_NAP] = {556, 441};

void r5_reverb_init(r5_reverb_t *rv, float fs)
{
    memset(rv, 0, sizeof(*rv));
    float scale = fs / 44100.0f;
    for (int i = 0; i < R5_RV_NCOMB; i++) {
        int len = (int)(k_comb_44k[i] * scale + 0.5f);
        if (len > R5_RV_COMB_MAX) len = R5_RV_COMB_MAX;
        if (len < 1) len = 1;
        rv->comb_len[i] = len;
    }
    for (int i = 0; i < R5_RV_NAP; i++) {
        int len = (int)(k_ap_44k[i] * scale + 0.5f);
        if (len > R5_RV_AP_MAX) len = R5_RV_AP_MAX;
        if (len < 1) len = 1;
        rv->ap_len[i] = len;
    }
    rv->damp = 0.25f;
    r5_reverb_set(rv, 0.3f, 0.5f);
}

void r5_reverb_set(r5_reverb_t *rv, float depth, float decay)
{
    if (depth < 0.0f) depth = 0.0f;
    if (depth > 1.0f) depth = 1.0f;
    if (decay < 0.0f) decay = 0.0f;
    if (decay > 1.0f) decay = 1.0f;
    rv->depth = depth;
    rv->feedback = 0.70f + 0.26f * decay;   /* 0.70 .. 0.96 */
}

void r5_reverb_process(r5_reverb_t *rv, const float *in, float *out, int n)
{
    const float fb = rv->feedback;
    const float d1 = rv->damp, d2 = 1.0f - rv->damp;
    const float wet_gain = 0.35f * rv->depth;
    const float dry_gain = 1.0f - 0.4f * rv->depth;
    for (int i = 0; i < n; i++) {
        float x = in[i];
        float xin = x * 0.25f + 1e-18f;   /* tiny offset keeps buffers out of denormals */
        float acc = 0.0f;
        for (int c = 0; c < R5_RV_NCOMB; c++) {
            float *buf = rv->comb_buf[c];
            int idx = rv->comb_idx[c];
            float y = buf[idx];
            rv->comb_filt[c] = y * d2 + rv->comb_filt[c] * d1;
            buf[idx] = xin + rv->comb_filt[c] * fb;
            if (++idx >= rv->comb_len[c]) idx = 0;
            rv->comb_idx[c] = idx;
            acc += y;
        }
        for (int a = 0; a < R5_RV_NAP; a++) {
            float *buf = rv->ap_buf[a];
            int idx = rv->ap_idx[a];
            float bo = buf[idx];
            float y = -acc + bo;
            buf[idx] = acc + bo * 0.5f;
            if (++idx >= rv->ap_len[a]) idx = 0;
            rv->ap_idx[a] = idx;
            acc = y;
        }
        out[i] = x * dry_gain + acc * wet_gain;
    }
    for (int c = 0; c < R5_RV_NCOMB; c++) {
        if (rv->comb_filt[c] < 1e-20f && rv->comb_filt[c] > -1e-20f) rv->comb_filt[c] = 0.0f;
    }
}
