/*
 * Latency click: a short unipolar Hann pulse is written to the DAC; the user
 * patches the headphone output back into the pickup input. The recording of
 * ADC-L is cross-correlated with the template; the lag of the largest
 * |correlation| is the round-trip delay in samples. |.| makes the detector
 * immune to polarity inversion in the analog path.
 */
#include <math.h>
#include "r5dsp.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

void r5_click_make(float *tmpl, int len, float amp)
{
    for (int i = 0; i < len; i++) {
        tmpl[i] = amp * 0.5f * (1.0f - cosf(2.0f * (float)M_PI * (float)(i + 1) / (float)(len + 1)));
    }
}

int r5_click_detect(const float *rec, int n, const float *tmpl, int m,
                    float min_snr, float *snr_out)
{
    if (snr_out) *snr_out = 0.0f;
    if (n <= m || m <= 0) return -1;

    /* remove DC of the recording (AC coupling leaves offsets) */
    double mean = 0.0;
    for (int i = 0; i < n; i++) mean += rec[i];
    mean /= n;
    double tmean = 0.0;
    for (int k = 0; k < m; k++) tmean += tmpl[k];
    tmean /= m;

    const int L = n - m + 1;
    double best = 0.0, sumsq = 0.0;
    int best_k = -1;
    for (int k = 0; k < L; k++) {
        double acc = 0.0;
        for (int j = 0; j < m; j++) {
            acc += ((double)rec[k + j] - mean) * ((double)tmpl[j] - tmean);
        }
        double a = fabs(acc);
        sumsq += acc * acc;
        if (a > best) {
            best = a;
            best_k = k;
        }
    }
    /* noise estimate: rms of correlation away from the peak */
    double excl = 0.0;
    int excl_n = 0;
    for (int k = best_k - 2 * m; k <= best_k + 2 * m; k++) {
        if (k < 0 || k >= L) continue;
        double acc = 0.0;
        for (int j = 0; j < m; j++) {
            acc += ((double)rec[k + j] - mean) * ((double)tmpl[j] - tmean);
        }
        excl += acc * acc;
        excl_n++;
    }
    double rest = sumsq - excl;
    int rest_n = L - excl_n;
    double rms = rest_n > 0 && rest > 0.0 ? sqrt(rest / rest_n) : 1e-30;
    double snr = best / rms;
    if (snr_out) *snr_out = (float)snr;
    if (best_k < 0 || snr < min_snr) return -1;
    return best_k;
}
