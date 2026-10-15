# SmartVio R4 固件修改说明（R3 → R4）

日期：2026-10-15。基线：R3 交付包 `engineering/firmware`（未改动）。

**硬件实测：0 项。** 以下所有结论都来自主机测试、交叉编译和指令级仿真。上板前必须按文末的清单逐项实测。

本目录内容：

| 路径 | 内容 |
|---|---|
| `R3-to-R4.patch` | 统一 diff（`diff -ruN`，相对固件根目录，`patch -p1` 可用）。只含源码，不含 artifacts、vendor-source、handoff 和二进制。已验证：打到 R3 原包副本上，结果与 R4 工作副本逐文件一致。 |
| `src/` | 所有改动和新增的源文件，按原相对路径存放。包括 `build_r4_linux.sh` 和新测试。 |
| `build/` | `smartvio-r4.elf/.bin/.map`，共 2.9 MB。SERVICE 镜像可用脚本重建，不随附。 |

## 1. 构建

### 1.1 Linux 构建脚本 `build_r4_linux.sh`

原 `build.py` 只能在 Windows 上运行：写死了 `E:/codex/...` 路径，主机测试用 tcc，目标机用 arm-none-eabi-gcc 14.2。新脚本做了这些事：

- **目标机**：使用与 build.py 相同的编译选项、链接脚本 `base/stm32/stm32h743vi.ld`、同一批 HAL/CMSIS-DSP 源文件和目标文件列表。供应商源码取自包内 `vendor-source/`：cmsis、st、stm32h7xx-hal-driver-1.11.4、cmsis-dsp-1.16.2。
- **镜像**：生成 `IMAGE.elf/.bin/.hex/.map/.symbols.txt`，以及 SERVICE 变体（`-DSV_DIAGNOSTIC_SERVICE_CLEAR=1`）。
- **主机测试**：用 gcc `-std=c11 -Wall -Werror` 编译并运行全部测试。
  - 唯一偏差：加了 `-Wno-misleading-indentation`。这是 gcc 才有的风格警告，tcc 没有；原测试的单行宏写法会触发它。
  - 去掉了只给 tcc 用的 `-D__GNUC__=9`（gcc 会把重定义报成错误）。
- **i2c-model-device.h**：用内嵌的 Python 移植了 `generate-i2c-test-header.ps1`。注意 PowerShell 的 `-match` 默认不区分大小写，所以 `_Pos/_Msk` 宏也要一并收入。
- **ESP32**：本机没有 ESP-IDF，只对 `esp32/main/r2shared/*.c` 做 `gcc -fsyntax-only` 检查。
- **配置变体**：
  - `EXTRA_CFLAGS="-DHP_DETECT_ACTIVE_HIGH=0"`：耳机检测极性取反。
  - `EXTRA_CFLAGS="-DSV_HW_REV_R4=0"`：为 R3 板编译。
  - 脚本还会另外对 R3 板、`SV_PRODUCT_MODE=0`、`SV_CPU_FAST_MHZ=200`、`HP_DETECT_ACTIVE_HIGH=0` 四种配置做目标机编译检查。

用法：`./build_r4_linux.sh [固件根目录] [输出目录]`。环境变量 `IMAGE` 指定镜像名，默认 `smartvio-r4`。

### 1.2 R3 复现（原包副本，未作任何修改）

工具：gcc 13.3 和 arm-none-eabi-gcc 13.2.1。原包用的是 14.2.1，所以二进制不可能逐字节一致。

- **主机测试**：16 个套件加 `test_r2_charge_enabled_HOST_ONLY` 全部通过，断言数与 `artifacts/build-result.json` 完全相同（例如 legacy_telemetry 274754、test_radio_core 16822819、test_r2_charge 1253299）。
- **BRINGUP ELF 大小**：text 40576 / data 8 / bss 16720。原包为 39792 / 8 / 16720。.text 39904 对 39120，多 2.0%，属于编译器版本差异。
- **SERVICE ELF**：text 41084，原包 40328。
- **符号**：符号集相同，只有内联差异（`abort_transfer.isra.0`，以及 `sv_rf_u32` 没有内联）。.data、.bss、.dma 的布局和地址完全一致。

**结论：R3 构建在 Linux 上可复现。**

### 1.3 R4 构建结果（`arm-none-eabi-size`）

```
   text    data     bss     dec     hex filename
  45264      16   17432   62712    f4f8 smartvio-r4.elf
  45556      16   17432   63004    f61c smartvio-r4-SERVICE.elf
```

- .dma 4128 B，栈预留 8192 B，DTCM 内有余量。
- SHA256：
  - elf `416b22af…1836e626`
  - bin `9cd2ec7b…a269bd92`

### 1.4 主机测试（R4，全部通过）

| 套件 | 结果 / 说明 |
|---|---|
| legacy_telemetry | 274754 断言。按 R3 板常数编译，R4 的常数由 test_r4_product 覆盖 |
| test_foundation | 全部 TEST 通过（R3 板常数） |
| test_radio_core | 16822819 |
| test_diagnostics | 243886 断言，PCM 操作 423 次（新增软件复位检查，R3 板常数） |
| test_audio_contract | 1162838（满幅 /2 不回绕） |
| test_ui | 1233081 |
| test_r2_charge / test_r2_charge_enabled_HOST_ONLY | 1253299 / 1253299 |
| **test_r4_product**（新） | 11 组，4977 断言 |
| **test_r4_product_r3board**（新） | 同一测试按 R3 板编译，4958 断言 |
| test_retry、test_rf_reply | 通过 |
| test_waveforms | 改为 1/2 缩放后的期望值 |
| test_service_clear_0 / _1 | 290 / 331 |
| test_i2c_probe | 159 |
| test_esp_pcm | 14360 |
| **test_safety_inputs** | 13 组，1857 断言（高有效，200 ms） |
| **test_safety_inputs_active_low**（新） | 1857，低有效极性 |
| **test_safety_inputs_r3board**（新） | 1852 |
| ESP32 r2shared 语法检查 | pcm_rx.c、sv_control.c、sv_radio_core.c 通过 |

另外用 unicorn 直接跑 R4 ARM ELF 中的 `sv_frame_encode` 和 `sv_parser_byte`：

- 类型 0x01/0x22/0x30/0x31/0x3B/0x40/0x41/0xA0/0xA1/0xB0 各解析出 1 帧。
- 类型 0x07/0x7F 解析出 0 帧。
- R3 ELF 上 0x30/0x40/0xA0/0xB0 都是 0 帧。

## 2. 逐条修改

格式：发现编号 → 改了什么（文件:函数） → 如何验证。

### 致命 / 高

**FW-PARSER-WHITELIST（致命）**

改动：
- `base/sv_control.c`：新增 `sv_frame_type_known()`。白名单为实际用到的帧类型：1–6、0x20–0x22、0x30–0x3C、0x40–0x43、0x80、0xA0、0xA1、0xB0。
- `sv_parser_byte` 改用这个白名单。
- `esp32/main/r2shared/sv_control.c/.h` 与 base 版逐字节同步，ESP 端也修复。

验证：
- test_r4_product 对全部 30 种类型往返编解码，并检查 CRC 损坏时被拒。
- 对 256 个类型逐一核对白名单。
- 用 main.c `startup_core` 的 0x30 自检帧验证。
- 构造含噪声的 MCU↔ESP 字节流（0x40/A0/41/22/A1/30/B0/43），全部按序解析。
- ARM ELF 仿真（见上）。

**FW-PORT-ENABLE-HP（致命）**

改动：
- 新增 `base/sv_product.c:sv_route_outputs()`，`stm32/main.c` 主循环用它决定输出。
- R3 板（`SV_HW_REV_R4=0`）：耳机 = PA0|PA1|PA3；任何路由只要用到 AUX/RETURN 输入，都加 PA3。
- R4 板：按 ECO E-03 分组，见下文 E-03。
- 原 `test_safety_inputs.c:65` 把错误掩码当成了正确行为。改为断言掩码 11（PA0|PA1|PA3）和 R4 分组位能原样通过安全掩码。

验证：test_r4_product（R4 和 R3 两种板）、test_safety_inputs*。

**FW-NO-CHARGE-PATH（高）**

改动：
- `stm32/main.c:charge_apply()` 加 `sv_product.c:sv_charge_decide()`，取代 V27 的“一次性会话 + 日志”门控。原来那套恒为否决；R4 不再调用它，但代码和测试保留。
- CHARGE_ALLOW（PE14）同时满足以下条件才为 1：
  - VBUS：ADS1115 USB 通道 4.4–5.6 V；
  - 监测帧有效；
  - 无 USB 故障：PE8 TPD2S300 FLT_N、PE9 TPD2S703 FLT_N、PE15 eFuse FLT 都为高；
  - 无 POWER 故障；
  - PACK 在 2.5–4.25 V 之间；
  - 板温（TMP117）0–45 °C；
  - 以上条件连续保持 2 s；
  - 不是 SERVICE 镜像。
- 电芯温度窗口由硬件保证：TPS3700（U1921）通过 R1601/CHARGE_GATE 与 CE 串联，BQ24074 的 TS 脚也会独立停充。固件读不到 CHARGE_GATE，原理图上没有回读通路。
- EN1/EN2 默认为 0/1（EN2=0、EN1=1，即 USB500）。有 USB 故障时回落到 USB100（00）。EN2 永不置 1，因此不会进入 ILIM 1.03 A 模式，也没有做 USB-PD。
- SysTick 保留独立否决：前台超过 100 ms 没有刷新，就拉低 PE14。

验证：test_r4_product 的充电组。覆盖 2 s 资格、否决后重新计时、8 种否决条件各 500 次、SERVICE 镜像全关，以及 EN2 永不为 1。

**FW-RT-BUDGET（高）**

改动：
- `stm32/main.c:caches_on()`：打开 I-cache 和 D-cache。MPU 把以下两块设为 normal non-cacheable，所以 DMA 和闪存写后回读都不需要做 cache 维护：
  - `.dma` 段（D2 SRAM1 0x30000000，128 KB）；
  - Bank2 故障日志扇区（0x081E0000，128 KB）。
- `pll1_start()` / `clocks_slow()` / `cpu()`：快速模式从 HSE 起 PLL1。
  - 默认 `SV_CPU_FAST_MHZ=120`：M6、N117、P4，得 119.808 MHz；VOS2；AXI 119.8 MHz；APB 59.9 MHz；闪存 2 WS。这是按电池预算（ECO 续航部分）选的，不跑 400 MHz。
  - 可选 200：VOS1，196.6 MHz，AHB /2。
  - HSE 或 PLL1 失败时退回 HSI 64 MHz。
  - USART3 和 I2C1 的内核时钟仍取 HSI，BRR 和 TIMINGR 不变。
  - SAI 和 MCO2 仍由 PLL2 提供，audio_hw.c 未改。
- 每次监测 I2C 事务（约 0.47 ms）之后，以及每次 codec 状态读之后，立即调用 `audio_poll()`，即 `sv_audio_hw_service`。原来每个主循环只服务一次。

预算（仿真加推算）：
- 用 unicorn 对 R4 ELF 计数，每半缓冲（64 帧，1.333 ms）的指令数：

  | 路由 | sv_factory_render | sv_audio_measure |
  |---|---|---|
  | HP+音量+音色+FX | 22.1 k | 7.0 k |
  | SPK（含 850 Hz 双二阶） | 25.2 k | 7.0 k |

  加上 RX 拷贝，最坏约 34 k 条指令。
- 119.8 MHz、开 cache、CPI 按 1.0–1.5 估算：0.28–0.43 ms，即 21–32% CPU。
- DMA 所有权窗口为 1.0 ms（`sv_dma_half_free` 要求留 32 字余量）。最坏链路是一次阻塞 I2C 0.47 ms 加渲染 0.43 ms，共 0.90 ms，余量约 10%，**可以放下**。
- 100 MHz 时为 0.51+0.47 = 0.98 ms，几乎没有余量。所以 **120 MHz 是可接受的最低频率**。
- R3 的 64 MHz、7 WS、无 cache（CPI 约 2.5），约 1.3 ms，必然溢出，与发现一致。

上板验收：
- `sv_dma_telemetry.max_cycles` ≤ 54 000 周期（0.45 ms × 119.8 MHz）。
- `ownership_waits` 不增长，且没有 DMA 故障。
- 否则改用 `-DSV_CPU_FAST_MHZ=200` 编译。

**FW-UART-OVERRUN（高）**

改动：
- `stm32/main.c`：`uart_start` 开启 FIFOEN、RXFNEIE、EIE，NVIC 优先级 2。
- 新增 `USART3_IRQHandler`，收到的字节进 512 B 环形缓冲。`uart_service` 从环形缓冲取数。
- ORE/FE/NE/PE 只计数（`sv_r4_diag.rx_errors`），由解析器靠帧头和 CRC 重新同步，不再锁存 PROTOCOL 故障。
- TX 超时只丢弃并计数，也不再算故障。
- PD9（RF_TX）打开内部上拉。这一点同时对应 ECO E-08。

验证：目标机编译，加上解析器流测试。中断时序本身没有实测。

**FW-FAULT-LATCH（高）**

改动：新增产品模式 `SV_PRODUCT_MODE=1`（默认，在 `base/sv_product.h`）。
- 上电即自动 arm：`sv_factory.c:sv_factory_product_arm()` 授予全部路由，输入为实时输入（mode 2），并取消 2 s 和 60 s 的命令超时（`sv_factory_tick` 中的 `!d->product`）。
- 音频跑起来、电位器数据新鲜之后，才打开旋钮和按键 UI（`sv_ui_enable`）。
- 旋钮不再要求先拨到 0 才能拾取，改为自动拾取（`sv_ui.c:auto_pickup`）。
- 任何故障都只是静音（power_off），然后按 1/2/4…30 s 退避重试：
  - 监测故障时重新初始化 I2C 和 ADS1115/TMP117；
  - 电位器故障时重新初始化 ADC；
  - codec 在下次上电时重新配置。
- 稳定 60 s 后清零重试计数。
- Flash 日志改为“历史记录”，上电不再读入成为静音故障。每个故障位每次开机最多写一次；日志写满或损坏也不会静音。
- 产品模式下的板温窗口放宽为 −20–60 °C。USB 端口故障线（PE8/PE9）只影响充电，不再让电池供电的演奏静音。
- `SV_PRODUCT_MODE=0` 时保留 R3 的台架 arm 流程。

验证：test_r4_product 的产品 arm 组（600 s 无命令仍保持 armed；故障后重新 arm 会清除故障）、退避表、目标机两种模式都能编译。

**FW-NO-UVLO（高）+ 任务 3 低电量**

PACK 由 ADS1115 AIN1 测量（MON_BAT：R1705/R1706 分压 → U1702 TMUX → U1703 缓冲；SYS 在 AIN2）。

改动：`sv_product.c:sv_battery_update()`。
- 每帧（约 4 次/s）取一个样本，8 帧 IIR 滤波（约 2 s），<2.0 V 或 >4.5 V 的样本丢弃。
- 低于 3.45 V 告警（LED1 每 2 s 闪一下），高于 3.55 V 解除。
- 只在电池供电时生效：滤波值 <3.30 V 连续 3 s，就有序关机：
  1. `request_off` 静音并 power_off；
  2. `journal_save` 写入未记录的故障。flash 写入要求 PACK ≥3.1 V 或有 USB。R3 和 R4 都没有其他需要保存的用户设置，音量由滚轮决定，路由自动选择；
  3. KILL（PE7）拉低，交给 LTC2954 关机。
- 有 USB 时不会因低压关机。

验证：test_r4_product 的电池组。覆盖：单次负载跌落被滤除、异常读数被忽略、告警及其迟滞、有 USB 不关机、3.29 V 恰好在 3.0 s 关机、中途回升会取消。

**FW-USB-SHUTDOWN-LATCH（高）**

改动：
- `sv_product.c:sv_power_kill()`：KILL 拉低 1.5 s 后如果 MCU 仍在运行，说明是 USB 维持着 V3D。此时释放 KILL，进入“只充电待机”。
- `sv_input_guard.c:sv_input_guard_rearm()` / `safety_inputs.c:sv_safety_rearm()`：清除 PWR 锁存，并重新开始 1 s 的忽略窗口。
- R4 板（ECO E-11）：待机时 PB12（PWR_PB_SENSE，内部上拉）读到低电平 ≥50 ms，且此前已经见过松开，就清除锁存并执行 `NVIC_SystemReset()`（`sv_power_pb_wake`）。复位后看到 SFTRSTF 或按键仍按着，就直接进入演奏，不再进待机。
- 两种板通用：待机中 VBUS 消失而 MCU 仍在运行，说明 LTC 已经开机，此时软件重新初始化进入演奏，不复位。
- 上电时：有 VBUS、不是软件复位、PWR 键也没按，判定为“只因插了 USB 而上电”，直接进入待机。
- R3 板没有 PB12，按 PWR（LTC 已开时的 INT 沿）或任一前面板键唤醒。

验证：test_r4_product 的电源组，包括：KILL 1.5 s、关机那次按键未松开时不唤醒、50 ms 门限、40 ms 抖动不唤醒、R3 板的唤醒规则。test_safety_inputs 的 rearm 组：rearm 后 1 s 内的 INT 被忽略，之后再次生效。

### 中 / 低（改动小的）

**FW-SYSTICK-PRIO（低）**

改动：`systick_start()`，每次 `SysTick_Config` 之后立即 `NVIC_SetPriority(SysTick_IRQn,0)`。HAL_RCC_ClockConfig 内部的 HAL_InitTick 之前先设 `uwTickPrio=0`。

验证：目标机编译。

**FW-HSE-LEFT-ON（低，部分）**

改动：`clocks_slow()` 中，PLL1/2/3 全部关闭后关掉 HSE 和 CSI。

未改：MON_ENABLE 仍然常开。改成周期开关的收益小于 0.2 mA，且 E-02 的高阻分压每次打开要等 100 ms，暂不做。

**FW-UNUSED-STATUS-IO（中，部分）**

已做：
- PC6–PC8 三颗 LED：
  - 开机或按键后显示 5 s 电量（≥3.9 V 三颗，≥3.65 V 两颗，否则一颗）；
  - 充电时最高一颗闪烁；
  - 低电量时 LED1 短闪；
  - 静音或重试期间 LED3 快闪。
- PA9 VBUS_SENSE 与 ADS1115 USB 通道相或，作为 VBUS 检测。
- PE15 eFuse FLT 参与充电否决。
- PB11 CHG_PGOOD_N、PD10 CHG_STATUS_N 写入 `sv_charge_diag`，CHG 用于 LED。

验证：test_r4_product 的 LED 组。

未做：USB 数据口（没有 USB 协议栈）、模式指示 LED。蓝牙 LED 见下一条。

**FW-BT-SECURITY-STREAM（中，部分）**

已做：
- MCU 在 BT 路由且已选定对端时，每 1 s 发一次 0x41 保活，避免 ESP 2 s 后断流（`uart_service`）。
- **产品模式 BT 键（只改 MCU，复用现有帧，ESP 协议不变）**：
  - `sv_factory_buttons`：产品模式下 BT 键在任何路由都有效。原来只在 port==BT 时有效。
  - `sv_ui.c`：BT 键长按门限改为 2 s，其他键仍为 1.5 s。
  - 短按：开关蓝牙（`sv_product.c:sv_bt_key`）。
    - 开：切到 BT 路由，即原有的 RF_ENABLE（PC5）上电 ESP32 加 UART；
    - 关：回到之前的路由（如果耳机已插入，回到 HP）。
    - 打开时如果已知对端，就自动发一次连接帧。
  - 长按 ≥2 s：通过正常的产品命令路径（`command()`，产品会话加序号）发送现有的 0x36 帧。MCU 把它转成 0x40 加对端 BDADDR，ESP 由此打开 60 s 的配对/连接窗口。等 ESP 链路起来后再发；回复超时就重发，直到被接受或超过 8 s。
  - LED2（PC7）只在 BT 路由打开时使用：
    - 常亮：已连接（ESP 状态字节 connected 且 encrypted，3 s 内由 0x41 保活回复刷新）；
    - 1 Hz 慢闪：配对窗口打开中；
    - 灭：未连接。
  - 叠加在电量显示之上。
- 验证：test_r4_product 的 BT 组。覆盖：
  - SPK 路由下短按也会上报；
  - 长按在 2000–2040 ms 之间触发，松开后不再产生短按；
  - 台架模式保留 R3 规则；
  - 无对端时长按不动作；
  - 开、关以及路由的恢复；
  - 全 0 和全 FF 地址被拒；
  - LED 三种状态、60 s 窗口到期，以及与电量显示的叠加。

**限制（如实说明）**：
- ESP 固件没有 inquiry/扫描，处于 NON_DISCOVERABLE，0x40 必须带目标耳机的 BDADDR（`sv_radio_open_local` 拒绝全 0 和全 FF）。
- 所以长按只能对**本次上电内已知的对端**打开配对或连接窗口。对端地址来自任意一次 0x36（台架或 App），只存在 RAM 里，断电即丢失。
- 新用户第一次配对一副从未见过的耳机，仍然需要 ESP 侧增加发现流程，或者有地址来源加持久化。这超出“只改 MCU、不发明 ESP 协议”的范围。

未做：
- Just Works 配对；
- ESP 侧预缓冲和漂移补偿；
- 首次发现新耳机。

这些都需要 ESP-IDF 环境和实机。

**FW-FLASH-ECC-BOOTLOOP（低，部分）**

已做：限制写入频率（每个故障位每次开机最多写一次）；PACK <3.1 V 且无 USB 时不写；日志扇区不经过 cache。

未做：ECC 双错的 BusFault 跳过处理。

**FW-TESTS-NOT-INTEGRATION（中，部分）**

已做：
- 新增 test_r4_product，覆盖帧类型往返、真实字节流、路由与安全掩码、UVLO、充电、电源和唤醒。
- 修正了把错误行为写成断言的测试。
- 在 ARM ELF 上仿真解析器和渲染耗时。

未做：main.c 仍然没有在主机上整体编译（需要完整的寄存器模型），也没有 HIL。

**FW-REPRO-STALE（低，部分）**

已做：提供 Linux 构建脚本，并已复现 R3。

未做：包里仍然没有 ESP32 的 sdkconfig，见 docs-esp-sdkconfig-missing。

**SCH-XDOMAIN-DIRECT 的固件部分 / PCM-03**

改动：`HardFault_Handler` 先关 PLL2（停 SAI 内核时钟和 MCO2），然后把以下引脚设为模拟态，最后才拉低 PE2：

| 引脚 | 写入的 MODER 位 |
|---|---|
| PC9（MCO2） | `GPIOC->MODER\|=3<<18` |
| PE3–PE6（SAI1） | `GPIOE->MODER\|=0xff<<6` |
| PE11（SAI2_SD_B） | `GPIOE->MODER\|=3<<22` |
| PD11–PD13（SAI2） | `GPIOD->MODER\|=0x3f<<22` |
| PD8（USART3_TX → RF_RX） | `GPIOD->MODER\|=3<<16` |

位掩码已逐位核对。正常下电路径（power_off：先关 PC13，再停 SAI/PLL2、引脚设模拟态、停 UART，最后 PE2=0）在 R3 中就是正确的，没有改。

**PCM-01 拾音增益**

改动：
- `sv_pcm1864.h`：新增 `SV_PCM_PICKUP_PGA_DB`，默认 12，即 reg 0x01 = 0x18。按 SLAS831D 表 27 核实：7.1 补码，0.5 dB 一步，0x18 = +12.0 dB，0x28 = +20 dB。范围限制在 −12 到 +40 dB。
- AUX（0x02–0x04）保持 0 dB。
- `sv_factory.c:sv_factory_render`：拾音和 AUX 的 `/16`（−24 dB）改为 `/2`（−6 dB 余量），后面仍有原来的 ±8388607 限幅、`sv_ui_process` 限幅和扬声器峰值上限。

验证：
- test_diagnostics 检查 reg1 = 0x18、reg2–4 = 0。
- test_waveforms 和 test_audio_contract 改为 1/2 的期望值，确认满幅不回绕。

拾音器实际电平未知，首样测量后只需要改这一个常量。

**PCM-02 软件复位**

改动：`sv_pcm1864.c:sv_pcm_tick` 的第 0 步先写 0x00 = 0xFE，等待 ≥2 个 tick（≥1 ms），再写 0x00 = 0x00，然后才开始配置。

验证：test_diagnostics 的芯片模型断言：复位是第 1 次操作，选页 0 是第 2 次；逐个注入总线失败点（423 个）仍然全部报 BUS 故障。

**FW-PCM1864-CLKCFG（info）**

**不改，发现关闭。** reg 0x20 = 0x41，即 SCK_XI_SEL = 01（只用 SCKI）、从模式、CLKDET_EN = 1，与硬件一致（SLAS831D 表 54，`checks/pcm1864-clock-sai.md`）。

### J301 耳机检测（DECISIONS Q7，对应 ECO E-01）

改动：
- `base/sv_input_guard.h`：编译期常量 `HP_DETECT_ACTIVE_HIGH`，默认 1；新增 `sv_hp_inserted_from_pin()`。
- 去抖从 30/50 ms 改为 200 ms，插入和拔出两个方向相同。
- `sv_input_observe_hp`：`hp_inserted` 改为真正的去抖状态，只有原始电平稳定 200 ms 才翻转。所以在尖端接触的接法下，大音量时的毛刺不会断开耳机。
- 扬声器在第一个原始插入沿就切断（SysTick 中拉低 PA2）。拔出后，稳定 200 ms 才允许扬声器。
- `safety_inputs.c:hp_raw()` 按极性读取 PA4。
- 自动路由 `sv_hp_auto_route`：插入时 SPK → HP，拔出时 HP → SPK。LINE、BT 和用户选择的“关”不受影响。开机时如果耳机已插好，直接选 HP。

**如何翻转极性**（首样用万用表量一次，见 DECISIONS Q7 的表）：

| 实测 | R323 | 编译 |
|---|---|---|
| 未插时 5–6 通、插入后断（独立常闭开关） | 装 0 Ω | 默认，`HP_DETECT_ACTIVE_HIGH=1`，插入 = 高 |
| 插入后 5 与尖端（4）导通 | 不装 | `EXTRA_CFLAGS="-DHP_DETECT_ACTIVE_HIGH=0" ./build_r4_linux.sh`，插入 = 低 |

不用脚本时，也可以直接改 `base/sv_input_guard.h` 中的默认值。运行时可从 SWD 读 `sv_r4_diag.hp_active_high` 和 `hp_inserted` 核对。

验证：test_safety_inputs 和 test_safety_inputs_active_low 两种极性都通过。覆盖：200 ms 门限、100 次逐 ms 交替毛刺下耳机路由保持、扬声器不会被打开、插入竞争、32 位回绕。

### R4 硬件 ECO 对应（单一配置头 `base/sv_hw_rev.h`，`SV_HW_REV_R4=1` 默认；设为 0 回到 R3 板）

| ECO | 固件改动 | 验证 |
|---|---|---|
| E-02 | PACK/SYS 换算系数 2.65 → 2.687：`sv_telemetry.c:sv_mon_divider_x1000()`，按 ratio×1000/8 µV 计算，R3 结果不变。USB 通道仍为 2.65。上电后监测的 settle 时间改为 100 ms（`SV_MON_SETTLE_MS`）。 | test_r4_product：系数，以及原始码 9826 换算为 3300 mV；legacy_telemetry 按 R3 常数通过 |
| E-03 | PD14 = HP_PORT_ENABLE，PD15 = RET_PORT_ENABLE，推挽输出，复位态为低。路由：耳机只置 PD14；用到 AUX/RETURN 时置 PD15；PA3 只用于 LINE/FX SEND。安全掩码扩到 6 位，耳机组（bit4）只在耳机去抖确认插入时才允许。`sv_audio_emergency_mute` 同时清 PD14/PD15。R3 板构建仍然是 PA3 加耳机的修法。 | test_r4_product 两种板；test_safety_inputs 检查 GPIOD BSRR |
| E-04 | 复位 BSRR 中 EN1 = 1（USB500），EN2 = 0。固件不会把 EN2 置 1。挂起模式（EN2/EN1 = 1/1）不需要，没有实现。 | test_r4_product 检查 `SV_E_BOOT_BSRR` |
| E-08 | PD9 内部上拉（见 FW-UART-OVERRUN） | 编译 |
| E-10 | 无固件改动 | — |
| E-11 | PB12 输入，内部上拉，低有效（见 FW-USB-SHUTDOWN-LATCH） | test_r4_product |
| 续航预算 | 120 MHz + I/D-cache；音频停止后关 HSE（见 FW-RT-BUDGET） | 仿真推算 |

### SWD 诊断

- 新增 `sv_r4_diag`：产品模式、板版本、HP 极性、PLL1 是否起来、CPU 频率、滤波后电池电压、告警和 UVLO 状态、电源状态、恢复次数、历史故障、UART 错误/丢字节/TX 超时、保活次数、耳机状态、LED。
- `sv_charge_diag` 改为 version 3。

## 3. 未修复或未能验证

| 条目 | 原因 |
|---|---|
| FW-PWR-TAP（低） | 未改。LTC2954 的 INT 脉宽和 PDT 强制关机时序没有数据手册，无法安全地做“长按确认”。 |
| FW-RESET-KILL（低） | 未改。复位期间 PE7 高阻，R1302 会把 KILL 拉低。E-11 的 NVIC_SystemReset 唤醒也受此影响：如果按键时 LTC 已经开机，并且已过 KILL 消隐期，复位可能让 LTC 关断。最坏结果是插着 USB 时能开机，拔掉 USB 后断电。需要台架实测；ECO 建议必要时把 R1302 改接 V3D。 |
| 闲置自动关机 | 未做。需要可靠的“有无琴声”判据，属于新功能。UVLO 已经能防止过放。 |
| MON_ENABLE 周期开关、LED 低占空比 | 未做，收益小。 |
| E-02 要求的出厂一点校准 | `sv_mon_cal` 结构已有，但没有校准值存储，属于新功能，列为待办。 |
| USB 数据口；蓝牙首次发现新耳机（ESP 无 inquiry）和对端地址持久化；ESP 端 Just Works / 预缓冲 | 不在本轮范围，且需要 ESP-IDF 和实机。BT 键的开关、配对窗口和 LED 已在 MCU 侧实现，见 FW-BT-SECURITY-STREAM。 |
| ESP32 镜像 | **必须由用户用 ESP-IDF 5.4.3 重新编译。** r2shared/sv_control.c 已改（解析器白名单），但本机没有 ESP-IDF，只做了语法检查。包里的 `artifacts/esp32/*.bin` 仍然是有 bug 的 R3 版本，不能用。sdkconfig 也不在包内（docs-esp-sdkconfig-missing），重编前要先补齐。 |
| 时钟、cache/MPU、USART 中断、PB12 唤醒、充电、UVLO 阈值 | 只通过编译、主机模型和指令仿真验证，**硬件测试 0 项**。 |

## 4. 上板验收清单（首样）

1. SWD 读 `sv_r4_diag.pll1`，确认为 1，`cpu_hz` = 119808000。
2. 三种路由各播放 10 min，`sv_dma_telemetry.max_cycles` ≤ 54 000，`errors` = 0，`ownership_waits` 不增长。
3. 用万用表确定 J301 的极性，并决定 R323 装不装。插拔 20 次，同时在 0 dBFS 下播放，检查无误判。
4. USB500 端口上边充电边播放，输入电流 ≤500 mA；`sv_charge_diag.allow` = 1；NTC 超出窗口时 CHG 熄灭。
5. 用可调电源模拟电池：3.45 V 时 LED1 闪；3.30 V 保持 3 s 后关机，并且 KILL 生效。
6. 插 USB → 按 PWR 关机 → 进入待机并继续充电 → 再按 PWR 能开机；拔掉 USB 后仍然开着。
7. 测拾音电平，决定 `SV_PCM_PICKUP_PGA_DB`。
8. 用 ESP-IDF 重编 ESP32，测 MCU↔ESP 握手（0x40/0xA0）和 BT 保活。
9. BT 键：
   - 短按开关 BT，LED2 跟随；
   - 先用台架 0x36 给出耳机地址，再长按 2 s，LED2 慢闪，连上后常亮；
   - 检查 ESP 首次 `radio_stack_init` 是否超出 MCU 的 1.5 s 回复超时（现有问题）。
