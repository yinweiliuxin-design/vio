/* Central parameter store. Every change goes through params_lock/unlock(commit)
 * which recomputes the codec gain plan, writes the codec and publishes the
 * engine parameters, so MIX always moves codec bypass and I2S1 together. */
#pragma once
#include <stdbool.h>
#include "esp_err.h"
#include "r5dsp.h"

typedef enum {
    R5_OUT_HP = 0,      /* wired only (HP/LINE always on); I2S1 silent, speaker off */
    R5_OUT_SPK = 1,     /* + speaker (ceiling active) */
    R5_OUT_BT = 2,      /* + BT module (speaker shut down, no ceiling) */
    R5_OUT_SPK_BT = 3,  /* + speaker and BT (ceiling active, BT gets same data) */
} r5_out_t;

typedef struct {
    int   vol_pct;            /* VOL 0..100, 0 = mute */
    float wired_db;           /* HP/LINE master, follows VOL unless set by `hp` */
    float spk_db;             /* I2S1 master, follows VOL */
    float dac_trim_db;
    int   mix_pct;
    float mix_cal_db;         /* `mix trim`: internal path calibration */
    float side_trim_db[2];
    bool  byp_mute[2];
    float pga_db[2];
    float pga_real_db[2];
    float pickup_gain_db;
    int   tone_pct;           /* 50 = flat */
    float bass_db, treble_db;
    int   fx_pct;
    bool  fx_on;
    r5_out_t out;
    float spk_limit_w, spk_ohm, spk_vrms_fs;
    bool  spk_limit_on;
    bool  standby;
    bool  test_mute;          /* latency test: bypass muted, outputs quiet */
    bool  bt_led;             /* BT LED state (BT button) */
    /* derived on commit (read only) */
    bool  mix_mute;
    float mix_db;
    r5_wired_req_t req;
    r5_wired_plan_t plan;
    float internal_accomp_db;
    float spk_ceiling;
} r5_params_t;

void params_init(void);                       /* defaults + NVS */
void params_engine_initial(r5_engine_params_t *out);
r5_params_t *params_lock(void);
void params_unlock(bool commit);
void params_get(r5_params_t *out);
esp_err_t params_commit_now(void);            /* re-apply everything (e.g. after codec init) */
esp_err_t params_save(void);                  /* calibration values to NVS */

float params_vol_db(int pct);
void  params_set_tone_pct(r5_params_t *p, int pct);
const char *params_out_name(r5_out_t o);
