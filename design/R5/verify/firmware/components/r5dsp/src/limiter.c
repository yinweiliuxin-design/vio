/* Speaker output ceiling: instant-attack peak limiter + hard clamp. */
#include <math.h>
#include "r5dsp.h"

float r5_spk_ceiling(float p_watt, float r_ohm, float vrms_fs)
{
    if (p_watt <= 0.0f || r_ohm <= 0.0f || vrms_fs <= 0.0f) {
        return 1.0f;
    }
    float vrms_max = sqrtf(p_watt * r_ohm);   /* P = V^2 / R */
    float c = vrms_max / vrms_fs;              /* sine peak relative to FS */
    if (c > 1.0f) c = 1.0f;
    if (c < 0.001f) c = 0.001f;
    return c;
}

void r5_limiter_init(r5_limiter_t *l, float fs, float ceiling, float release_ms)
{
    l->gain = 1.0f;
    /* gain recovers by (1 - rel) of the remaining distance per sample */
    float tau = release_ms * 0.001f * fs;
    if (tau < 1.0f) tau = 1.0f;
    l->rel = 1.0f - expf(-1.0f / tau);
    r5_limiter_set_ceiling(l, ceiling);
}

void r5_limiter_set_ceiling(r5_limiter_t *l, float ceiling)
{
    if (ceiling > 1.0f) ceiling = 1.0f;
    if (ceiling < 0.001f) ceiling = 0.001f;
    l->ceiling = ceiling;
}

float r5_limiter_process(r5_limiter_t *l, float *buf, int n)
{
    const float c = l->ceiling;
    float g = l->gain;
    float gmin = g;
    for (int i = 0; i < n; i++) {
        float x = buf[i];
        float a = fabsf(x);
        /* release toward 1.0 */
        g += (1.0f - g) * l->rel;
        if (g > 0.99999f) g = 1.0f;
        /* instant attack */
        if (a * g > c) {
            g = c / a;
        }
        if (g < gmin) gmin = g;
        float y = x * g;
        /* guarantee (rounding) */
        if (y > c) y = c;
        if (y < -c) y = -c;
        buf[i] = y;
    }
    l->gain = g;
    return gmin;
}
