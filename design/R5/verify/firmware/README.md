# SmartVio R5 台架验证固件（ESP32-S3）

## 这是什么

在 ESP32-S3-DevKitC-1 上验证 R5 的音频路由、延迟、CPU 负载和蓝牙共存的测试固件。功能：

- I2S0 与 codec 全双工：48 kHz，32 位槽 / 24 位数据，S3 当主机并输出 MCLK（256 fs = 12.288 MHz）。
- codec 两选一：**ES8388** 或 **TLV320AIC3204**。ADC-L = 小提琴拾音，ADC-R = 伴奏单声道（AUX L+R）。伴奏立体声走 codec 内部模拟旁路到耳机/线路；**DAC 里只有处理后的小提琴**。
- I2S1 只发送：小提琴 + 单声道伴奏，同时给 MAX98357A（4 Ω 喇叭）和蓝牙发射模块。I2S1 与 I2S0 同一时钟（见下）。
- 处理：拾音增益、低/高搁架音色、混响（深度可调）、YIN 调音器、喇叭 1 W 数字上限。
- 测量命令：`load`（双核占用、音频块耗时、断流）、`lat`（回环延迟）、`level`（电平/削顶）。
- BLE（NimBLE）GATT 服务 “SmartVio-R5-bench”；蓝牙发射模块串口透传；3 个编码器、5 个键、3 个灯。

## 当前状态（请如实看待）

- ✅ 两种 codec 变体都**编译通过**（ESP-IDF v5.4.3，0 错误 0 警告）。
- ✅ DSP 部分在电脑上做了**单元测试**（`tests/run_host_tests.sh`，全部通过）。
- ❌ **没有在任何实物上运行过**。codec 寄存器序列是按 Linux / esp-adf 源码重写的，没有对照规格书，见 CODEC-FINDINGS.md。
- ❌ 喇叭 1 W 上限里 “0 dBFS 正弦 = 3.0 Vrms” 是假设值，必须按 TEST-STEPS.md 第 7 节校准。

## 文件

| 文件 | 内容 |
|---|---|
| `main/` | 固件：I2S/音频任务、codec 驱动、参数、控制台、UI、BLE、蓝牙模块串口、调音器 |
| `components/r5dsp/` | 纯 C 的 DSP 库（固件和电脑测试共用） |
| `tests/` | 电脑单元测试，`tests/run_host_tests.sh` |
| `build-out/es8388/`、`build-out/aic3204/` | 已编译好的固件和烧录参数 |
| `WIRING.md` | 接线表 |
| `TEST-STEPS.md` | 台架测试步骤 |
| `CODEC-FINDINGS.md` | 两颗 codec 能力核对（只基于源码） |

## 烧录

开发板接 **“USB” 口**（GPIO19/20 那个，控制台也在这里）。端口在 Linux 上一般是 `/dev/ttyACM0`，Windows 上是某个 COM 口。

用已编译好的文件（不需要装 ESP-IDF，只要 `pip install esptool`）：

```
cd build-out/es8388        # 或 build-out/aic3204
python -m esptool --chip esp32s3 -p /dev/ttyACM0 -b 460800 --before default_reset --after hard_reset \
  write_flash --flash_mode dio --flash_size 8MB --flash_freq 80m \
  0x0 bootloader.bin 0x8000 partition-table.bin 0x10000 r5_bench.bin
```

或者在该目录里运行 `./flash.sh /dev/ttyACM0`（内容同上），或 `python -m esptool --chip esp32s3 -p PORT write_flash @flash_args`。

自己编译（ESP-IDF v5.4.x）：

```
idf.py -B build-es8388 -D SDKCONFIG=build-es8388/sdkconfig \
       -D "SDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.defaults.es8388" set-target esp32s3
idf.py -B build-es8388 -D SDKCONFIG=build-es8388/sdkconfig \
       -D "SDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.defaults.es8388" build flash monitor
```
AIC3204 把上面的 `es8388` 全换成 `aic3204`。只用到 IDF 自带组件，不需要联网下载组件。

## 选择 codec

三种方法，任选一种：

1. 直接烧对应目录：`build-out/es8388` 或 `build-out/aic3204`。
2. `idf.py menuconfig → SmartVio R5 bench → Default audio codec`。
3. 运行时在控制台输入 `codec use es` 或 `codec use aic`（存进 NVS，自动重启；`codec use default` 恢复编译时的默认）。两个驱动都编进了固件，所以两个预编译文件其实只差默认值。

开机后 `codec` 会探测两个地址（0x10 和 0x18），告诉你板上实际是哪一颗。

## I2S1 和 I2S0 的时钟

ESP32-S3 **没有 APLL**（IDF 的 soc_caps：I2S 时钟源只有 PLL_F240M、PLL_F160M、XTAL、外部输入）。默认做法：I2S1 当**从机**，它的 BCLK/WS 直接取自 I2S0 驱动的同一对引脚（GPIO 矩阵同时做输入和输出），所以喇叭/蓝牙数据和 codec 用的是完全相同的时钟沿，只多占一个 DOUT 脚。代价是 I2S1 的格式跟 I2S0 一样（32 位槽，BCLK = 64 fs）。menuconfig 里还有两个备选：I2S1 主机、时钟取 I2S0 的 MCLK 引脚（可用 16 位槽）；或 I2S1 主机、同样从 PLL_F160M 分频（频率相同但不锁相）。备选模式需要另配 BCLK/WS 引脚，见 WIRING.md。

## 电脑单元测试

```
tests/run_host_tests.sh
```
只需要 gcc。测试内容：搁架滤波器系数、混音规则（DAC 只有小提琴、I2S1 = 小提琴 + 单声道伴奏、MIX 同时改两条路径且一致）、喇叭上限、调音器（196 / 293.66 / 440 / 659.25 Hz 误差 < ±2 音分）、延迟脉冲检测。

## 已知限制

- AIC3204：按 Linux 源码，线路输出（LOL/LOR）没有伴奏旁路，旁路也没有独立音量（借用耳机驱动增益，最低 −6 dB）。需看规格书。
- ES8388：ADC 输入不能在片内把 AUX L+R 相加，需片外两只电阻求和；PGA 最大正好 +24 dB。
- 喇叭：台架 MAX98357A 用 5 V，产品用电池/SYS 3.0–4.4 V，台架更响。
- 引脚：DevKitC-1 的干净引脚全部用完，MODE 键用了板载 BOOT 键（GPIO0），MIX 键和三个灯用了绑定脚 / UART0 TX，接法见 WIRING.md。
