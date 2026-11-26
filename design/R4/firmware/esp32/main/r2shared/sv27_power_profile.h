#ifndef SV27_POWER_PROFILE_H
#define SV27_POWER_PROFILE_H

/* Bound to ECO V27-C-2000-1500-499-68100. No normal-charge release. */
#if defined(SV27_HOST_MODEL_ENABLE) && (defined(__arm__) || defined(__XTENSA__) || defined(ESP_PLATFORM))
#error "SV27_HOST_MODEL_ENABLE is forbidden for embedded targets"
#endif
#if defined(SV27_HOST_MODEL_ENABLE)
#define SV27_NORMAL_CHARGE_RELEASED 1 /* HOST TEST ONLY: no flash artifact */
#else
#define SV27_NORMAL_CHARGE_RELEASED 0
#endif
#define SV27_RILIM_OHM 1500u
#define SV27_RITERM_OHM 499u
#define SV27_RTMR_OHM 68100u
#define SV27_PROFILE_ID 0x27C20001u
#define SV27_RISET_OHM 2000u
#define SV27_MONITOR_OHM 10000000u
#define SV27_CHARGE_WORST_MA 491u
#define SV27_SOURCE_GRANT_MA 1500u
#define SV27_DELIVERY_BUDGET_MA 990u
#define SV27_MIN_OVERHEAD_MA 10u
#define SV27_PACK_MAX_MV 4250u
/* <=3.5h only when clock slow error<=1% and final-gate latency<=100ms. */
#define SV27_SESSION_BUDGET_MS 12470000u
#define SV27_INPUT_MAX_AGE_MS 100u

#endif
