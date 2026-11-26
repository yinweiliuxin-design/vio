#ifndef SV_PCM_RX_H
#define SV_PCM_RX_H
#include <stdbool.h>
#include <stdint.h>
bool sv_esp_pcm_start(void);
void sv_esp_pcm_gate(bool enabled);
int32_t sv_esp_pcm_read(uint8_t *,int32_t);
uint32_t sv_esp_pcm_underflows(void);
typedef struct {uint32_t version,frames,underflows,overflows,read_errors,buffered,last_input_ms,enabled;} sv_esp_pcm_stats;
void sv_esp_pcm_snapshot(sv_esp_pcm_stats *);
#endif
