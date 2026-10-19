/* Tuner: 4:1 decimating FIR + YIN pitch estimator + note naming. */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "r5dsp.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

void r5_decim4_init(r5_decim4_t *d, float fs_in)
{
    memset(d, 0, sizeof(*d));
    /* Blackman-windowed sinc low-pass. Normalised cutoff 0.1042 cycles/sample
     * (5 kHz at 48 kHz in), i.e. 0.42 x the Nyquist of the 4:1 output. */
    (void)fs_in;
    const double fc = 5000.0 / 48000.0;
    const int M = R5_DEC_TAPS - 1;
    double sum = 0.0;
    for (int k = 0; k < R5_DEC_TAPS; k++) {
        double m = k - M / 2.0;
        double s = (m == 0.0) ? 2.0 * fc : sin(2.0 * M_PI * fc * m) / (M_PI * m);
        double w = 0.42 - 0.5 * cos(2.0 * M_PI * k / M) + 0.08 * cos(4.0 * M_PI * k / M);
        d->h[k] = (float)(s * w);
        sum += s * w;
    }
    for (int k = 0; k < R5_DEC_TAPS; k++) {
        d->h[k] = (float)(d->h[k] / sum);
    }
}

int r5_decim4_process(r5_decim4_t *d, const float *in, int n, float *out)
{
    int nout = 0;
    for (int i = 0; i < n; i++) {
        d->hist[d->pos] = in[i];
        d->hist[d->pos + R5_DEC_TAPS] = in[i];
        if (++d->pos >= R5_DEC_TAPS) d->pos = 0;
        if (++d->phase >= 4) {
            d->phase = 0;
            const float *w = &d->hist[d->pos];   /* oldest .. newest */
            float acc = 0.0f;
            for (int k = 0; k < R5_DEC_TAPS; k++) {
                acc += d->h[k] * w[k];
            }
            out[nout++] = acc;
        }
    }
    return nout;
}

/* Difference function d(tau) = sum_j (f[j] - f[j+tau])^2 over the frame f. */
static float yin_diff(const float *f, int W, int tau)
{
    float acc = 0.0f;
    const float *b = f + tau;
    for (int j = 0; j < W; j++) {
        float diff = f[j] - b[j];
        acc += diff * diff;
    }
    return acc;
}

bool r5_yin(const float *x, int W, int tau_min, int tau_max, float thresh, float fs,
            float *scratch, r5_pitch_t *out)
{
    const int nbuf = R5_YIN_PRE + W + tau_max + 2;
    const float *f = x + R5_YIN_PRE;       /* analysis frame */
    float *d = scratch;                    /* raw difference, [0..tau_max] */
    float *dp = scratch + (tau_max + 1);   /* cumulative-mean-normalised */
    float *y = scratch + 2 * (tau_max + 1);/* low-passed copy for refinement */
    out->f0 = 0.0f;
    out->aperiodicity = 1.0f;
    if (tau_min < 2) tau_min = 2;
    if (tau_max <= tau_min + 2) return false;

    d[0] = 0.0f;
    for (int tau = 1; tau <= tau_max; tau++) {
        d[tau] = yin_diff(f, W, tau);
    }
    dp[0] = 1.0f;
    float running = 0.0f;
    for (int tau = 1; tau <= tau_max; tau++) {
        running += d[tau];
        dp[tau] = running > 0.0f ? d[tau] * (float)tau / running : 1.0f;
    }

    int best = -1;
    for (int tau = tau_min; tau < tau_max; tau++) {
        if (dp[tau] < thresh) {
            while (tau + 1 < tau_max && dp[tau + 1] < dp[tau]) {
                tau++;
            }
            best = tau;
            break;
        }
    }
    if (best < 0) {
        float m = 1e30f;
        for (int tau = tau_min; tau < tau_max; tau++) {
            if (dp[tau] < m) {
                m = dp[tau];
                best = tau;
            }
        }
        if (best < 0 || m > 0.35f) {
            out->aperiodicity = m;
            return false;
        }
    }

    /*
     * Sub-sample refinement. A 3-point parabola on d(tau) is biased when strong
     * harmonics sit close to Nyquist (d is then far from quadratic within +/-1
     * lag). Low-passing does not change the period, so the refinement runs on
     * a copy filtered by two cascaded 2nd-order low-passes at 1.25 x the coarse
     * f0: the copy is nearly a pure sine and the parabola becomes accurate.
     * R5_YIN_PRE samples of pre-roll let the filters settle before the frame.
     */
    float fc = 1.25f * fs / (float)best;
    if (fc > 0.45f * fs) fc = 0.45f * fs;
    r5_bq_t lp;
    r5_bq_lowpass(&lp.c, fs, fc, 0.7071f);
    r5_bq_reset(&lp);
    r5_bq_process(&lp, x, y, nbuf);
    r5_bq_reset(&lp);
    r5_bq_process(&lp, y, y, nbuf);
    const float *fy = y + R5_YIN_PRE;
    float a = yin_diff(fy, W, best - 1);
    float b = yin_diff(fy, W, best);
    float c = yin_diff(fy, W, best + 1);
    float shift = 0.0f;
    float den = a - 2.0f * b + c;
    if (den > 0.0f) {
        shift = 0.5f * (a - c) / den;
        if (shift > 1.0f) shift = 1.0f;
        if (shift < -1.0f) shift = -1.0f;
    }
    out->f0 = fs / ((float)best + shift);
    out->aperiodicity = dp[best];
    return true;
}

void r5_note_from_freq(float f, float a4, int *midi, float *cents)
{
    if (f <= 0.0f) {
        *midi = -1;
        *cents = 0.0f;
        return;
    }
    double n = 69.0 + 12.0 * log2((double)f / (double)a4);
    int m = (int)lround(n);
    double ref = (double)a4 * pow(2.0, (m - 69) / 12.0);
    *midi = m;
    *cents = (float)(1200.0 * log2((double)f / ref));
}

const char *r5_note_name(int midi, char *buf, int buflen)
{
    static const char *names[12] = {"C", "C#", "D", "D#", "E", "F",
                                    "F#", "G", "G#", "A", "A#", "B"};
    if (midi < 0) {
        snprintf(buf, (size_t)buflen, "--");
    } else {
        snprintf(buf, (size_t)buflen, "%s%d", names[midi % 12], midi / 12 - 1);
    }
    return buf;
}
