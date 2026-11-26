#include <stdio.h>
#include "i2c_bus.h"
#include "esp_log.h"

static const char *TAG = "i2c";
static i2c_master_bus_handle_t s_bus;
static uint32_t s_hz = 100000;

esp_err_t r5_i2c_init(int sda, int scl, uint32_t hz)
{
    i2c_master_bus_config_t cfg = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = sda,
        .scl_io_num = scl,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,   /* add 4.7k externally, see WIRING.md */
    };
    s_hz = hz;
    esp_err_t err = i2c_new_master_bus(&cfg, &s_bus);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c_new_master_bus: %s", esp_err_to_name(err));
    }
    return err;
}

esp_err_t r5_i2c_probe(uint8_t addr7)
{
    if (!s_bus) return ESP_ERR_INVALID_STATE;
    return i2c_master_probe(s_bus, addr7, 50);
}

esp_err_t r5_i2c_add(uint8_t addr7, i2c_master_dev_handle_t *out)
{
    i2c_device_config_t dc = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = addr7,
        .scl_speed_hz = s_hz,
    };
    return i2c_master_bus_add_device(s_bus, &dc, out);
}

esp_err_t r5_i2c_wr(i2c_master_dev_handle_t dev, uint8_t reg, uint8_t val)
{
    uint8_t b[2] = {reg, val};
    return i2c_master_transmit(dev, b, 2, 50);
}

esp_err_t r5_i2c_rd(i2c_master_dev_handle_t dev, uint8_t reg, uint8_t *val)
{
    return i2c_master_transmit_receive(dev, &reg, 1, val, 1, 50);
}

void r5_i2c_scan(void)
{
    printf("I2C scan:");
    int n = 0;
    for (int a = 0x08; a < 0x78; a++) {
        if (r5_i2c_probe((uint8_t)a) == ESP_OK) {
            printf(" 0x%02x", a);
            n++;
        }
    }
    printf("%s\n", n ? "" : " (nothing found)");
}
