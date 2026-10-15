#ifndef SV_PCM1864_H
#define SV_PCM1864_H
#include <stdbool.h>
#include <stdint.h>
typedef struct {
    void *ctx;
    bool (*read)(void *,uint8_t,uint8_t *);
    bool (*write)(void *,uint8_t,uint8_t);
} sv_codec_bus;
/* PCM-01: pickup (VINL1 -> ADC1L) PGA gain, PGA_VAL_CH1_L reg 0x01, 7.1 two's
 * complement, 0.5 dB steps (SLAS831D Table 27: 0x18 = +12.0 dB, 0x28 = +20 dB).
 * AUX L/R (0x02..0x04) stay 0 dB. Change only this constant after measuring. */
#ifndef SV_PCM_PICKUP_PGA_DB
#define SV_PCM_PICKUP_PGA_DB 12
#endif
#define SV_PCM_PICKUP_PGA_REG ((uint8_t)(int8_t)(SV_PCM_PICKUP_PGA_DB*2))
typedef char sv_pcm_pga_range[(SV_PCM_PICKUP_PGA_DB>=-12 && SV_PCM_PICKUP_PGA_DB<=40)?1:-1];
typedef struct {sv_codec_bus bus;uint32_t at,fault,reset_at;uint8_t phase,index,sub,old;bool ready;} sv_pcm1864;
enum {SV_PCM_BUS=1,SV_PCM_READBACK=2,SV_PCM_TIMEOUT=4,SV_PCM_RESERVED=8};
void sv_pcm_start(sv_pcm1864 *,sv_codec_bus,uint32_t now);
/* One bounded register operation per tick; clocks running, outputs muted. */
void sv_pcm_tick(sv_pcm1864 *,uint32_t now);
bool sv_pcm_status(sv_pcm1864 *);
#endif
