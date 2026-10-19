/* Bluetooth TX module control over UART. The module model is not chosen yet,
 * so this layer only moves bytes: no command set is assumed. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"
esp_err_t btmod_start(int tx_pin, int rx_pin, int baud);
esp_err_t btmod_send(const char *text, bool crlf);
esp_err_t btmod_send_raw(const uint8_t *data, size_t len);
esp_err_t btmod_set_baud(int baud);
void btmod_set_echo(bool on);
/* Text sent when the BT button is pressed (empty = only toggle the BT LED). */
esp_err_t btmod_set_button_cmd(const char *text);
void btmod_button_pressed(void);
const char *btmod_button_cmd(void);
