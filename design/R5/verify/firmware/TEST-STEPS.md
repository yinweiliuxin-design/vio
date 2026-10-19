# R5 台架测试步骤

> 固件状态：**只编译过、只做过电脑单元测试，没有在实物上运行过**。第一次上台架时，先做第 0 节，任何一步结果不对就停下来记录，不要往下硬测。

每一步都按同样的格式写：**接什么 → 输入什么命令 → 应该看到什么 → 怎么记录**。
控制台：开发板 “USB” 口，`idf.py -p <端口> monitor`，或任何串口终端（USB-Serial-JTAG，波特率无所谓）。输入 `help` 看全部命令。

## 记录表（每次测试复制一份）

| 项目 | 日期 | codec（ES8388/AIC3204） | 固件版本（开机第一行） | 条件 | 结果数值 | 通过/不通过 | 备注 |
|---|---|---|---|---|---|---|---|

需要的仪器：示波器（或 USB 声卡 + 电脑录音软件）、真有效值万用表、USB 功率计、信号发生器或手机播放测试音（1 kHz、440 Hz、500 Hz 单声道/单边文件）、16 Ω 和 32 Ω 耳机各一副、4 Ω 喇叭（台架买两只，一只备用）、5 副主流蓝牙耳机、装了 nRF Connect 的手机。

---

## 0. 准备

1. 按 WIRING.md 接线。先只接开发板和 codec。
2. 烧录（见 README.md），打开控制台，复位。
   - 应看到：`SmartVio R5 bench firmware ...`、`I2S running: 48 kHz, 64 frames x 3 DMA buffers`、codec `initialised`、`ready`。
   - 不应看到：`PIN CLASH`、`not answering`。
3. `codec` → 你接的那颗芯片显示 `ACK`。`i2cscan` → 能扫到 0x10（ES8388）或 0x18（AIC3204）。
4. `status` → 把整段输出拷进记录（这是本次测试的配置快照）。
5. 示波器量：GPIO4 = 12.288 MHz，GPIO5 = 3.072 MHz，GPIO6 = 48 kHz。
6. `reg dump` → 拷进记录。

记录：开机日志、`status`、`reg dump` 全文。

---

## 1. 有线耳机延迟 ≤ 10 ms

接什么：
- 一根 3.5 mm 线，一头插耳机口，另一头只把**左声道**接到拾音输入（运放缓冲器输入端）。拔掉 AUX。
- 不接耳机。

命令：
```
vol 70
pga L 0
lat 10
```

应该看到：
- 每次一行 `#n: xxx samples = x.xxx ms (snr ...)`，snr 应大于 8。
- 一行理论值：`theoretical buffering: ... = 4.00..5.33 ms`（默认 64 帧 × 3 个 DMA 缓冲）。理论值**不含** codec ADC/DAC 数字滤波延时。
- 最后 `measured round trip: min .. avg .. max .. ms -> PASS (limit 10 ms)`。

找不到脉冲（`no click found`）时：把 `vol` 调大或 `pga L` 调大，确认线接在左声道。

不通过时：在 menuconfig 把 `Frames per DMA buffer` 改成 32，或 `DMA buffers` 改成 2，重新编译再测，并记录 `load` 是否还通过（第 2 节）。

记录：10 次的 min/avg/max、理论值、当时的块大小和缓冲个数。测得值减去理论值 ≈ codec 滤波延时，单独记一列。

---

## 2. 双核 CPU ≤ 70%（效果 + 调音器 + BLE 全开），1 小时无断音

接什么：拾音输入接信号源（小提琴或信号发生器 440 Hz），AUX 播放音乐，耳机、喇叭、蓝牙模块都接上并配好一副蓝牙耳机。

命令：
```
fx on
fx 60
tuner on
out all
```
手机 nRF Connect 连接 `SmartVio-R5-bench`，打开 Battery Level、两个 R5 特征的通知（Notify），并每隔几秒写一次参数特征（4 字节，例如 `46 32 3C 32`）。

BLE 特征一览：
| 服务 / 特征 | UUID | 格式 |
|---|---|---|
| Battery Service / Battery Level | 0x180F / 0x2A19 | 1 字节，假数据（87% 起，每分钟减 1） |
| R5 服务 | 5a0e5000-7e4b-4c1e-9c2a-52355f425231 | |
| 输出模式（读/写/通知） | 5a0e5001-7e4b-4c1e-9c2a-52355f425231 | 1 字节：0 hp，1 spk，2 bt，3 spk+bt |
| 参数（读/写/通知） | 5a0e5002-7e4b-4c1e-9c2a-52355f425231 | 4 字节：vol、tone、fx、mix，各 0–100 |

先跑 1 分钟看数：
```
load 60
```
然后正式跑 1 小时：
```
load 3600
```

应该看到：
- 每 10 秒一行：core0、core1 占用，音频任务 avg/max（µs）和块周期（默认 1333 µs），`drop rx/tx0/tx1` 和 `err` 计数。
- 结束时：`core0: ... -> PASS`、`core1: ... -> PASS`（每个核最大窗口 ≤ 70%）、`dropouts/underruns: 0 -> PASS`。
- 音频任务 max 应明显小于块周期（建议 < 70%）。
- 同时用耳朵听耳机、喇叭、蓝牙耳机：1 小时内不应有咔哒声、断音。

记录：最后的 summary 全文、任务列表、听到的问题（时间点）。注意：计数器看的是 I2S 层面的断流；蓝牙耳机里的断音要靠耳朵记（见第 5 节）。

---

## 3. 信号路由 ①–⑥

先确认通用条件：`mix 50`、`vol 70`、`fx off`（避免混响干扰测量）、`out all`。**AIC3204 另外输入 `hp 6`**：它的旁路电平就是耳机驱动增益，最低只能到 −6 dB，有线总音量太低时 `byp`、`mix` 会被卡在下限（`status` 里能看到实际值）。用示波器或 USB 声卡测各输出口。测试音建议：拾音输入 440 Hz，AUX L 1 kHz，AUX R 500 Hz。

### ① 两路 ADC，48 kHz / 24 位，模拟增益 0 到 ≥ +24 dB

1. 拾音输入接 440 Hz、约 50 mVrms；AUX 不接。
2. `pga L 0`，`level 3` → 记下 L 的 rms。
3. `pga L 12`，`level 3` → L 应比上一步大约 12 dB。
4. `pga L 24`，`level 3` → 再大约 12 dB（注意别削顶）。
5. AUX 接 1 kHz，对右声道重复：`pga R 0/12/24`。
6. 拾音输入对地短路，`level 5` → 记下 L 的 rms（底噪，dBFS）。

应该：每步增益差在 ±1 dB 内。ES8388 步进 3 dB、最大 24 dB；AIC3204 步进 0.5 dB、最大 47.5 dB（`pga L 30` 也能设）。

### ② AUX L+R 求和进右 ADC

1. AUX 只在 L 放 1 kHz（R 静音）：`level 3` → 记 R 的 rms = A。
2. 只在 R 放 1 kHz：`level 3` → 记 R 的 rms = B。
3. L、R 同时放同一个 1 kHz（同相、等幅）：`level 3` → 记 = C。

应该：A ≈ B（差 < 1 dB）；C ≈ A + 6 dB（同相相加）。ES8388 的求和在片外电阻上做；AIC3204 在芯片里做（P1 R55）。若 A、B 差很多，检查求和电阻或 `reg r 1:55`（AIC）。

### ③ 伴奏模拟旁路到耳机和线路，左右独立，可调可静音

1. AUX 只在 L 放 1 kHz。拾音输入短路。
2. 量耳机 L、耳机 R、LINE L、LINE R。
   - 应该：耳机 L 有，耳机 R 没有（< −60 dB）；LINE L 有（ES8388）。**AIC3204 的 LOL/LOR 按源码没有旁路，LINE 应该没有伴奏**——如实记录，这是已知问题（见 CODEC-FINDINGS.md）。
3. `byp L -6` → 耳机 L 降约 6 dB（ES8388 3 dB 一档；AIC3204 是改耳机驱动增益，同时用 DAC 音量补偿小提琴）。`status` 会显示实际值。
4. `byp mute L 1` → 耳机 L 的 1 kHz 消失。`byp mute L 0` 恢复。`byp L 0` 恢复。
5. AUX 改到只在 R，对右边重复 2–4。

### ④ DAC 和旁路在输出混音器里相加

1. AUX L 放 1 kHz，同时 `dactone -20 440`（DAC 送 440 Hz）。
2. 耳机 L：应同时有 1 kHz 和 440 Hz（用示波器 FFT 或声卡频谱看）。
3. LINE L：ES8388 应两个都有；AIC3204 只有 440 Hz。
4. `dactone off`。

### 伴奏“不重复”、MIX 一致（核心）

1. AUX L、R 都放同一首音乐（或 1 kHz）。拾音输入短路。`dactone off`。
2. `mix 0` → 耳机、LINE、喇叭、蓝牙**全部**没有伴奏。这一步证明 DAC 里没有伴奏（否则 mix 0 时耳机里还会有）。
3. `mix 50` → 耳机有立体声伴奏；喇叭和蓝牙有单声道伴奏。
4. 依次 `mix 25`、`mix 50`、`mix 75`、`mix 100`，每一步：
   - 记 `status` 里的 `mix ... dB` 和 `I2S1 mono accompaniment gain ... dB`（两个数应该相等）。
   - 用 1 kHz 测耳机 L 电平和喇叭（或蓝牙模块 I2S 录到的）电平。
   - 应该：相邻两步之间，耳机电平变化量和喇叭电平变化量相差 < 1 dB。
5. 再确认“不重复”：耳机里伴奏只有一份——在耳机 L 上看 1 kHz 时，`dactone` 关着、拾音短路，`byp mute L 1` 后应完全消失（如果还剩一点，说明 DAC 里混进了伴奏，**不通过**）。
6. 绝对电平对齐（可选）：调 `mix trim <dB>` 让喇叭里的伴奏和小提琴比例听起来与耳机一致，然后 `save`。

### ⑤ 耳机 16–32 Ω、线路输出、防爆音

1. 插 32 Ω 耳机。`dactone -6 1000`，`vol 100`。示波器看耳机两端：记 Vpp，看有没有削顶。换 16 Ω 再测。
2. LINE 口接 10 kΩ 负载（或声卡输入），记 Vrms。
3. 爆音：戴着耳机（音量调低），依次做：复位开发板、`standby on`、`standby off`、`out hp`/`out spk`。主观记：无 / 轻微 / 明显。也可在示波器上抓单次波形。
4. `dactone off`。

### ⑥ I2C、I2S 从机 48 kHz、单 3.3 V

1. `codec` 显示 ACK；`reg dump` 能读出数（不是全 0x00 或全 0xFF）。
2. 示波器量 LRCK = 48.000 kHz（codec 是从机，时钟全由 ESP32 给）。
3. 记录 codec 模块实际接的电源：只接了 3.3 V，还是另有 1.8 V/5 V。用万用表量 codec 的各电源脚电压。
4. AIC3204 若只接 3.3 V：确认 menuconfig 的 `R5_AIC_LDO_ENABLE` 设置，并记录。

---

## 4. 拾音电平：最大弓压不削顶，正常演奏电平够

接什么：小提琴拾音器 → 缓冲器 → codec。AUX 不接。

命令：
```
level 30
```
边跑边拉：先正常演奏 10 秒，再最大弓压（靠近琴码、ff）10 秒，再拉空弦 G 和 E。

应该：
- 最大弓压：`max peak L` ≤ −3 dBFS，`clipped samples L 0`。
- 正常演奏：L 的 peak 在 −24 到 −12 dBFS 之间（够用）。
- 示波器同时看运放输出（缓冲器 1 脚），不能削顶（3.3 V 供电时最大约 3.2 Vpp）。

调整：削顶就 `pga L` 降一档；太小就升一档。定下后 `save`。
记录：最终 `pga L` 值、正常/最大时的 peak 和 rms、运放输出 Vpp。

调音器顺便检查：`tuner show 20`，拉四根空弦，记读数（G3、D4、A4、E5 和音分）。电脑单元测试里纯音误差 < 0.2 音分，实物看稳定性。

---

## 5. 蓝牙发射模块兼容性：5 副主流耳机，每副 10 分钟无断音

接什么：蓝牙模块按 WIRING.md 第 6 节接 I2S 和串口。

命令：
```
out bt
bt echo on
bt send <模块手册里的命令>
```
固件**不知道**模块的命令集，只透传。配对方法按模块手册。可以 `bt btn <命令>` 把常用命令（如进入配对）绑到 BT 键上。

每副耳机：
1. 配对，记录配对是否一次成功、用时。
2. 拾音和 AUX 都有声音，听 10 分钟（人离开发板 1 m，耳机 3 m 内）。
3. 同时在控制台跑 `load 600`，确认 I2S 层面 0 断流。
4. 记录：耳机型号、模块报告的编码（SBC/AAC/aptX 等，若模块能报告）、听到的断音次数和时间、延迟主观感觉。

建议的 5 副（按手上有的为准）：AirPods 系列、索尼 WH/WF 系列、Bose QC 系列、华为或小米、JBL 或森海塞尔。

---

## 6. BLE + 蓝牙发射共存

接什么：同第 5 节（蓝牙耳机在播），手机 nRF Connect 连着 `SmartVio-R5-bench`。

步骤：
1. 手机打开所有通知，每 1–2 秒写一次参数特征或输出模式特征（改 `vol`/`mix`），持续 10 分钟。
2. 控制台：`load 600`。
3. 同时听蓝牙耳机。

应该：BLE 不掉线（`ble` 显示 connections 1）；蓝牙耳机无断音；`load` 显示 0 断流，两核 ≤ 70%。再把手机拿到 5 m 外重复一次。
记录：距离、断音次数、BLE 是否断开、`load` summary。

---

## 7. 喇叭 1 W 限制（4 Ω）

接什么：4 Ω 喇叭接 MAX98357A +/−。MAX98357A Vin 接 5 V。

⚠ **台架 Vin = 5 V，产品是电池/SYS 3.0–4.4 V。台架上能放的声音比产品低电量时更大**，本节的电平结论只对 5 V 成立；产品上要在 3.0 V、3.7 V、4.4 V 各重测一次。

步骤：
1. `out spk`，`spk ohm 4`，`spk show` → 记默认值（默认按 1 W、4 Ω、0 dBFS 正弦 3.0 Vrms 估算，这个 3.0 V 是**假设**，必须校准）。
2. `spk tone -20` → 用真有效值万用表量喇叭两端交流电压（MAX98357A 是无滤波 D 类输出，普通万用表读数可能偏；最好在喇叭两端并一个 RC 低通再量，或用示波器算 RMS）。
3. `spk cal <量到的 Vrms> -20`，然后 `save`。
4. `spk show` → 显示新的 ceiling（dBFS）。
5. `spk tone 0` → 固件会自动压到 ceiling。量喇叭两端 Vrms，应 ≈ 2.0 V（4 Ω 上 1 W = 2.0 Vrms）。
6. `spk tone off`。拉琴 + 放伴奏，`vol 100`，听有没有明显压缩感，`spk show` 里 `min limiter gain` 反映压了多少。

记录：校准值、ceiling、第 5 步的 Vrms 和算出的功率。

---

## 8. 电流

接什么：USB 功率计串在开发板 USB 线上；需要细分时，用万用表分别串在 codec 3.3 V 电源线和 MAX98357A 5 V 电源线上。

依次测，每种状态稳定 30 秒后读数：
1. `standby on`（BLE 仍在广播）
2. `standby off`，`out hp`，耳机播放
3. `out spk`，`spk tone 0`（1 W 限制下最大）
4. `out all`，蓝牙耳机在播，BLE 已连接

记录：每种状态的 USB 总电流、codec 电流、功放电流。说明：开发板上的 USB-UART 芯片、电源灯等也在耗电，这些数**不等于产品功耗**；功放电流在 5 V 下测得，产品电压不同。

---

## 附：常用命令速查

| 命令 | 作用 |
|---|---|
| `status` | 全部状态和增益计划 |
| `level [秒]` | ADC-L（拾音）/ADC-R（伴奏）峰值、RMS、削顶 |
| `load [秒]` | 两核占用、音频块耗时、断流计数 |
| `lat [次数]` | 回环延迟 |
| `mix <0-100>` | 同时改 codec 旁路和喇叭/蓝牙伴奏 |
| `byp L <dB>`（L/R/LR）、`byp mute L 1`（0/1） | 单边旁路微调/静音 |
| `pga L <dB>`（L/R/LR） | codec 模拟增益 |
| `dac <dB>`、`hp <dB>`、`vol <0-100>` | 有线小提琴微调、有线总音量、总音量 |
| `out hp`（hp/spk/bt/all） | 输出模式 |
| `spk ...` | 喇叭限制、校准、测试音 |
| `dactone <dBFS> [Hz]` / `dactone off` | DAC 测试音 |
| `reg r 0x27`、`reg w 1:12 0x0c`、`reg dump` | 读写 codec 寄存器（AIC3204 写成 页:寄存器） |
| `bt send <文字>`（还有 nocr/hex/baud/echo/btn） | 蓝牙模块串口 |
| `tuner show [秒]` | 调音器读数 |
| `codec use aic`（aic/es/default） | 换 codec（存 NVS，自动重启） |
| `save` | 保存校准 |
