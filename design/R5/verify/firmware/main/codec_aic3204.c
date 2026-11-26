/*
 * TI TLV320AIC3204 driver for the R5 bench (I2C, codec = I2S slave).
 *
 * Register numbers, bit fields and the power-up order are re-implemented
 * from (no code copied):
 *   [L]  Linux sound/soc/codecs/tlv320aic32x4.c / .h / -clk.c (torvalds/master)
 *   [T]  Tympan_Library src/control_aic3206.cpp (MIT, TLV320AIC3206 which
 *        shares the AIC3204 register map) - only used where noted.
 * Addresses use the Linux convention AIC32X4_REG(page, reg) = page*128 + reg.
 *
 * Input pin map chosen for the bench (see CODEC-FINDINGS.md):
 *   IN3_L        <- pickup buffer     -> Left MicPGA(+)  via 10k  (P1 R52)
 *   IN1_L, IN2_L <- AUX L (two caps)  -> IN1_L: HPL mixer bypass (P1 R12 b2)
 *                                        IN2_L: Right MicPGA(+) via 20k (P1 R55)
 *   IN1_R        <- AUX R             -> HPR mixer bypass (P1 R13 b2) and
 *                                        Right MicPGA(+) via 20k (P1 R55)
 *   => ADC-R = AUX L + AUX R summed in the MicPGA input mixer.
 */
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "sdkconfig.h"
#include "codec.h"
#include "i2c_bus.h"

static const char *TAG = "aic3204";

#define AIC_REG(p, r) ((uint16_t)((p) * 128 + (r)))

/* page 0 */
#define P0_PSEL      AIC_REG(0, 0)
#define P0_RESET     AIC_REG(0, 1)
#define P0_CLKMUX    AIC_REG(0, 4)
#define P0_PLLPR     AIC_REG(0, 5)
#define P0_NDAC      AIC_REG(0, 11)
#define P0_MDAC      AIC_REG(0, 12)
#define P0_DOSRMSB   AIC_REG(0, 13)
#define P0_DOSRLSB   AIC_REG(0, 14)
#define P0_NADC      AIC_REG(0, 18)
#define P0_MADC      AIC_REG(0, 19)
#define P0_AOSR      AIC_REG(0, 20)
#define P0_IFACE1    AIC_REG(0, 27)
#define P0_IFACE2    AIC_REG(0, 28)
#define P0_IFACE3    AIC_REG(0, 29)
#define P0_DACSPB    AIC_REG(0, 60)
#define P0_ADCSPB    AIC_REG(0, 61)
#define P0_DACSETUP  AIC_REG(0, 63)
#define P0_DACMUTE   AIC_REG(0, 64)
#define P0_LDACVOL   AIC_REG(0, 65)
#define P0_RDACVOL   AIC_REG(0, 66)
#define P0_ADCSETUP  AIC_REG(0, 81)
#define P0_ADCFGA    AIC_REG(0, 82)
#define P0_LADCVOL   AIC_REG(0, 83)
#define P0_RADCVOL   AIC_REG(0, 84)
/* page 1 */
#define P1_PWRCFG    AIC_REG(1, 1)
#define P1_LDOCTL    AIC_REG(1, 2)
#define P1_OUTPWRCTL AIC_REG(1, 9)
#define P1_CMMODE    AIC_REG(1, 10)
#define P1_HPLROUTE  AIC_REG(1, 12)
#define P1_HPRROUTE  AIC_REG(1, 13)
#define P1_LOLROUTE  AIC_REG(1, 14)
#define P1_LORROUTE  AIC_REG(1, 15)
#define P1_HPLGAIN   AIC_REG(1, 16)
#define P1_HPRGAIN   AIC_REG(1, 17)
#define P1_LOLGAIN   AIC_REG(1, 18)
#define P1_LORGAIN   AIC_REG(1, 19)
#define P1_HEADSTART AIC_REG(1, 20)
#define P1_LMICPGAPIN AIC_REG(1, 52)
#define P1_LMICPGANIN AIC_REG(1, 54)
#define P1_RMICPGAPIN AIC_REG(1, 55)
#define P1_RMICPGANIN AIC_REG(1, 57)
#define P1_LMICPGAVOL AIC_REG(1, 59)
#define P1_RMICPGAVOL AIC_REG(1, 60)
#define P1_REFPOWERUP AIC_REG(1, 123)

static i2c_master_dev_handle_t s_dev;
static SemaphoreHandle_t s_mtx;
static int s_page = -1;

static esp_err_t raw_wr(uint8_t reg, uint8_t val) { return r5_i2c_wr(s_dev, reg, val); }

static esp_err_t sel_page(int page)
{
    if (page == s_page) return ESP_OK;
    esp_err_t e = raw_wr(0, (uint8_t)page);   /* register 0 of every page = page select */
    s_page = (e == ESP_OK) ? page : -1;
    return e;
}

static esp_err_t aic_w(uint16_t a, uint8_t v)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    int page = a / 128, reg = a % 128;
    esp_err_t e;
    if (reg == 0) {
        e = raw_wr(0, v);
        s_page = (e == ESP_OK) ? v : -1;
    } else {
        e = sel_page(page);
        if (e == ESP_OK) e = raw_wr((uint8_t)reg, v);
    }
    xSemaphoreGive(s_mtx);
    if (e != ESP_OK) ESP_LOGW(TAG, "write P%d R%d failed: %s", page, reg, esp_err_to_name(e));
    return e;
}

static esp_err_t aic_r(uint16_t a, uint8_t *v)
{
    xSemaphoreTake(s_mtx, portMAX_DELAY);
    int page = a / 128, reg = a % 128;
    esp_err_t e = sel_page(page);
    if (e == ESP_OK) e = r5_i2c_rd(s_dev, (uint8_t)reg, v);
    xSemaphoreGive(s_mtx);
    return e;
}

#define W(a, v) do { esp_err_t _e = aic_w((a), (v)); if (_e != ESP_OK) return _e; } while (0)

static esp_err_t aic_init(void)
{
    if (!s_mtx) s_mtx = xSemaphoreCreateMutex();
    if (!s_dev) {
        esp_err_t e = r5_i2c_add(CONFIG_R5_AIC_I2C_ADDR, &s_dev);
        if (e != ESP_OK) return e;
    }
    s_page = -1;

    /* 1. Software reset. [L] aic32x4_probe(): regmap_write(AIC32X4_RESET, 0x01);
     *    [T] aic_reset() waits 10 ms afterwards. */
    W(P0_PSEL, 0);
    W(P0_RESET, 0x01);
    vTaskDelay(pdMS_TO_TICKS(10));
    s_page = -1;

    /* 2. Clocks. CODEC_CLKIN = MCLK pin, PLL unused ([L] .h CLKMUX fields:
     *    CODEC_CLKIN_MCLK = 0, PLL_CLKIN_MCLK = 0). MCLK = 256*fs = 12.288 MHz.
     *    NDAC=1 MDAC=2 DOSR=128 and NADC=1 MADC=2 AOSR=128 -> 48 kHz.
     *    Checks against [L] aic32x4_setup_clocks(): MDAC*DOSR = 256 >= 32*8
     *    (DAC resource class 8), MADC*AOSR = 256 >= 32*6; DOSR rate
     *    48k*128 = 6.144 MHz inside [2.8, 6.2] MHz (AIC32X4_MIN/MAX_DOSR_FREQ).
     *    Divider registers: bit7 = enable, bits 6:0 = value ([L] AIC32X4_DIVEN). */
    W(P0_CLKMUX, 0x00);
    W(P0_PLLPR, 0x11);          /* PLL off, P=1, R=1 ([L] PLLPR fields) */
    W(P0_NDAC, 0x80 | 1);
    W(P0_MDAC, 0x80 | 2);
    W(P0_DOSRMSB, 0x00);
    W(P0_DOSRLSB, 128);
    W(P0_NADC, 0x80 | 1);
    W(P0_MADC, 0x80 | 2);
    W(P0_AOSR, 128);

    /* 3. Audio interface: I2S, 24-bit word, BCLK and WCLK are inputs (slave).
     *    [L] aic32x4_set_dai_fmt (CBC_CFC -> master bits clear) and
     *    aic32x4_hw_params (AIC32X4_WORD_LEN_24BITS << 4). The S3 sends 64 BCLK
     *    per frame (32-bit slots); the extra 8 LSBs of each slot are ignored. */
    W(P0_IFACE1, (0x00 << 6) | (0x02 << 4));
    W(P0_IFACE2, 0x00);
    W(P0_IFACE3, 0x00);

    /* 4. Processing blocks for fs <= 48 kHz: PRB_P1 / PRB_R1
     *    ([L] aic32x4_configure_rate: prb_tx = prb_rx = 1). */
    W(P0_DACSPB, 1);
    W(P0_ADCSPB, 1);

    /* 5. Power configuration in [L] aic32x4_component_probe() order:
     *    PWRCFG (AVDD weak-link disable), LDOCTL, CMMODE. [T] also writes 0x08
     *    to P1 R1. Whether AVDD comes from the internal LDO or from the board is
     *    board dependent -> Kconfig, see WIRING.md / CODEC-FINDINGS.md. */
    W(P1_PWRCFG, 0x08);         /* AIC32X4_AVDDWEAKDISABLE */
#if CONFIG_R5_AIC_LDO_ENABLE
    W(P1_LDOCTL, 0x01);         /* AIC32X4_LDOCTLEN */
#else
    W(P1_LDOCTL, 0x00);
#endif
#if CONFIG_R5_AIC_LDOIN_18_36
    W(P1_CMMODE, 0x03);         /* AIC32X4_LDOIN_18_36 | AIC32X4_LDOIN2HP */
#else
    W(P1_CMMODE, 0x00);
#endif

    /* 6. MicPGA input routing ([L] *_lpga_p_enum / *_rpga_p_enum fields,
     *    2 bits each: 0=off 1=10k 2=20k 3=40k).
     *    Left  (+): IN3_L 10k  -> bits 3:2 = 01           = 0x04
     *    Left  (-): CM_L 10k   -> AIC32X4_LMICPGANIN_CM1L_10K = 0x40
     *    Right (+): IN1_R 20k (bits 7:6 = 10) + IN2_L 20k (bits 1:0 = 10) = 0x82
     *               two inputs into the same PGA = analog sum AUX L + AUX R;
     *               20k each so the sum is about (L+R)/2 of the 10k gain.
     *    Right (-): CM_R 10k   -> AIC32X4_RMICPGANIN_CM1R_10K = 0x40 */
    W(P1_LMICPGAPIN, 0x04);
    W(P1_LMICPGANIN, 0x40);
    W(P1_RMICPGAPIN, 0x82);
    W(P1_RMICPGANIN, 0x40);
    W(P1_LMICPGAVOL, 0x00);     /* enabled (bit7=0), 0 dB; set later */
    W(P1_RMICPGAVOL, 0x00);

    /* [L] workaround in probe: power the ADC up and down once. */
    W(P0_ADCSETUP, 0xC0);
    W(P0_ADCSETUP, 0x00);

    /* 7. Reference fast charge, 40 ms ([L] AIC32X4_REFPOWERUP_40MS + msleep(40)). */
    W(P1_REFPOWERUP, 0x05);
    vTaskDelay(pdMS_TO_TICKS(40));

    /* 8. Output mixers ([L] hpl/hpr/lol/lor_output_mixer_controls):
     *    HPL: L_DAC (bit3) + IN1_L (bit2)   HPR: R_DAC (bit3) + IN1_R (bit2)
     *    LOL: L_DAC (bit3)                  LOR: R_DAC (bit3)
     *    The Linux driver exposes no analog bypass into LOL/LOR. Start with the
     *    bypass off and all drivers muted (bit6), then power the drivers. */
    W(P1_HPLROUTE, 0x08);
    W(P1_HPRROUTE, 0x08);
    W(P1_LOLROUTE, 0x08);
    W(P1_LORROUTE, 0x08);
    W(P1_HPLGAIN, 0x40);
    W(P1_HPRGAIN, 0x40);
    W(P1_LOLGAIN, 0x40);
    W(P1_LORGAIN, 0x40);
    W(P1_OUTPWRCTL, 0x3C);      /* HPL b5, HPR b4, LOL b3, LOR b2 ([L] DAPM PGA widgets) */

    /* 9. DAC: power L+R (bits 7,6), left data -> left DAC, right -> right
     *    ([L] DAPM "Left/Right DAC" + AIC32X4_LDAC2LCHN | AIC32X4_RDAC2RCHN). */
    W(P0_LDACVOL, 0x00);
    W(P0_RDACVOL, 0x00);
    W(P0_DACSETUP, 0xC0 | 0x10 | 0x04);
    W(P0_DACMUTE, 0x00);        /* clear AIC32X4_MUTEON (0x0C) */

    /* 10. ADC: power L+R ([L] AIC32X4_LADC_EN | AIC32X4_RADC_EN), fine gain unmuted. */
    W(P0_ADCSETUP, 0xC0);
    W(P0_ADCFGA, 0x00);
    W(P0_LADCVOL, 0x00);
    W(P0_RADCVOL, 0x00);

    ESP_LOGI(TAG, "initialised (IN3_L pickup, IN1_L+IN2_L AUX L, IN1_R AUX R)");
    return ESP_OK;
}

static esp_err_t aic_apply_wired(const r5_wired_plan_t *p)
{
    W(P1_HPLROUTE, 0x08 | (p->mute[0] ? 0 : 0x04));
    W(P1_HPRROUTE, 0x08 | (p->mute[1] ? 0 : 0x04));
    W(P0_LDACVOL, r5_aic_dac_reg(p->aic_dac_halfdb[0]));
    W(P0_RDACVOL, r5_aic_dac_reg(p->aic_dac_halfdb[1]));
    W(P1_HPLGAIN, r5_aic_drv_reg(p->aic_drv_db[0], false));
    W(P1_HPRGAIN, r5_aic_drv_reg(p->aic_drv_db[1], false));
    /* line outputs carry the DAC only; same gain keeps the violin level equal */
    W(P1_LOLGAIN, r5_aic_drv_reg(p->aic_drv_db[0], false));
    W(P1_LORGAIN, r5_aic_drv_reg(p->aic_drv_db[1], false));
    return ESP_OK;
}

static esp_err_t aic_set_pga(const float db[2], float real[2])
{
    W(P1_LMICPGAVOL, r5_aic_pga_reg(db[0], &real[0]));
    W(P1_RMICPGAVOL, r5_aic_pga_reg(db[1], &real[1]));
    return ESP_OK;
}

static esp_err_t aic_dac_mute(bool mute)
{
    return aic_w(P0_DACMUTE, mute ? 0x0C : 0x00);
}

static void aic_dump(void)
{
    static const uint16_t regs[] = {
        P0_CLKMUX, P0_PLLPR, P0_NDAC, P0_MDAC, P0_DOSRMSB, P0_DOSRLSB, P0_NADC, P0_MADC, P0_AOSR,
        P0_IFACE1, P0_IFACE2, P0_IFACE3, P0_DACSPB, P0_ADCSPB, P0_DACSETUP, P0_DACMUTE,
        P0_LDACVOL, P0_RDACVOL, P0_ADCSETUP, P0_ADCFGA, P0_LADCVOL, P0_RADCVOL,
        P1_PWRCFG, P1_LDOCTL, P1_OUTPWRCTL, P1_CMMODE, P1_HPLROUTE, P1_HPRROUTE, P1_LOLROUTE,
        P1_LORROUTE, P1_HPLGAIN, P1_HPRGAIN, P1_LOLGAIN, P1_LORGAIN, P1_HEADSTART,
        P1_LMICPGAPIN, P1_LMICPGANIN, P1_RMICPGAPIN, P1_RMICPGANIN, P1_LMICPGAVOL,
        P1_RMICPGAVOL, P1_REFPOWERUP,
    };
    for (size_t i = 0; i < sizeof(regs) / sizeof(regs[0]); i++) {
        uint8_t v = 0;
        esp_err_t e = aic_r(regs[i], &v);
        printf("  P%d R%-3d (%3u) = 0x%02x%s\n", regs[i] / 128, regs[i] % 128, regs[i], v,
               e == ESP_OK ? "" : "  (read error)");
    }
}

const r5_codec_t r5_codec_aic3204 = {
    .name = "TLV320AIC3204",
    .kind = R5_CODEC_AIC3204,
    .addr = CONFIG_R5_AIC_I2C_ADDR,
    .init = aic_init,
    .apply_wired = aic_apply_wired,
    .set_pga = aic_set_pga,
    .dac_mute = aic_dac_mute,
    .reg_read = aic_r,
    .reg_write = aic_w,
    .dump = aic_dump,
    .input_map = "IN3_L=pickup; IN1_L+IN2_L=AUX L (2 caps); IN1_R=AUX R; "
                 "HPL/HPR=headphone (DAC+bypass); LOL/LOR=line (DAC only)",
    .limits = "LINE OUT has no analog bypass in the Linux driver (needs datasheet); "
              "bypass level = HP driver gain >= -6 dB (no separate IN1->HP volume in source)",
};
