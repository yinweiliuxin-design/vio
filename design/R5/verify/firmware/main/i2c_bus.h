/* Thin wrapper over the ESP-IDF 5.x I2C master driver (codec control bus). */
#pragma once
#include <stdint.h>
#include "esp_err.h"
#include "driver/i2c_master.h"

esp_err_t r5_i2c_init(int sda, int scl, uint32_t hz);
esp_err_t r5_i2c_probe(uint8_t addr7);
esp_err_t r5_i2c_add(uint8_t addr7, i2c_master_dev_handle_t *out);
esp_err_t r5_i2c_wr(i2c_master_dev_handle_t dev, uint8_t reg, uint8_t val);
esp_err_t r5_i2c_rd(i2c_master_dev_handle_t dev, uint8_t reg, uint8_t *val);
void r5_i2c_scan(void);
