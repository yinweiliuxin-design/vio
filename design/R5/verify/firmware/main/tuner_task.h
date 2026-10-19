/* Single-voice tuner on the pickup channel (YIN at 12 kHz). */
#pragma once
#include <stdbool.h>
#include "esp_err.h"
esp_err_t tuner_start(void);
void tuner_enable(bool on);     /* compute (default on; part of the CPU load) */
void tuner_show(int seconds);   /* print note/cents for N seconds */
bool tuner_enabled(void);
