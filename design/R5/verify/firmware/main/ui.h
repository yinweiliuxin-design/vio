/* Bench UI: 3 rotary encoders (PCNT), 5 buttons, 3 LEDs. */
#pragma once
#include "esp_err.h"
esp_err_t ui_start(void);
void ui_print_state(void);
