# 编解码芯片能力核对（按驱动源码）

日期：2026-10-19。范围：SmartVio R5 台架验证用的两颗候选 codec。

**规则**：下面每一条结论都来自开源驱动源码。源码里看不出来的，一律写“需看规格书/实测”。**本核对没有对照任何规格书**，乙方请按规格书复核。

## 1. 读过的源码

| 代号 | 文件 | 地址 | 说明 |
|---|---|---|---|
| [L-AIC] | tlv320aic32x4.c | https://raw.githubusercontent.com/torvalds/linux/master/sound/soc/codecs/tlv320aic32x4.c | Linux 主线，1393 行 |
| [L-AIC-h] | tlv320aic32x4.h | https://raw.githubusercontent.com/torvalds/linux/master/sound/soc/codecs/tlv320aic32x4.h | 寄存器表，263 行 |
| [L-AIC-clk] | tlv320aic32x4-clk.c | https://raw.githubusercontent.com/torvalds/linux/master/sound/soc/codecs/tlv320aic32x4-clk.c | PLL/分频器，497 行 |
| [L-ES] | es8328.c | https://raw.githubusercontent.com/torvalds/linux/master/sound/soc/codecs/es8328.c | Linux 主线（ES8328/ES8388 共用），921 行 |
| [L-ES-h] | es8328.h | https://raw.githubusercontent.com/torvalds/linux/master/sound/soc/codecs/es8328.h | 寄存器位定义，290 行 |
| [A-ES] | es8388.c (audio_hal) | https://raw.githubusercontent.com/espressif/esp-adf/v2.7/components/audio_hal/driver/es8388/es8388.c | 乐鑫 esp-adf v2.7（master 分支已无此路径），582 行 |
| [A-ES-h] | es8388.h (audio_hal) | https://raw.githubusercontent.com/espressif/esp-adf/v2.7/components/audio_hal/driver/es8388/es8388.h | I2C 地址注释 |
| [A-ES-common] | esxxx_common.h | https://raw.githubusercontent.com/espressif/esp-adf/v2.7/components/audio_hal/driver/include/esxxx_common.h | 输入/输出/位宽枚举值 |
| [C-ES] | es8388.c (esp_codec_dev) | https://raw.githubusercontent.com/espressif/esp-adf/master/components/esp_codec_dev/device/es8388/es8388.c | esp-adf master，488 行 |
| [C-ES-reg] | es8388_reg.h | https://raw.githubusercontent.com/espressif/esp-adf/master/components/esp_codec_dev/device/es8388/es8388_reg.h | 寄存器地址 |
| [T] | control_aic3206.cpp | https://raw.githubusercontent.com/Tympan/Tympan_Library/main/src/control_aic3206.cpp | Tympan（MIT 许可），芯片是 **AIC3206**，与 AIC3204 寄存器表相同，只作旁证 |

说明：
- 固件里的寄存器写入是按这些源码**重新写的**，没有复制 GPL 代码。每段写入在 `main/codec_aic3204.c`、`main/codec_es8388.c` 里都注明了依据哪个文件。
- esp-adf 里没有找到 TLV320 驱动。
- AIC3204 寄存器地址写法沿用 Linux：`AIC32X4_REG(page, reg) = page*128 + reg`，下文写成 `P1 R12` 这种形式。

## 2. TLV320AIC3204（I2C 0x18）

### 2.1 六项要求

| 要求 | 结论 | 证据（寄存器 + 文件 + 行号/函数） | 备注 |
|---|---|---|---|
| ① ≥2 路 ADC，48k/24bit，每路模拟增益 0 到 ≥+24 dB | **能** | 左/右 ADC：`SND_SOC_DAPM_ADC("Left ADC"… AIC32X4_ADCSETUP, 7)`、`("Right ADC"… 6)` [L-AIC] 445、429 行。采样率 `SNDRV_PCM_RATE_8000_192000` [L-AIC] 914 行；格式含 `S24_LE` 915–917 行。MicPGA：`"PGA Level Volume"` P1 R59/R60，0…0x5F，0.5 dB 步进 = 0…47.5 dB，左右各自独立 [L-AIC] 292–293 行；bit7 是开关（`"Mic PGA Switch"` 284 行，反相）。另有 ADC 数字细调 −12…+20 dB（`"ADC Level Volume"` 290 行）。 | 增益余量充足。 |
| ② AUX L+R 在芯片输入混音器里模拟相加，进右 ADC | **能（源码结构支持，求和系数需实测）** | 右 MicPGA 正端有 4 个**各自独立**的电阻选择位：IN1_R（P1 R55 bit7:6）、IN2_R（bit5:4）、IN3_R（bit3:2）、IN2_L（bit1:0），每个可选 关/10k/20k/40k [L-AIC] 371–374 行，路由 505–524 行。各位在不同 bit 上，可以同时打开。 | **IN1_L 只能进右 PGA 的负端**（P1 R57 bit5:4，[L-AIC] 376 行），会变成 R−L，不能用。所以 AUX L 要同时接 IN1_L（给旁路）和 IN2_L（给求和）。两路同时接入时增益如何叠加、是否有限制：需看规格书/实测。 |
| ③ AUX 模拟旁路到**耳机**和**线路**输出，左右独立，可调增益和静音 | **耳机：部分能；线路：源码看不出（需看规格书）** | 耳机：HPL 混音器 `"IN1_L Switch"` = P1 R12 bit2，HPR 混音器 `"IN1_R Switch"` = P1 R13 bit2 [L-AIC] 310–318 行，左右各自可开关 = 可静音。增益：源码里**没有单独的旁路音量寄存器**，只有耳机驱动增益 P1 R16/R17（−6…+29 dB，1 dB，bit6 静音）[L-AIC] 275–280 行，它同时作用于 DAC 和旁路。线路：LOL/LOR 混音器只有 `"L_DAC Switch"` / `"R_DAC Switch"`（P1 R14/R15 bit3）[L-AIC] 320–326 行，**没有任何模拟输入到线路输出的通路**。 | 固件做法：旁路电平 = 耳机驱动增益，DAC 数字音量反向补偿，保证小提琴电平不变（`components/r5dsp/src/mixlaw.c`）。限制：旁路最低只能到 −6 dB（驱动增益下限）。规格书里可能还有专门的 IN1→HP 音量寄存器或到线路的通路，但 Linux 驱动没有，**需看规格书**。临时办法：线路输出从 HPL/HPR 取（见 WIRING.md）。 |
| ④ 立体声 DAC，输出混音器把 DAC 和旁路相加（耳机和线路都要） | **耳机：能；线路：只有 DAC** | 同一个 HPL 混音器里 `L_DAC Switch`（bit3）和 `IN1_L Switch`（bit2）可同时开 [L-AIC] 310–313 行，DAPM 路由 482–483 行。左/右 DAC：`AIC32X4_DACSETUP` bit7/bit6，数据通道 `LDAC2LCHN`/`RDAC2RCHN` [L-AIC-h] 183–187 行。 | 线路同 ③。 |
| ⑤ 耳机驱动 16–32 Ω，线路输出，防爆音 | **驱动存在；带载能力需看规格书；防爆音部分** | 有 HPL/HPR/LOL/LOR 四个驱动，电源位 P1 R9 bit5/4/3/2 [L-AIC] 412–427 行。上电时 Linux 写 `AIC32X4_REFPOWERUP_40MS`（P1 R123 = 0x05，参考电压快充 40 ms）[L-AIC] 1030–1032 行。`AIC32X4_HEADSTART`（P1 R20，耳机启动控制）在头文件里有定义 [L-AIC-h] 96 行，但 Linux **没有写它**；[T] 716 行对 AIC3206 写 0b10100101（注释：软切换 200 ms，5 倍时间常数，6k）。 | 16 Ω/32 Ω 输出功率、THD：需看规格书/实测。HEADSTART 各位含义：需看规格书。固件没有写 P1 R20，可用 `reg w 1:20 <值>` 在台架上试。 |
| ⑥ I2C 控制，I2S 从机 48 kHz，单 3.3 V 供电 | **I2C、I2S 从机：能；单 3.3 V：源码支持，电压范围需看规格书** | I2C 地址 0x18：[T] 16 行。从机：`SND_SOC_DAIFMT_CBC_CFC` 时不置主机位（IFACE1 bit3:2 = 0）[L-AIC] 618 行。48 kHz：≤48 kHz 用处理块 PRB_P1/PRB_R1、AOSR 128 [L-AIC] 707–713 行。供电：驱动需要 `iov`，再加 `ldoin` 或 (`dv`+`av`) [L-AIC] 1229–1257 行；只给 `ldoin` 不给 `av` 时自动打开内部 LDO（`AIC32X4_PWR_AIC32X4_LDO_ENABLE`）1290–1291 行；LDOIN 量程位 `AIC32X4_LDOIN_18_36`、耳机由 LDOIN 供电位 `AIC32X4_LDOIN2HP` [L-AIC-h] 203–204 行。 | DVDD 是否也能片内产生、LDOIN=3.3 V 是否允许、耳机在 3.3 V 下的摆幅：需看规格书。具体到买到的模块：看模块原理图。固件用 Kconfig `R5_AIC_LDO_ENABLE` / `R5_AIC_LDOIN_18_36` 开关，默认关。 |

### 2.2 时钟（固件实际配置）

- MCLK = 256 × 48 kHz = 12.288 MHz，由 ESP32-S3 I2S0 输出。
- CODEC_CLKIN 直接选 MCLK（P0 R4 = 0x00，[L-AIC-h] 120–125 行），不用 PLL（P0 R5 = 0x11，PLL 关）。
- NDAC=1、MDAC=2、DOSR=128；NADC=1、MADC=2、AOSR=128 → 12.288 MHz ÷ (1×2×128) = 48 kHz。
- 按 Linux `aic32x4_setup_clocks()` 的约束检查：MDAC×DOSR = 256 ≥ 32×8（DAC 资源等级 8），MADC×AOSR = 256 ≥ 32×6（[L-AIC] 775、786 行）；DOSR 频率 6.144 MHz 在 2.8–6.2 MHz 之内（[L-AIC-h] 231–232 行）。[T] 74 行也写了同样的约束 “MDAC*DOSR/32 >= RC”。
- 接口：I2S，24 位字长（IFACE1 = 0x20），codec 是从机。ESP32 发 32 位槽（每帧 64 个 BCLK），低 8 位不用。

### 2.3 选定的输入脚

| codec 脚 | 接什么 | 去哪里 | 寄存器 |
|---|---|---|---|
| IN3_L | 拾音缓冲器输出 | 左 MicPGA 正端，10 kΩ | P1 R52 = 0x04 |
| CM_L | （内部共模） | 左 MicPGA 负端，10 kΩ | P1 R54 = 0x40（Linux `AIC32X4_LMICPGANIN_CM1L_10K`） |
| IN1_L | AUX L（隔直电容 1） | HPL 混音器（模拟旁路） | P1 R12 bit2 |
| IN2_L | AUX L（隔直电容 2） | 右 MicPGA 正端，20 kΩ | P1 R55 bit1:0 = 10 |
| IN1_R | AUX R | HPR 混音器（旁路）＋ 右 MicPGA 正端 20 kΩ | P1 R13 bit2；P1 R55 bit7:6 = 10 |
| CM_R | （内部共模） | 右 MicPGA 负端，10 kΩ | P1 R57 = 0x40 |
| HPL/HPR | 耳机 | DAC + 旁路 | P1 R12/R13 = 0x0C |
| LOL/LOR | 线路输出 | **只有 DAC** | P1 R14/R15 = 0x08 |

两路 20 kΩ 并联约等于 10 kΩ，和负端 10 kΩ 对称；每路比 10 kΩ 少 6 dB，所以右 ADC 大约是 (L+R)/2 再乘 PGA 增益。实际系数需实测，用 `mix trim` 校准。

## 3. ES8388（I2C 0x10）

### 3.1 六项要求

| 要求 | 结论 | 证据（寄存器 + 文件 + 行号/函数） | 备注 |
|---|---|---|---|
| ① ≥2 路 ADC，48k/24bit，每路模拟增益 0 到 ≥+24 dB | **能（增益刚好到 +24 dB，没有余量）** | 左/右 ADC：ADCPOWER bit5/bit4 [L-ES] 301–304 行。48 kHz 在 12.288 MHz MCLK 的速率表里 [L-ES] 25–27 行；格式含 `S24_LE` 72–76 行。`"Mic PGA Volume"` ADCCONTROL1（0x09）bit7:4 左、bit3:0 右，0…8，3 dB 步进 = 0…+24 dB [L-ES] 208–209 行、`mic_tlv` 102 行。esp-adf 写法相同（左右各占半字节）[A-ES] 517–523 行。 | 最大正好 +24 dB。若拾音器输出很小，可能还要靠前级缓冲器加增益或数字增益（`gain`）。 |
| ② AUX L+R 在芯片输入混音器里模拟相加，进右 ADC | **不能（源码显示是选择器，不是混音器）** | 右 PGA 输入是 4 选 1：`"Line 1"/"Line 2"/"Line 3"/"Differential"`，ADCCONTROL2（0x0A）bit5:4 [L-ES] 247–264 行。差分档是 LINx − RINx（ADCCONTROL3 bit7 选 Line1/Line2）[L-ES] 266–271 行、路由 383–386 行，是**相减**。`"Digital Mono"`（ADCCONTROL3 bit4:3）[L-ES] 273–279、390–394 行是数字混合，而且会占用左声道。 | 改用**片外求和**：AUX L、AUX R 各串 10 kΩ 到一个点，再隔直进 RINPUT1（或用一只运放做反相加法）。见 WIRING.md。 |
| ③ AUX 模拟旁路到耳机和线路，左右独立，可调增益和静音 | **能** | 旁路源选择 DACCONTROL16（0x26）：LMIXSEL bit5:3、RMIXSEL bit2:0，值 1 = Line 2 [L-ES-h] 194–202 行、[L-ES] 216–231 行；esp-adf “LINE 模式”写 0x09（LIN2&RIN2 旁路）[A-ES] 161 行。左混音器：`"Left Bypass Switch"` = DACCONTROL17（0x27）bit6，`"Left Mixer Left Bypass Volume"` = bit5:3，−15…+6 dB，3 dB 步进 [L-ES] 187–188、235 行、`bypass_tlv` 101 行。右：DACCONTROL20（0x2A）bit6、bit5:3 [L-ES] 193–194、244 行。esp-adf 写 0x50 = “旁路 0 dB” [A-ES] 162–163 行，与码值 2 = 0 dB 一致。`Left Out 1` 和 `Left Out 2` 都接在 `Left Mixer` 后面 [L-ES] 430–437 行 → 耳机（OUT1）和线路（OUT2）同时有旁路。 | OUT1 和 OUT2 共用一个混音器，所以两路里 DAC:旁路 的比例相同；两路总音量各自可调（LOUT1VOL 0x2E…ROUT2VOL 0x31，[L-ES] 200–206 行）。注意：Linux 里 DACCONTROL18/19 的音量控件名字和头文件位名对不上（187–194 行 vs [L-ES-h] 209–217 行），固件不用这两个交叉通路（写 0）。 |
| ④ 立体声 DAC，输出混音器把 DAC 和旁路相加（耳机和线路） | **能** | 左混音器的电源位就是 DACCONTROL17 bit7（LD2LO，DAC→左混音器）[L-ES] 336 行，同一寄存器 bit6 是旁路；右混音器 DACCONTROL20 bit7/bit6 [L-ES] 339 行。esp-adf 默认 0x90 = 只有 DAC 0 dB [A-ES] 292–293 行。 | 固件写 0xD0 = DAC + 旁路 0 dB。 |
| ⑤ 耳机驱动 16–32 Ω，线路输出，防爆音 | **有两组输出；能否直接推 16–32 Ω 需看规格书；防爆音部分** | OUT1/OUT2 放大器各有电源位 DACPOWER（0x04）bit5…2 [L-ES-h] 65–73 行。防爆音相关位：DACCONTROL6 bit3 `CLICKFREE` [L-ES-h] 165 行；DACCONTROL3 软斜坡 / 过零 [L-ES-h] 147–148 行；ADCCONTROL7 软斜坡 / 过零 110–111 行；上电先用 VMID 5k 快充 100 ms 再切 50k [L-ES] 689–699 行。 | 哪一组适合直接接耳机、输出功率：需看规格书/实测。固件把 OUT1 当耳机、OUT2 当线路。 |
| ⑥ I2C 控制，I2S 从机 48 kHz，单 3.3 V 供电 | **I2C、I2S 从机：能；单 3.3 V：需看规格书** | I2C 8 位地址 0x20（CE=0）/0x22（CE=1）[A-ES-h] 38 行 → 7 位 0x10/0x11。从机：MASTERMODE（0x08）bit7 `MSC` = 0 [L-ES] 614–621 行、[L-ES-h] 83 行；esp-adf 注释 “CODEC IN I2S SLAVE MODE” [A-ES] 283 行。48 kHz、MCLK/LRCK = 256：DACCONTROL2 = ADCCONTROL5 = 0x02 [A-ES] 290、325 行。电源：Linux 需要 DVDD、AVDD、PVDD、HPVDD 四路 [L-ES] 51–66 行，**没有给电压**。 | 3.3 V 单电源是否可行：需看规格书和模块原理图。 |

### 3.2 选定的输入脚

| codec 脚 | 接什么 | 去哪里 | 寄存器 |
|---|---|---|---|
| LINPUT1 | 拾音缓冲器输出 | 左 PGA → 左 ADC | ADCCONTROL2 bit7:6 = 00 |
| RINPUT1 | AUX L+R 片外求和点 | 右 PGA → 右 ADC | ADCCONTROL2 bit5:4 = 00 |
| LINPUT2 | AUX L | 左混音器旁路（LI2LO） | DACCONTROL16 bit5:3 = 001，DACCONTROL17 bit6 |
| RINPUT2 | AUX R | 右混音器旁路（RI2RO） | DACCONTROL16 bit2:0 = 001，DACCONTROL20 bit6 |
| LOUT1/ROUT1 | 耳机 | DAC + 旁路 | LOUT1VOL/ROUT1VOL |
| LOUT2/ROUT2 | 线路输出 | DAC + 旁路 | LOUT2VOL/ROUT2VOL |

### 3.3 初始化顺序（固件实际做法，来源混合，已标注）

1. DACCONTROL3=0x04（DAC 静音）、CONTROL2=0x50、CHIPPOWER=0x00：[A-ES]/[C-ES] `es8388_open()`。
2. MASTERMODE=0x00（从机）：[L-ES] `set_dai_fmt`。
3. CONTROL1 先写 VMID 5k + ENREF，等 100 ms，再写 VMID 50k + ENREF：[L-ES] `set_bias_level()`；另加 SAMEFS（bit4），来自 esp-adf 的 0x12。**这里两份源码不一致**：esp-adf 写 0x12（没有 ENREF），Linux 工作状态总是带 ENREF。固件跟 Linux。若台架上 ADC/DAC 无声，可试 `reg w 0x00 0x12`。
4. 字长 24 位、I2S：DACCONTROL1=0x00、ADCCONTROL4=0x00（[L-ES] `hw_params` 中 24 位 = 0）。
5. 旁路源、混音器、输出音量、ADC 选择：见上表。
6. CHIPPOWER 写 0xF0 再写 0x00（重启状态机）：[A-ES] `es8388_start()`。
7. esp-adf 还写了 0x35/0x37/0x39（注释“为 8 kHz 关闭内部 DLL”）[C-ES] 238–241 行。这些寄存器 Linux 没有定义，48 kHz 用不上，**固件没有写**。

## 4. 汇总（②③④）

| 要求 | TLV320AIC3204 | ES8388 |
|---|---|---|
| ② AUX L+R 片内模拟求和进右 ADC | 能：右 MicPGA 正端可同时接 IN1_R + IN2_L（P1 R55）。AUX L 需同时接 IN1_L 和 IN2_L。系数需实测。 | 不能：ADC 输入是 4 选 1 选择器（ADCCONTROL2）。改用片外 2 电阻求和进 RINPUT1。 |
| ③ AUX 旁路到耳机 + 线路，左右独立增益/静音 | 耳机：能开关（P1 R12/R13 bit2），增益只能借用耳机驱动增益（−6…+29 dB，和 DAC 共用）。线路：Linux 源码里没有通路 → 需看规格书。 | 能：LI2LO/RI2RO（0x27/0x2A bit6）+ 各自 −15…+6 dB（bit5:3），同时到 OUT1 和 OUT2。 |
| ④ 输出混音器 DAC + 旁路 | 耳机：能。线路：只有 DAC。 | 耳机、线路都能（同一个混音器）。 |

结论：**按源码，ES8388 满足 ③④，但 ② 要片外求和；AIC3204 满足 ②，但 ③④ 在线路输出上缺通路，旁路增益也不独立。** 两边都还有“需看规格书/实测”的项（耳机带载、单 3.3 V、防爆音效果）。台架上用 TEST-STEPS.md 第 3 节逐项实测。

## 5. 需要拿到规格书后再确认的问题清单

1. AIC3204：是否有 IN1→HPL/HPR 的独立音量寄存器（Linux 未用）；LOL/LOR 是否能接模拟旁路或混音放大器；P1 R20（HEADSTART）各位；P1 R10 其它位（共模电压）；LDOIN 3.3 V 时 DVDD 怎么供；耳机 16/32 Ω 输出功率。
2. ES8388：RINPUT1/LINPUT 输入阻抗（决定片外求和电阻取值）；OUT1 能否直接推 16/32 Ω；单 3.3 V 时各电源脚要求；CONTROL1 的 ENREF 位到底该不该置（Linux 与 esp-adf 不一致）。
3. 两者：ADC/DAC 数字滤波器群延时（影响 `lat` 测量结果，固件的“理论值”没有算进去）。
