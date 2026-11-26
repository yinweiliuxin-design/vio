/* RBJ cookbook biquads (Robert Bristow-Johnson, "Audio EQ Cookbook"). */
#include <math.h>
#include "r5dsp.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

float r5_db2lin(float db) { return powf(10.0f, db / 20.0f); }

float r5_lin2db(float lin)
{
    if (lin <= 1e-10f) {
        return -200.0f;
    }
    return 20.0f * log10f(lin);
}

void r5_bq_identity(r5_bq_coef_t *c)
{
    c->b0 = 1.0f; c->b1 = 0.0f; c->b2 = 0.0f; c->a1 = 0.0f; c->a2 = 0.0f;
}

static void store(r5_bq_coef_t *c, double b0, double b1, double b2,
                  double a0, double a1, double a2)
{
    c->b0 = (float)(b0 / a0);
    c->b1 = (float)(b1 / a0);
    c->b2 = (float)(b2 / a0);
    c->a1 = (float)(a1 / a0);
    c->a2 = (float)(a2 / a0);
}

void r5_bq_lowshelf(r5_bq_coef_t *c, float fs, float f0, float gain_db, float S)
{
    double A = pow(10.0, gain_db / 40.0);
    double w0 = 2.0 * M_PI * f0 / fs;
    double cw = cos(w0), sw = sin(w0);
    double alpha = sw / 2.0 * sqrt((A + 1.0 / A) * (1.0 / S - 1.0) + 2.0);
    double sa = 2.0 * sqrt(A) * alpha;
    store(c,
          A * ((A + 1) - (A - 1) * cw + sa),
          2 * A * ((A - 1) - (A + 1) * cw),
          A * ((A + 1) - (A - 1) * cw - sa),
          (A + 1) + (A - 1) * cw + sa,
          -2 * ((A - 1) + (A + 1) * cw),
          (A + 1) + (A - 1) * cw - sa);
}

void r5_bq_highshelf(r5_bq_coef_t *c, float fs, float f0, float gain_db, float S)
{
    double A = pow(10.0, gain_db / 40.0);
    double w0 = 2.0 * M_PI * f0 / fs;
    double cw = cos(w0), sw = sin(w0);
    double alpha = sw / 2.0 * sqrt((A + 1.0 / A) * (1.0 / S - 1.0) + 2.0);
    double sa = 2.0 * sqrt(A) * alpha;
    store(c,
          A * ((A + 1) + (A - 1) * cw + sa),
          -2 * A * ((A - 1) + (A + 1) * cw),
          A * ((A + 1) + (A - 1) * cw - sa),
          (A + 1) - (A - 1) * cw + sa,
          2 * ((A - 1) - (A + 1) * cw),
          (A + 1) - (A - 1) * cw - sa);
}

void r5_bq_peaking(r5_bq_coef_t *c, float fs, float f0, float gain_db, float Q)
{
    double A = pow(10.0, gain_db / 40.0);
    double w0 = 2.0 * M_PI * f0 / fs;
    double cw = cos(w0), sw = sin(w0);
    double alpha = sw / (2.0 * Q);
    store(c, 1 + alpha * A, -2 * cw, 1 - alpha * A, 1 + alpha / A, -2 * cw, 1 - alpha / A);
}

void r5_bq_lowpass(r5_bq_coef_t *c, float fs, float f0, float Q)
{
    double w0 = 2.0 * M_PI * f0 / fs;
    double cw = cos(w0), sw = sin(w0);
    double alpha = sw / (2.0 * Q);
    store(c, (1 - cw) / 2, 1 - cw, (1 - cw) / 2, 1 + alpha, -2 * cw, 1 - alpha);
}

float r5_bq_mag_db(const r5_bq_coef_t *c, float fs, float f)
{
    double w = 2.0 * M_PI * f / fs;
    double c1 = cos(w), s1 = sin(w), c2 = cos(2 * w), s2 = sin(2 * w);
    double nr = c->b0 + c->b1 * c1 + c->b2 * c2;
    double ni = -(c->b1 * s1 + c->b2 * s2);
    double dr = 1.0 + c->a1 * c1 + c->a2 * c2;
    double di = -(c->a1 * s1 + c->a2 * s2);
    double num = nr * nr + ni * ni;
    double den = dr * dr + di * di;
    return (float)(10.0 * log10(num / den));
}

void r5_bq_reset(r5_bq_t *bq)
{
    bq->z1 = 0.0f;
    bq->z2 = 0.0f;
}

void r5_bq_process(r5_bq_t *bq, const float *in, float *out, int n)
{
    const float b0 = bq->c.b0, b1 = bq->c.b1, b2 = bq->c.b2;
    const float a1 = bq->c.a1, a2 = bq->c.a2;
    float z1 = bq->z1, z2 = bq->z2;
    for (int i = 0; i < n; i++) {
        float x = in[i];
        float y = b0 * x + z1;
        z1 = b1 * x - a1 * y + z2;
        z2 = b2 * x - a2 * y;
        out[i] = y;
    }
    /* flush denormals */
    if (fabsf(z1) < 1e-20f) z1 = 0.0f;
    if (fabsf(z2) < 1e-20f) z2 = 0.0f;
    bq->z1 = z1;
    bq->z2 = z2;
}
