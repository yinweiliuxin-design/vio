/*
 * MIX law and codec gain plans.
 *
 * Rule: the codec DAC carries only the violin. The accompaniment reaches the
 * wired outputs only through the codec's ANALOG bypass, and reaches I2S1
 * (speaker / BT) only through ADC-R. MIX therefore has to move two things at
 * once: the codec bypass gain and the internal mono-accompaniment gain. To
 * keep them equal, the internal gain is computed from the gain the codec can
 * REALLY produce (after quantisation and clamping), not from the request.
 *
 * Register scales used below (no datasheet was available; all from source):
 *   ES8388  bypass  LI2LOVOL/RI2ROVOL : Linux es8328.c bypass_tlv
 *           (-1500, 300) inverted, 3 bits -> code 0=+6 dB ... 7=-15 dB.
 *           esp-adf es8388.c writes 0x50 for "0db" -> code 2 = 0 dB (agrees).
 *   ES8388  LOUT1VOL..ROUT2VOL        : Linux play_tlv (-3000, 100);
 *           esp-adf comment "0x00:-30dB, 0x1E:0dB, 0x21:3dB". Clamp 0x21.
 *   ES8388  DACCONTROL4/5 (DAC vol)   : Linux dac_adc_tlv (-9600, 50) inverted,
 *           0x00=0 dB .. 0xC0=-96 dB (esp-adf comment agrees).
 *   ES8388  ADCCONTROL1 MicAmp        : Linux mic_tlv (0, 300), 0..8.
 *   AIC3204 HPL/HPR/LOL/LOR gain      : Linux tlv320aic32x4.c tlv_driver_gain
 *           (-600, 100), signed 6-bit (-6..+29), bit6 = mute.
 *   AIC3204 LDACVOL/RDACVOL           : Linux tlv_pcm (-6350, 50), signed 8-bit
 *           -127..+48.
 *   AIC3204 L/R MICPGA VOL            : Linux tlv_step_0_5, 0..0x5f, bit7=off.
 */
#include <math.h>
#include "r5dsp.h"

static float clampf(float x, float lo, float hi)
{
    return x < lo ? lo : (x > hi ? hi : x);
}

float r5_mix_pct_to_db(int pct, bool *mute)
{
    if (pct <= 0) {
        if (mute) *mute = true;
        return R5_MIX_DB_MIN;
    }
    if (mute) *mute = false;
    if (pct > 100) pct = 100;
    if (pct <= 50) {
        return R5_MIX_DB_MIN + (0.0f - R5_MIX_DB_MIN) * (float)(pct - 1) / 49.0f;
    }
    return R5_MIX_DB_MAX * (float)(pct - 50) / 50.0f;
}

uint8_t r5_es_byp_code(float db, float *real_db)
{
    int code = (int)lroundf((6.0f - clampf(db, -15.0f, 6.0f)) / 3.0f);
    if (code < 0) code = 0;
    if (code > 7) code = 7;
    if (real_db) *real_db = 6.0f - 3.0f * (float)code;
    return (uint8_t)code;
}

uint8_t r5_es_outvol_code(float db, float *real_db)
{
    int code = (int)lroundf(clampf(db, -30.0f, 3.0f) + 30.0f);
    if (code < 0) code = 0;
    if (code > 0x21) code = 0x21;
    if (real_db) *real_db = (float)code - 30.0f;
    return (uint8_t)code;
}

uint8_t r5_es_dacvol_code(float db, float *real_db)
{
    int code = (int)lroundf(-clampf(db, -96.0f, 0.0f) * 2.0f);
    if (code < 0) code = 0;
    if (code > 0xC0) code = 0xC0;
    if (real_db) *real_db = -0.5f * (float)code;
    return (uint8_t)code;
}

uint8_t r5_es_pga_code(float db, float *real_db)
{
    int code = (int)lroundf(clampf(db, 0.0f, 24.0f) / 3.0f);
    if (code > 8) code = 8;
    if (real_db) *real_db = 3.0f * (float)code;
    return (uint8_t)code;
}

uint8_t r5_aic_drv_reg(int db, bool mute)
{
    if (db < -6) db = -6;
    if (db > 29) db = 29;
    uint8_t v = (uint8_t)(db & 0x3F);   /* 6-bit two's complement */
    if (mute) v |= 0x40;
    return v;
}

uint8_t r5_aic_dac_reg(int halfdb)
{
    if (halfdb < -127) halfdb = -127;
    if (halfdb > 48) halfdb = 48;
    return (uint8_t)(int8_t)halfdb;
}

uint8_t r5_aic_pga_reg(float db, float *real_db)
{
    int code = (int)lroundf(clampf(db, 0.0f, 47.5f) * 2.0f);
    if (code > 0x5F) code = 0x5F;
    if (real_db) *real_db = 0.5f * (float)code;
    return (uint8_t)code;               /* bit7 = 0 -> PGA enabled */
}

void r5_plan_wired(r5_codec_kind_t kind, const r5_wired_req_t *req, r5_wired_plan_t *plan)
{
    for (int s = 0; s < 2; s++) {
        float want_violin = req->vol_db + req->dac_trim_db;
        float want_acc = req->vol_db + req->mix_db + req->side_trim_db[s];
        plan->mute[s] = req->mute[s];
        if (kind == R5_CODEC_ES8388) {
            float out_real, dac_real, byp_real;
            plan->es_outvol[s] = r5_es_outvol_code(req->vol_db, &out_real);
            plan->es_dacvol[s] = r5_es_dacvol_code(want_violin - out_real, &dac_real);
            plan->es_byp_code[s] = r5_es_byp_code(want_acc - out_real, &byp_real);
            plan->violin_db[s] = out_real + dac_real;
            plan->accomp_db[s] = out_real + byp_real;
            plan->aic_drv_db[s] = 0;
            plan->aic_dac_halfdb[s] = 0;
        } else {
            /* AIC3204: the only bypass level control proven by the Linux driver is
             * the HP driver gain (shared with the DAC), so the driver gain sets the
             * accompaniment level and the DAC digital volume compensates for the
             * violin. IN1->HP path gain assumed 0 dB (needs bench measurement). */
            int drv = (int)lroundf(clampf(want_acc, -6.0f, 29.0f));
            int half = (int)lroundf((want_violin - (float)drv) * 2.0f);
            if (half < -127) half = -127;
            if (half > 48) half = 48;
            plan->aic_drv_db[s] = (int8_t)drv;
            plan->aic_dac_halfdb[s] = (int16_t)half;
            plan->violin_db[s] = (float)drv + 0.5f * (float)half;
            plan->accomp_db[s] = (float)drv;
            plan->es_outvol[s] = 0;
            plan->es_dacvol[s] = 0;
            plan->es_byp_code[s] = 0;
        }
        plan->mix_real_db[s] = plan->accomp_db[s] - plan->violin_db[s];
    }
}

float r5_plan_internal_accomp_db(const r5_wired_plan_t *plan, const r5_wired_req_t *req,
                                 bool mix_mute, float cal_db)
{
    if (mix_mute) {
        return -200.0f;
    }
    float m = 0.5f * ((plan->mix_real_db[0] - req->side_trim_db[0]) +
                      (plan->mix_real_db[1] - req->side_trim_db[1]));
    return m + cal_db;
}
