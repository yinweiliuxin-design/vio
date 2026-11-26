/* NimBLE GATT server "SmartVio-R5-bench" (CPU / RF coexistence load for tests). */
#pragma once
#include "esp_err.h"
esp_err_t ble_start(void);
void ble_params_changed(void);   /* notify subscribed centrals (any task) */
void ble_status_print(void);
