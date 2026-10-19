# R5 台架接线（ESP32-S3-DevKitC-1）

> 状态：本接线和固件**只编译过、只做过电脑上的单元测试，还没有在实物上跑过**。第一次上电请限流，先只接开发板和 codec。

## 0. 总图（文字版）

```
               ┌──────────── 5V（USB 供电）──────────────► MAX98357A Vin
 USB 线 ──► DevKitC-1 ──── 3V3 ──► codec 模块 / 运放 / 编码器上拉
 （接“USB”口）   │
               ├─ I2S0：MCLK BCLK WS DOUT DIN ──► codec（ES8388 或 AIC3204）
               ├─ I2S1：DOUT（BCLK/WS 与 I2S0 共用）──► MAX98357A DIN ＋ 蓝牙发射模块 I2S DATA
               ├─ I2C：SDA SCL ──► codec
               ├─ UART1：TX RX ──► 蓝牙发射模块
               └─ 3 个编码器、5 个按键、3 个 LED

 拾音器 ─► 运放缓冲（MCP6002/TLV9062）─► codec ADC-L 输入
                         └─► 第二个运放：SEND 输出口
 伴奏 AUX（3.5mm）─► codec 旁路输入 L/R ＋ 求和进 ADC-R
 codec 耳机输出 ─► 耳机口      codec 线路输出 ─► LINE 口
```

## 1. 供电和地

| 电源 | 来自 | 给谁 | 说明 |
|---|---|---|---|
| USB 5 V | DevKitC-1 的 “USB” 口（GPIO19/20 那个，控制台也走这里） | 开发板自身 | 另一个 “UART” 口这次不用 |
| 5V 脚 | 开发板排针 5V | MAX98357A Vin | 台架用 5 V。**产品里 MAX98357A 由电池/SYS 供电（3.0–4.4 V）**，所以台架上喇叭比产品低电量时更响 |
| 3V3 脚 | 开发板排针 3V3 | codec 模块、运放、蓝牙模块（若它是 3.3 V） | codec 模块若自带稳压器、要求 5 V 输入，按模块说明接 5V |
| GND | 开发板 GND | 所有模块 | 音频地用星形接法：codec 模块的 GND 作为音频中心点，运放、AUX 口、耳机口的地都回到这里；喇叭功放的地单独一根线回开发板 GND |

- 全部逻辑电平 3.3 V。不要把 5 V 信号接到任何 GPIO。
- 喇叭：**4 Ω、28 mm、≥1 W**（台架买两只，一只备用）。接 MAX98357A 的 “+” 和 “−”，两端都**不能**接地（桥式输出）。

## 2. ESP32-S3 引脚总表（两种 codec 相同）

排针位置按乐鑫 DevKitC-1 用户指南，以板子丝印为准。J1 = 左排，J3 = 右排。

| GPIO | 排针 | 功能 | 接到 | 注意 |
|---|---|---|---|---|
| 4 | J1 | I2S0 MCLK（12.288 MHz 输出） | codec MCLK | 线尽量短 |
| 5 | J1 | I2S0 BCLK（3.072 MHz 输出） | codec BCLK ＋ MAX98357A BCLK ＋ 蓝牙模块 BCLK | 一个脚带三个负载，线短，必要时靠 S3 端串 33 Ω |
| 6 | J1 | I2S0 WS/LRCK（48 kHz 输出） | codec LRCK/WCLK ＋ MAX98357A LRC ＋ 蓝牙模块 LRCK | 同上 |
| 7 | J1 | I2S0 DOUT（S3→codec，只有小提琴） | codec DAC 数据输入 | |
| 15 | J1 | I2S0 DIN（codec→S3） | codec ADC 数据输出 | |
| 16 | J1 | I2S1 DOUT（小提琴 + 单声道伴奏） | MAX98357A DIN ＋ 蓝牙模块 I2S DATA | |
| 8 | J1 | I2C SDA | codec SDA | 加 4.7 kΩ 上拉到 3V3（固件也开了内部上拉，但太弱） |
| 9 | J1 | I2C SCL | codec SCL | 同上 |
| 17 | J1 | UART1 TX | 蓝牙模块 RX | 115200，8N1 |
| 18 | J1 | UART1 RX | 蓝牙模块 TX | |
| 10 | J1 | 喇叭关断（开漏） | MAX98357A SD | 固件只会拉低（关断）或松开，**从不输出高电平** |
| 1 | J3 | 编码器 VOL A | | |
| 2 | J3 | 编码器 VOL B | | |
| 42 | J3 | 编码器 VOL 按下 | | |
| 41 | J3 | 编码器 TONE A | | |
| 40 | J3 | 编码器 TONE B | | |
| 39 | J3 | 编码器 TONE 按下 | | |
| 47 | J3 | 编码器 FX A | | |
| 21 | J3 | 编码器 FX B | | |
| 14 | J1 | 编码器 FX 按下 | | |
| 11 | J1 | 按键 PWR | | 短按打印状态，长按 1 s 进/出待机 |
| 12 | J1 | 按键 BT | | 切换 BT 灯，并发送 `bt btn` 设的串口命令 |
| 0 | J3 | 按键 MODE | **就是板上的 BOOT 键，不用接线** | ⚠ 绑定脚：上电/复位时按着会进下载模式 |
| 13 | J1 | 按键 FX | | 效果开/关 |
| 3 | J1 | 按键 MIX | | ⚠ 绑定脚（JTAG 选择，只在烧了对应 eFuse 时起作用）。复位时不要按住 |
| 46 | J1 | LED 电源 | GPIO→1 kΩ→LED→GND | ⚠ 绑定脚，复位时必须为低。**只能这样接**（LED 到地），不能接上拉 |
| 45 | J3 | LED 蓝牙 | GPIO→1 kΩ→LED→GND | ⚠ 绑定脚（决定 flash 电压），复位时为高会**无法启动**。同上，只能 LED 到地 |
| 43 | J3 | LED 输出 | GPIO→1 kΩ→LED→GND | ⚠ 这是 U0TXD，连着板上的 USB-UART 芯片。开机时 LED 会随启动日志闪，正常 |

不能用的脚（固件开机会检查，接错会在日志里报）：
- GPIO19/20：USB D−/D+（控制台就在这里）。
- GPIO35/36/37：模组内部八线 PSRAM（N8R8/N16R8）。
- GPIO38（v1.1）或 GPIO48（v1.0）：板载 RGB 灯。两个都别用。
- GPIO44：U0RXD，被 USB-UART 芯片驱动，不能当输入。

引脚不够用的说明：干净的脚已经全部用完，所以 MODE、MIX、三个 LED 用了绑定脚/串口脚。如果想让 I2S1 用独立的 BCLK/WS（menuconfig → I2S1 clocking 选另外两种），要先腾出两个脚，例如把 `LED_OUT` 和 `SPK_SD` 设为 −1，再把 I2S1 BCLK/WS 设到 10 和 43。所有脚都能在 `idf.py menuconfig → SmartVio R5 bench → Pins` 里改。

## 3. codec 接线

### 3.1 ES8388 模块

ES8388 地址：CE 接 GND = 0x10（固件默认），CE 接高 = 0x11。

| ES8388 模块脚（常见丝印，以手上的板子为准） | 接到 |
|---|---|
| MCLK | GPIO4 |
| SCLK / BCLK | GPIO5 |
| LRCK | GPIO6 |
| DSDIN（DAC 数据输入） | GPIO7 |
| ASDOUT（ADC 数据输出） | GPIO15 |
| CCLK / SCL | GPIO9 |
| CDATA / SDA | GPIO8 |
| CE / AD0 | GND |
| VDD / 3V3 | 3V3（单 3.3 V 是否可行：**需看规格书和模块原理图**） |
| GND | 音频中心地 |
| LINPUT1（LIN1） | 拾音缓冲器输出（经 10 µF 隔直） |
| LINPUT2（LIN2） | AUX L（经 1 µF 隔直；模块上已有电容就直连） |
| RINPUT2（RIN2） | AUX R（经 1 µF 隔直） |
| RINPUT1（RIN1） | AUX 求和点（见 4.2）经 1 µF 隔直 |
| LOUT1 / ROUT1 | 耳机口 L / R（模块没有隔直电容就各串 100–220 µF，负极朝耳机） |
| LOUT2 / ROUT2 | LINE 口 L / R（各串 10 µF 隔直＋ 100 Ω） |

ES8388 的 ADC 输入只能选一路，不能在芯片里把 AUX L+R 加起来，所以 RINPUT1 需要片外求和（见 CODEC-FINDINGS.md ②）。

### 3.2 TLV320AIC3204 模块

I2C 地址 0x18。

| AIC3204 脚 | 接到 |
|---|---|
| MCLK | GPIO4 |
| BCLK | GPIO5 |
| WCLK | GPIO6 |
| DIN（MFP1） | GPIO7 |
| DOUT（MFP2） | GPIO15 |
| SCL | GPIO9 |
| SDA | GPIO8 |
| RESET | 10 kΩ 上拉到 3V3（模块已有就不用）。固件用软件复位 |
| IOVDD | 3V3 |
| LDOIN / AVDD / DVDD | **按模块原理图**。若模块只引出 3.3 V（没有 1.8 V 稳压器），要在 menuconfig 打开 `R5_AIC_LDO_ENABLE`（和 `R5_AIC_LDOIN_18_36`）。拿不准就先别开：开错可能和外部稳压器打架 |
| GND | 音频中心地 |
| IN3_L | 拾音缓冲器输出（经 10 µF 隔直） |
| IN1_L | AUX L（隔直电容 1，1 µF） |
| IN2_L | AUX L（**另一个**隔直电容 2，1 µF）—— 同一个 AUX L 信号分两路进芯片 |
| IN1_R | AUX R（1 µF 隔直） |
| HPL / HPR | 耳机口 L / R（AIC3204 耳机输出带共模电压，需 100–220 µF 隔直，模块已有就不用） |
| LOL / LOR | LINE 口 L / R（10 µF 隔直）。⚠ 按 Linux 源码这里**只有 DAC（小提琴），没有伴奏旁路** |

AIC3204 线路输出的变通接法（测试 ③ 时需要伴奏也出现在 LINE 口）：用一个双刀开关，把 LINE 口从 LOL/LOR 切到 HPL/HPR（每路串 1 kΩ 再隔直）。这样 LINE 和耳机是同一个信号。规格书确认后再改。

## 4. 模拟前端

### 4.1 拾音缓冲器（运放 A）和 SEND 缓冲器（运放 B）

运放：**MCP6002**（DIP-8，好插面包板）或 **TLV9062**（SOIC，焊在转接板上）。都是 CMOS 输入、轨到轨、单电源，可用 3.3 V（也可 5 V）。**不要用 TL072**，它在 3.3–5 V 单电源下不能正常工作。

引脚（标准双运放排列，焊接前对照数据手册确认）：1 = A 输出，2 = A 反相输入，3 = A 同相输入，4 = 地，5 = B 同相输入，6 = B 反相输入，7 = B 输出，8 = 电源。

接法（文字版）：
1. 电源：8 脚接 3V3，4 脚接地。8 脚到地就近放 100 nF。
2. 中点偏置 VREF：3V3 → 100 kΩ → VREF → 100 kΩ → GND；VREF 到地再放 10 µF ＋ 100 nF。VREF ≈ 1.65 V。
3. 输入：拾音器插座尖端 → 47–100 nF 薄膜电容（隔直）→ 节点 IN。IN 经 **1–10 MΩ** 接 VREF（给同相端偏置，电阻越大，压电拾音器低频越好；10 MΩ 配 47 nF 截止约 0.3 Hz）。可选：IN 前串 1 kΩ 限流，IN 到 3V3/GND 各一只小信号二极管做保护。插座套管接音频地。
4. 运放 A 接成电压跟随器：3 脚 = IN；1 脚和 2 脚直接相连。
5. 输出：1 脚 → 10 µF（正极朝运放）→ codec 拾音输入（ES8388 LINPUT1 / AIC3204 IN3_L）。
6. 运放 B 做 SEND 缓冲：5 脚接 1 脚（A 的输出）；7 脚和 6 脚相连（跟随器）；7 脚 → 10 µF → 100 Ω → SEND 插座尖端；SEND 插座尖端到地放 100 kΩ（让隔直电容放电）。
7. 余量：3.3 V 供电时输出最大约 3.2 Vpp。用力拉弓若在示波器上看到 1 脚削顶，改用 5 V 给运放供电（MCP6002 最高 6 V，TLV9062 最高 5.5 V），codec 输入那边加分压。

### 4.2 AUX 输入（3.5 mm TRS 立体声）

尖 = L，环 = R，套 = 地（接音频中心地）。

ES8388：
- AUX L → 1 µF → LINPUT2；AUX R → 1 µF → RINPUT2（旁路）。
- 求和：AUX L → 10 kΩ → 节点 S；AUX R → 10 kΩ → 节点 S；S → 1 µF → RINPUT1。S 点电压约 (L+R)/2。
- 两只 10 kΩ 会让 L、R 之间有一点串扰（音源内阻越小越好，手机/声卡耳机口一般没问题）。更干净的做法：再用一只 MCP6002 做反相加法器（两只 10 kΩ 输入、10 kΩ 反馈、同相端接 VREF）。RINPUT1 的输入阻抗**需看规格书/实测**。

AIC3204：
- AUX L → 1 µF → IN1_L，同时 AUX L → 另一个 1 µF → IN2_L。
- AUX R → 1 µF → IN1_R。
- 求和在芯片里做（P1 R55），不需要外部电阻。

### 4.3 输出口

- 耳机口（3.5 mm TRS）：尖 = 左，环 = 右，套 = codec 地。
- LINE 口（3.5 mm TRS）：同上。
- 测试用 16 Ω 和 32 Ω 两种耳机。

## 5. MAX98357A（Adafruit #3006）

| 板子脚 | 接到 | 说明 |
|---|---|---|
| LRC | GPIO6 | 与 codec WS 共用（同一时钟） |
| BCLK | GPIO5 | 与 codec BCLK 共用 |
| DIN | GPIO16 | I2S1 数据（L = R = 小提琴 + 单声道伴奏） |
| GAIN | 悬空 | Adafruit 说明里悬空是 9 dB。改 GAIN 接法后**必须重新做 `spk cal`**（未用规格书核对） |
| SD | GPIO10 | 固件开漏：拉低 = 关断；松开 = 由板上的上拉决定声道。按 Adafruit 说明，Vin = 5 V 时板上 1 MΩ 上拉选的是 (L+R)/2（**需看 Adafruit 指南确认**） |
| GND | GND | 单独一根线回开发板 GND |
| Vin | 5V | 台架 5 V；产品是电池/SYS 3.0–4.4 V |
| + / − | 4 Ω 喇叭 | 都不能接地 |

产品设计提醒：SD 的上拉分压和电源电压有关。Vin 降到 3.0–4.4 V 时，同一个上拉得到的 SD 电压不同，可能不再是 (L+R)/2。产品原理图要单独确定 SD_MODE 的接法。I2S1 两个声道数据相同，所以选左、右或 (L+R)/2 声音一样，只有“关断”需要避免。

## 6. 蓝牙发射模块（型号未定，通用脚名）

| 模块脚 | 接到 | 说明 |
|---|---|---|
| I2S BCLK / SCK | GPIO5 | 共用 |
| I2S LRCK / WS | GPIO6 | 共用 |
| I2S DATA / DIN / SDIN | GPIO16 | 共用 |
| I2S MCLK（若模块必须要） | GPIO4 | 只有模块要求 256 fs MCLK 时才接；这根线已带 codec，线要短 |
| UART RX | GPIO17 | |
| UART TX | GPIO18 | |
| VCC | 模块要求的电压（多为 3.3 V） | 若是 5 V 模块，确认它的 I/O 是 3.3 V 电平 |
| GND | GND | |

I2S1 格式：48 kHz，飞利浦 I2S，立体声，每声道 32 位槽（BCLK = 64 × 48 kHz = 3.072 MHz），因为它和 codec 共用 BCLK/WS。若模块只认 16 位槽（BCLK = 32 fs），在 menuconfig 把 I2S1 clocking 改成 `EXT_MCLK` 并打开 `R5_I2S1_16BIT`，同时给 I2S1 另配 BCLK/WS 脚（见第 2 节末）。模块的命令集未定，固件只透传串口文字（`bt send ...`）。

## 7. 编码器、按键、LED

- 编码器（EC11 类）：A、B 两脚接 GPIO，中间 C 脚接 GND；按键两脚一端接 GPIO，一端接 GND。固件开了内部上拉。建议 A、B 各加 10 kΩ 上拉到 3V3 和 10 nF 到地（去抖）。固件按“每格 4 个计数”算；如果转一格变化 2 步或半步，说明编码器型号不同，在台架记录里写下来。
- 按键：一端接 GPIO，一端接 GND。
- LED：GPIO → 1 kΩ → LED 正极，LED 负极 → GND。GPIO45、46 **只能**这样接。

## 8. 上电检查顺序

1. 只接 USB：控制台出现 `r5>`，看开机日志里有没有 `PIN CLASH` 报错。
2. 接上 codec：`codec` 应显示对应地址 `ACK`；`i2cscan` 能扫到 0x10 或 0x18。
3. 用示波器看 GPIO4（12.288 MHz）、GPIO5（3.072 MHz）、GPIO6（48 kHz）。
4. 再接运放、AUX、耳机，最后接喇叭和蓝牙模块。
