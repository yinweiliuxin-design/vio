#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "nvs.h"
#include "btmod.h"

static const char *TAG = "btmod";
#define BT_UART UART_NUM_1
static bool s_started, s_echo = true;
static char s_btn_cmd[64];

static void rx_task(void *arg)
{
    uint8_t buf[128];
    char line[160];
    int n = 0;
    for (;;) {
        int got = uart_read_bytes(BT_UART, buf, sizeof(buf), pdMS_TO_TICKS(50));
        for (int i = 0; i < got; i++) {
            char c = (char)buf[i];
            if (c == '\r') continue;
            if (c == '\n' || n == (int)sizeof(line) - 1) {
                line[n] = 0;
                if (s_echo && n) printf("[BT<] %s\n", line);
                n = 0;
                continue;
            }
            line[n++] = (c >= 0x20 && c < 0x7f) ? c : '.';
        }
        /* flush a partial line after a quiet gap (prompts without newline) */
        if (got == 0 && n > 0) {
            line[n] = 0;
            if (s_echo) printf("[BT<] %s\n", line);
            n = 0;
        }
    }
}

esp_err_t btmod_start(int tx_pin, int rx_pin, int baud)
{
    uart_config_t cfg = {
        .baud_rate = baud,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    esp_err_t e = uart_driver_install(BT_UART, 1024, 512, 0, NULL, 0);
    if (e == ESP_OK) e = uart_param_config(BT_UART, &cfg);
    if (e == ESP_OK) e = uart_set_pin(BT_UART, tx_pin, rx_pin, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (e != ESP_OK) {
        ESP_LOGE(TAG, "UART init: %s", esp_err_to_name(e));
        return e;
    }
    nvs_handle_t h;
    if (nvs_open("r5", NVS_READONLY, &h) == ESP_OK) {
        size_t len = sizeof(s_btn_cmd);
        if (nvs_get_str(h, "btcmd", s_btn_cmd, &len) != ESP_OK) s_btn_cmd[0] = 0;
        nvs_close(h);
    }
    xTaskCreatePinnedToCore(rx_task, "bt_rx", 3072, NULL, 4, NULL, 0);
    s_started = true;
    ESP_LOGI(TAG, "UART%d TX=%d RX=%d %d baud", BT_UART, tx_pin, rx_pin, baud);
    return ESP_OK;
}

esp_err_t btmod_send_raw(const uint8_t *data, size_t len)
{
    if (!s_started) return ESP_ERR_INVALID_STATE;
    int w = uart_write_bytes(BT_UART, data, len);
    return w == (int)len ? ESP_OK : ESP_FAIL;
}

esp_err_t btmod_send(const char *text, bool crlf)
{
    esp_err_t e = btmod_send_raw((const uint8_t *)text, strlen(text));
    if (e == ESP_OK && crlf) e = btmod_send_raw((const uint8_t *)"\r\n", 2);
    if (e == ESP_OK && s_echo) printf("[BT>] %s%s\n", text, crlf ? "\\r\\n" : "");
    return e;
}

esp_err_t btmod_set_baud(int baud)
{
    return uart_set_baudrate(BT_UART, (uint32_t)baud);
}

void btmod_set_echo(bool on) { s_echo = on; }

esp_err_t btmod_set_button_cmd(const char *text)
{
    snprintf(s_btn_cmd, sizeof(s_btn_cmd), "%s", text);
    nvs_handle_t h;
    esp_err_t e = nvs_open("r5", NVS_READWRITE, &h);
    if (e != ESP_OK) return e;
    e = nvs_set_str(h, "btcmd", s_btn_cmd);
    if (e == ESP_OK) e = nvs_commit(h);
    nvs_close(h);
    return e;
}

const char *btmod_button_cmd(void) { return s_btn_cmd; }

void btmod_button_pressed(void)
{
    if (s_btn_cmd[0]) {
        btmod_send(s_btn_cmd, true);
    } else {
        printf("[BT] button: no command configured (use `bt btn <text>`)\n");
    }
}
