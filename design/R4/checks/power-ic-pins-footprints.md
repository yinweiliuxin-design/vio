# SmartVio R3 电源 IC 管脚与封装核对（U501 / U1001 / U1101 / U1301 / U1401 / U1921）

日期：2026-10-15　范围：只读核对 R3 包（PKG = scratchpad/pkg/R3）。
数据来源：
- 网表：`PKG/engineering/verification/independent/native-netlist.xml`
- 库封装：`PKG/engineering/project/footprints/SmartVioV25.pretty/*.kicad_mod`、`SmartVioV26.pretty/TI_DDC0006A_Official.kicad_mod`
- 板内封装实例：`PKG/engineering/project/pcb/SmartVio-main-r3-linked.kicad_pcb`、`SmartVio-usb-r2-synced.kicad_pcb`。板内实例与库文件逐焊盘一致，PCB 焊盘网络与网表一致（6 颗 IC 均无错脚）。
- 数据手册：包内没有这几颗 IC 的 PDF（`verification/references` 只有 RF/插座资料），TI/ADI 网站无法直接下载。下文的器件事实来自 TI/ADI 官方文档页面的检索摘录，每条都标了置信度：
  - 「检索确认」：在 TI/ADI 数据手册摘录中看到原文。
  - 「推算」：由检索到的设计示例反推得到。
  - 「记忆」：凭记忆，未能在线核实。

脚本和中间结果：`scratchpad/agents/powerics/`（nets.py、pcbfp.py、fp.py、marks.py）

---

## 1. 结论速览

| 器件 | 管脚对应 | 封装几何 | 外围取值 | 新问题 |
|---|---|---|---|---|
| U501 BQ24074RGTR | 17/17 OK | OK（无散热过孔，已由 PCB-03 记录） | ILIM/ISET/ITERM/TMR 都在数据手册允许范围内 | PWR-05（无 1 脚标记） |
| U1001 TPS259470LRPWR | 10/10 OK，AUXOFF/ITIMER 悬空合法 | 自洽，无法逐尺寸对照 TI 焊盘图 | **ILIM 只有 0.50 A**；OVLO 余量偏小 | **PWR-01**、PWR-07、PWR-05 |
| U1101 TPS63070RNMR | 15/15 OK，FB2 悬空合法 | 功率焊盘阻焊开窗比焊盘小、钢网却按全焊盘开 | 分压 3.296 V OK；输出电容勉强满足 | PWR-03、**PWR-06（纠正 SCH-PSYNC-PFM）**、PWR-08、PWR-05 |
| U1301 LTC2954ITS8-1 | 8/8 OK，-1 版 EN 为高有效开漏 | 焊盘偏宽（0.50 mm，ADI 推荐约 0.40 mm） | ONT 约 0.67 s，PDT 约 3.1 s，合理 | PWR-04 |
| U1401 TPD2S300YFFR | 9/9 OK（C2=VPWR，C3=VM） | OK | VBIAS/VPWR 电容离芯片 11–13 mm | **PWR-02**、PWR-09 |
| U1921 TPS3700DDC | 6/6 OK | 与 TI DDC 推荐焊盘完全一致 | 窗口约 4.8–39.5 °C | PWR-05（无 1 脚标记） |

---

## 2. 逐器件核对

### 2.1 U501 BQ24074RGTR（VQFN-16 RGT 3×3 带 EP），封装 `TI_RGT0016C_BQ24074_EP17`，位置 (60.3, 6.8) F.Cu

| 脚 | 数据手册名 | 网表网络 | 结论 |
|---|---|---|---|
| 1 | TS | PACK_NTC → J501.3 | OK（要求 10 k NTC，电池包 NTC 规格见既有 C13） |
| 2、3 | BAT | PACK_PLUS；C503 10 µF 距芯片约 5 mm | OK（手册要求 4.7–47 µF；检索确认） |
| 4 | CE（低有效，内部约 285 k 下拉） | CHARGE_DISABLE；R503 10k 上拉到 SYS，Q1601 拉低 | OK，默认禁止充电（检索确认） |
| 5、6 | EN2 / EN1 | 分别由 R504 10k、R590 100k 下拉，经 R1604/R1603 1k 接 MCU | OK；00 = USB100 模式（检索确认） |
| 7 | PGOOD（开漏） | PGOOD_TP，R505 100k 上拉 V3D，R1902 1k 接 MCU | OK |
| 8 | VSS | GND | OK |
| 9 | CHG（开漏） | CHG_TP，R506 100k 上拉 V3D，R1903 1k 接 MCU | OK |
| 10、11 | OUT | SYS；C502 10 µF | OK |
| 12 | ILIM | R502 1.50 k 接地 | OK（手册写明 ILIM 为第 12 脚；检索确认） |
| 13 | IN | USB_5V_SAFE；C501 4.7 µF，3.5 mm | OK |
| 14 | TMR | R2352 68.1 k | OK（允许 18–72 k） |
| 15 | ITERM（BQ24074 独有） | R2351 499 Ω | OK（要求 < 15 k） |
| 16 | ISET | R501 2.00 k；同时接 U1702 S4 | OK（S4 支路见既有 SCH-ISET-SWITCHED-CAP） |
| EP(17) | 散热焊盘，接 VSS | GND | 网络 OK；焊盘内 0 个过孔，已由 PCB-03 记录 |

封装几何：
- 引脚焊盘 0.60×0.24 mm，节距 0.5，焊盘中心 ±1.40（中心距 2.8），伸出本体 0.2 mm。与 TI RGT0016C 推荐焊盘（16×0.6×0.24，中心距 2.8）一致（记忆，中等置信度）。
- EP 1.68×1.68，焊盘边缘到 EP 0.26 mm，角部焊盘间隙 0.33 mm。
- EP 钢网为 4 块 0.706 mm 方孔，覆盖率 70.6%，在 50–80% 的常规范围内。
- 1 脚在左上，逆时针编号正确。

外围计算：
- 输入限流：KILIM 1550 A·Ω（检索确认），I_IN,max = 1550/1500 = **1.03 A**（按 KILIM 公差约 1.00–1.07 A）。R 在允许的 1.1–8 kΩ 范围内。
- 充电电流：KISET 797/890/975 A·Ω（检索确认），ICHG = **445 mA**（399–488 mA）。
- 终止电流：ITERM = 0.03×RITERM/RISET（非 USB100 模式），USB100 模式系数为 0.01（检索确认）。得 **7.5 mA（1.7% ICHG）**，USB100 模式下 2.5 mA。
- 定时器：KTMR 36/48/60 s/kΩ（检索确认），预充 54.5 min（41–68 min），快充 10×，约 **9.1 h（6.8–11.4 h）**。
- 器件规格：OVP 10.5 V，VO(REG) 4.4 V，VBAT(REG) 4.2 V（检索确认）。

### 2.2 U1001 TPS259470LRPWR（RPW 10 脚 VQFN-HR 2×2），封装 `TI_RPW0010A_TPS259470`，位置 (66.3, 6.8) F.Cu

| 脚 | 数据手册名 | 网表网络 | 结论 |
|---|---|---|---|
| 1 | EN/UVLO | USB_UV = R1001 26.1k / R1002 10k，接 VBUS_RAW | OK（不得悬空，未悬空） |
| 2 | OVLO（470x 可调） | USB_OV = R1003 37.4k / R1004 10k | OK；余量见 PWR-07 |
| 3 | PG/AUXOFF（470x 为 AUXOFF，开漏数字**输出**） | 悬空（NC） | **OK**。它只是优先级电源切换时控制另一颗 eFuse 的输出，悬空不影响本片导通（检索确认）。既有 SCH-PINAUDIT-POWER 的疑问可以关闭 |
| 4 | FLT（开漏，低有效） | USB_FLT，R1006 100k 上拉 V3D，R1901 1k 接 MCU | OK |
| 5 | IN | VBUS_RAW | OK |
| 6 | OUT | USB_5V_SAFE | OK |
| 7 | dVdt | C1001 4.7 nF C0G | OK：SR ≈ 2000/4700 ≈ 0.43 V/ms，0→5 V 约 12 ms，约 8 µF 负载的浪涌约 3.4 mA（常数 2000 由手册示例推算，中等置信度） |
| 8 | GND | GND | OK |
| 9 | ILM | R1005 6.65 k 接地 | **问题，见 PWR-01** |
| 10 | ITIMER | 悬空 | 合法：手册说悬空时消隐最短、断路最快（检索确认）。但和 0.5 A 限流叠加，会立即进入限流，见 PWR-01 |

封装几何：
- 1–4 脚在左列，节距 0.45/0.475；1、4 脚为 L 形焊盘。
- IN/OUT 为 0.30×2.40 的中间长条，位于 x = ±0.25，两条间隙 0.20 mm。
- 7–10 脚在右列，7、10 脚为 L 形焊盘。
- 各焊盘伸出本体 0.2 mm，相互间隙 ≥ 0.20 mm。没有 EP（器件本身也没有 EP）。
- 1 脚在左上，逆时针编号，IN 在左、OUT 在右，与手册描述一致（检索确认 1–8 脚；9 = ILM、10 = ITIMER 为排除法推断）。
- 无法拿到 RPW0010A 焊盘图逐尺寸核对。封装本身自洽，结论为「需对照 TI 焊盘图签核」，没有发现错误。
- 板上检查：3、10 脚焊盘没有任何走线接触；3 脚离 USB_FLT 线 0.37 mm，大于 0.15 mm 规则。

L 版本行为（检索确认）：
- 过流时：先按 ITIMER 消隐，超时后**主动限流在 ILIM（不锁死）**，并在 tITIMER 后拉低 FLT。
- 持续限流会让结温升到热关断（TSD，上升阈值 154 °C）。L 版在 TSD 后**锁死**，A 版自动重试。
- 解锁方法：VIN 掉电，或把 EN/UVLO 拉到 VSD 以下。本设计的 EN/UVLO 只接在 VBUS 分压上，所以 TSD 后只能拔插 USB 线才能恢复。

阈值计算（VUVLO(R) = VOV(R) = 1.183/1.20/1.223 V，VUVLO(F) = 1.09 V；检索确认）：
- UVLO：上升 4.33 V（4.21–4.48 V），下降 3.93 V。OK。
- OVLO：上升 **5.69 V（5.52–5.89 V）**，见 PWR-07。

### 2.3 U1101 TPS63070RNMR（RNM 15 脚 VQFN-HR 2.5×3），封装 `TI_RNM0015A_TPS63070`，位置 (61.3, 14.8) F.Cu

| 脚 | 手册名（检索确认） | 网表 | 结论 |
|---|---|---|---|
| 1 | PS/SYNC：**低 = 强制 PWM，高 = PWM/PFM 省电** | GND | 当前为强制 PWM，见 PWR-06（纠正既有结论） |
| 2 | PG（开漏） | V3_PG，R1104 100k 上拉 V3D，未使用 | OK（既有 C1） |
| 3 | VAUX（不得外接负载） | C1101 100 nF | OK |
| 4 | GND | GND | OK |
| 5 | FB（0.8 V） | R1101 312k / R1102 100k | OK：Vout = 0.8×(1+3.12) = **3.296 V** |
| 6 | FB2 | 悬空 | OK：VSEL 为低时 FB2 高阻，手册允许悬空或接地。既有疑问可以关闭 |
| 7、8 | VOUT | V3D；C1104、C1105 22 µF 0805 X5R 10 V | 见 PWR-08 |
| 9 | L2 | BUCK_L2 → L1101.2 | OK |
| 10 | PGND | GND | OK |
| 11 | L1 | BUCK_L1 → L1101.1 | OK |
| 12、13 | VIN | SYS；C1102 10 µF + C1103 100 nF | 输入电容偏少、偏远，已由 PCB-07 记录 |
| 14 | EN（高有效） | SYS_ENABLE（D1301/D1302 或门，R1304 100k 下拉） | OK：使能电平约 0.75×(SYS−Vf) ≥ 2.0 V |
| 15 | VSEL | GND | OK |

封装几何：
- 左列 1–4，下排 5–8，右侧 9/10/11 为横向长条（L2/PGND/L1），上排 12–15，逆时针编号，1 脚在左上。
- 7/8 脚、12/13 脚的铜皮做成 L 形相连（同一网络，有意为之）。
- 各焊盘伸出本体 0.2 mm，焊盘间最小间隙 0.225 mm。没有 EP（器件本身也没有 EP）。
- 无法逐尺寸对照 TI 焊盘图。功率焊盘的阻焊和钢网有问题，见 PWR-03。

外围元件：
- L1101 XGL4020-152 1.5 µH，与手册推荐的 XFL4020-152（1.5 µH，Isat 4.6 A）同系列等效（检索确认推荐值）。
- 手册参考 BOM：CIN 2×10 µF + 10 µF，COUT 3×22 µF；有效输出电容至少为 10×L(µH)，即约 15 µF（检索确认）。

### 2.4 U1301 LTC2954ITS8-1（TSOT-23-8），封装 `SmartVioV25:TSOT-23-8`，位置 (68.3, 22.8) F.Cu

管脚（检索确认 TS8：1 VIN、2 PB、3 ONT、4 GND、5 INT、6 EN、7 PDT、8 KILL）：

| 脚 | 网表 | 结论 |
|---|---|---|
| 1 VIN | SYS | OK（2.7–26.4 V） |
| 2 PB | PWR_PB，R826 10k 上拉 SYS，SW813 接地 | OK |
| 3 ONT | C1302 0.1 µF C0G | tON = 32 ms + 6.4 s/µF×0.1 µF ≈ **0.67 s** 长按开机，OK |
| 4 GND | GND | OK |
| 5 INT（开漏） | KEY_PWR，R823 10k 上拉 V3D，C824 10 nF，接 MCU | OK |
| 6 EN（-1 版：**开漏、高有效**） | PWR_LTC_EN，R1103 33k 上拉 SYS，D1301 → TPS63070 EN | OK：-1 版极性与 TPS63070 高有效 EN 一致，开漏需要的上拉也有 |
| 7 PDT | C1303 0.47 µF C0G | 64 ms + 6.4 s/µF×0.47 µF ≈ **3.1 s** 强制关机，OK（2220 体积问题见既有 C2） |
| 8 KILL | PWR_KILL，R1301 10k 接 PE7，R1302 100k 下拉 | OK：阈值 0.6 V；开机后有 400/512/650 ms 消隐，期间 KILL 必须被拉高，否则 EN 释放（检索确认） |

封装：
- 焊盘 1.325×0.50 mm，节距 0.65，中心 ±1.1375（内侧间距 0.95，外侧 3.60）。
- 丝印三角和 Fab 倒角都在 1 脚，方向正确。焊盘宽度问题见 PWR-04。

### 2.5 U1401 TPD2S300YFFR（DSBGA-9），封装 `SmartVioV25:TI_YFF0009_Official`，USB 板 (5, 9) F.Cu

| 球 | 手册名（检索确认） | 网表 | 结论 |
|---|---|---|---|
| A1 | C_CC1（连接器侧） | CC1_PORT → J401.A5 | OK |
| A2 | VBIAS（ESD 支撑电容，0.1 µF 到地） | C1401 100 nF/50 V | 取值 OK，**位置不合格**，见 PWR-02 |
| A3 | C_CC2 | CC2_PORT → J401.B5 | OK |
| B1 | CC1（系统侧） | CC1_SAFE → R401 5.1k | OK |
| B2 | GND | GND（焊盘内微孔，已由 PCB-13/HB-08 记录） | OK |
| B3 | CC2 | CC2_SAFE → R402 5.1k | OK |
| C1 | FLT（开漏） | CC_FAULT_N，R1401 100k 上拉 V3D → MCU | OK |
| C2 | VPWR（2.7–4.5 V，1 µF 就近去耦） | V3D；C1402 1 µF | 电源 OK，**电容位置不合格**，见 PWR-02 |
| C3 | VM（2.7–4.5 V 为 CC/PD/FRS 模式） | V3D | OK：只需 CC 模拟/PD 信号时允许 VM 直接接 VPWR、不加电容（检索确认） |

封装：
- 3×3 球，节距 0.4，铜皮 Ø0.23（NSMD），阻焊 +0.04（Ø0.31），钢网 0.25 方孔，A1 在左上，丝印圆点在 A1 一侧。
- 与 TI DSBGA 0.4 mm 节距推荐做法一致（记忆，中等置信度）。命名不一致见 PWR-09。

### 2.6 U1921 TPS3700DDC（SOT-23-6），封装 `SmartVioV26:TI_DDC0006A_Official`，主板 B 面 (65.75, 38.75) 旋转 90°

| 脚 | 手册名（检索确认 DDC：1 OUTA、2 GND、3 INA+、4 INB−、5 VDD、6 OUTB） | 网表 | 结论 |
|---|---|---|---|
| 1 | OUTA | CHARGE_GATE | OK |
| 2 | GND | GND | OK |
| 3 | INA+（低于 400 mV 时 OUTA 拉低，欠压） | CELL_NTC_SENSE | OK |
| 4 | INB−（高于 400 mV 时 OUTB 拉低，过压） | NTC_COLD_DIV | OK |
| 5 | VDD | SYS，C1921 100 nF | OK |
| 6 | OUTB | CHARGE_GATE（与 OUTA 线或） | OK |

封装：焊盘 6×(1.1×0.6)，中心 ±1.35（中心距 2.7），节距 0.95，阻焊 +0.07，与 TI DDC0006A 推荐焊盘完全一致（记忆，置信度高）。1 脚标记缺失，见 PWR-05。

---

## 3. 新发现

### PWR-01【high】eFuse 限流只有 0.50 A，比充电器设定的 1.03 A 输入限流和固件 990 mA 预算低一半，会长期限流甚至热锁死

- **证据**
  - 网表 R1005 6.65k，EFUSE_ILM（U1001.9）接地。
  - TPS25947 手册 Eq.7：R_ILM(Ω) = 3334 / I_LIM(A)；R_ILM 允许 549–6650 Ω（检索确认）。代入得 I_LIM = 3334/6650 = **0.501 A**，正好是允许设定范围的最低点；TI 说明低于约 0.5 A 不保证精度。
  - 同一路径上：
    - BQ24074 R502 1.5k 对应 I_IN,max **1.03 A**；
    - ICHG 445 mA；
    - 固件 `firmware/base/sv27_power_profile.h:19-20` 写 `SV27_SOURCE_GRANT_MA 1500u`、`SV27_DELIVERY_BUDGET_MA 990u`。
  - ITIMER（U1001.10）悬空，消隐时间最短。
- **后果**
  - 一旦放开充电（EN2/EN1 = 10 进入 ILIM 模式，或 01 的 USB500 模式），充电 445 mA 加系统负载（MCU、ESP32、PhotoMOS、喇叭）就会超过 0.5 A，eFuse 立即进入主动限流，FLT 持续拉低。
  - USB_5V_SAFE 跌落后，靠 BQ24074 的输入 DPM 回退。若该模式下 DPM 不生效，会在 BQ 的 UVLO/睡眠阈值附近打嗝。
  - eFuse 持续承受 (VBUS−VOUT)×0.5 A 的功耗，而且芯片在 0.15 mm 细线上（PCB-01），散热差。持续过热进入 TSD 后，**L 版会锁死，只能拔线恢复**。
  - 固件里 `sv_telemetry.c:139` 一旦接入，会把 USB_FLT 当成 external_fault，并通过 FW-FAULT-LATCH 永久锁定。
  - 既有 PCB-01、HB-02 按「约 1 A/1.2 A 输入」做的发热估算，实际上被这颗电阻限制住了（结论仍需按修正后的限流重算）。
- **修复**
  - R1005 改为 **2.49 kΩ 1%**，I_LIM ≈ 1.34 A：高于 BQ24074 ILIM 上限 1.07 A 和元件公差之和，又低于 Type-C 默认 1.5 A。或者用 2.74 kΩ，约 1.22 A。
  - ITIMER 加对地电容（例如 10 nF；按手册 Eq.8，t = ΔV_ITIMER×C/1.8 µA 核算，几毫秒级），让插拔和负载瞬态不立即进入限流。
  - 如果确实要在 0.5 A 限流（无 Rp 检测时按 USB 2.0 端口处理），应由 BQ24074 的 EN1/EN2 实现，而不是靠 eFuse 卡电流。
  - 首样做 1 A 持续负载下 U1001 的温升和 FLT 测试。
- **置信度**：高（公式和范围来自 TI 手册检索原文，网表事实已核对）。

### PWR-02【medium】TPD2S300 的 VBIAS 电容和 VPWR 去耦电容离芯片 11–13 mm，走线约 19 mm，还要换层，CC 口的 ESD 钳位能力达不到手册水平

- **证据**
  - USB 板 U1401 在 (5, 9) F.Cu，C1401（VBIAS，100 nF）在 (12, 18) **B.Cu**，CC_VBIAS 走线 F.Cu 0.85 mm + B.Cu 18.5 mm，经 1 个过孔。
  - C1402（VPWR，1 µF）在 (12, 20) F.Cu；V3D 在 USB 板上的走线约 31 mm（0.15–0.2 mm 线，2 个过孔）。
  - 手册要求：VBIAS 放 0.1 µF 到地（ESD 支撑电容）；VPWR 的 1 µF 尽量靠近芯片（检索确认）。
- **后果**
  - VBIAS 是内部 ESD 钳位的储能节点。约 15–20 nH 的走线和过孔电感，会让 IEC 61000-4-2 接触放电时的钳位电压明显升高，CC 引脚静电或短接 VBUS 时的保护能力达不到数据手册水平。
  - USB 板只有 4 个 GND 过孔（PCB-13），情况更差。
- **修复**：C1401 移到 F.Cu、紧邻 A2 球（≤1 mm，直接接 B2/GND 平面）；C1402 紧邻 C2/C3 球；首样做 CC 口 ±8 kV 接触放电。
- **置信度**：中高（几何为实测，手册要求为检索确认，影响幅度为工程判断）。

### PWR-03【medium】TPS63070 功率焊盘的阻焊开窗比铜皮每边小 0.05 mm，钢网却按整个焊盘开孔，锡膏会印到阻焊上

- **证据**：`TI_RNM0015A_TPS63070.kicad_mod` 中 7–13 脚（VOUT、L2、PGND、L1、VIN）的焊盘宽 0.25 mm，`solder_mask_margin -0.05`，阻焊开窗只剩 **0.15 mm 宽**；钢网没有设置收缩，仍是 0.25 mm 宽。L2/PGND/L1 三条长条的间距只有 0.25 mm。板级 `pad_to_mask_clearance 0`。
- **后果**
  - 锡膏有一半宽度印在阻焊上，回流后容易产生锡珠和桥连，而桥连位置正是 SW 节点与 PGND 之间。
  - 0.15 mm 开窗也接近阻焊对位公差（±0.05），大电流焊盘的可焊面积减少约 40%。
- **修复**：按 TI RNM0015A 焊盘图重做。若 TI 规定阻焊定义焊盘（SMD），则把铜皮加宽、开窗按 TI 值，钢网 ≤ 开窗；若为非阻焊定义（NSMD），就把 mask margin 改回 0 或正值。由 SMT 厂做 DFM 复核。
- **置信度**：中（钢网与阻焊的矛盾是确定的；TI 原始焊盘图未能取得）。

### PWR-04【low】LTC2954 TSOT-23-8 焊盘宽 0.50 mm、焊盘间隙 0.15 mm，比 ADI 推荐的约 0.40 mm 宽；焊盘还伸入本体下方 0.33 mm

- **证据**：`SmartVioV25.pretty/TSOT-23-8.kicad_mod`：8 个焊盘 1.325×0.50，中心 ±1.1375，内侧间距 0.95 mm。按记忆，ADI TS8（05-08-1637）推荐焊盘约 0.40 max×1.22，中心距 2.62，内侧 ≥ 1.4，外侧 ≤ 3.85；引脚宽 0.22–0.36。
- **后果**：0.65 mm 节距下焊盘间隙只有 0.15 mm（阻焊桥也只有 0.15 mm），桥连风险上升；伸入本体下方的焊盘容易产生锡珠。
- **修复**：焊盘改为约 0.40×1.2，中心 ±1.31。
- **置信度**：中（ADI 推荐尺寸来自记忆，焊盘自身几何为实测）。

### PWR-05【low】U501、U1001、U1101、U1921 的封装既没有丝印，也没有 Fab 层 1 脚标记

- **证据**
  - `TI_RGT0016C_BQ24074_EP17`、`TI_RPW0010A_TPS259470`、`TI_RNM0015A_TPS63070` 只有 F.Fab 矩形框和 F.CrtYd，没有任何 F.SilkS 图形，也没有倒角或圆点。
  - `TI_DDC0006A_Official` 只有 Fab 矩形框。
  - 对照：TSOT-23-8 和 TI_YFF0009 封装有 1 脚标记。
  - 前两颗是正方形 QFN，4 个方向都能放上去。
- **后果**：首件检验、AOI 和手工返修时无法确认方向；BQ24074 或 eFuse 转 90° 会直接把 VBUS 加到逻辑脚上。
- **修复**：在 1 脚角加丝印点或角标，Fab 层加倒角；装配图标出 1 脚。
- **置信度**：高。

### PWR-06【medium，纠正既有 SCH-PSYNC-PFM】TPS63070 的 PS/SYNC 接地实际是「强制 PWM」，不是省电模式；既有修复建议会适得其反

- **证据**：TI TPS63070 手册 PS/SYNC 脚描述原文为「Pull to low for forced PWM, pull high for PWM/PFM (power save) mode」，TI E2E 也确认接 GND 即为低（检索确认）。网表 U1101.1 接 GND。
- **后果**
  - 现状下不存在 PFM 突发纹波，SCH-PSYNC-PFM 的问题本身不成立。
  - 该条的修复写的是「PS/SYNC 改接 V3D（强制 PWM）」，照做反而会**打开**省电模式，把可闻频段的突发纹波引入 V3D→V3A。
  - 现在真正的代价是轻载效率：强制 PWM 下，待机或插 USB 的 housekeeping 状态会多出几毫安量级的开关损耗（量级未核实），影响电池续航。
- **修复**：把 SCH-PSYNC-PFM 改为「已核实：PS/SYNC=GND=强制 PWM，音频期间正确」。如需省电，可把 PS/SYNC 接 MCU GPIO：音频工作时为低（强制 PWM），深度待机时为高（省电）。
- **置信度**：高。

### PWR-07【low】eFuse OVLO 的最小值 5.52 V 只比 Type-C vSafe5V 上限 5.5 V 高 20 mV

- **证据**：R1003 37.4k / R1004 10k，阈值 1.183–1.223 V，电阻 1%，算得 OVLO 上升阈值 5.52–5.89 V（标称 5.69 V）。
- **后果**：电压偏高的适配器，或热插拔振铃，可能误触发过压关断。过压不锁死，但每次都要按 dVdt 重新上升约 12 ms，SYS 会出现瞬时掉电。
- **修复**：R1003 改为 39.2k，上升阈值约 5.90 V（最低 5.73 V），仍远低于 BQ24074 的 10.5 V OVP 和 eFuse 的耐压。
- **置信度**：中（OVLO 阈值为检索确认；下降阈值未取得）。

### PWR-08【low】TPS63070 输出电容只有 2×22 µF 0805 X5R 10 V，直流偏压降额后约 18–22 µF，刚够手册的 15 µF 下限，TI 参考设计用 3×22 µF

- **证据**：网表 C1104、C1105（CC0805MKX5R6BB226，±20%）接 V3D；手册写有效 COUT ≥ 10×L(µH)，即 15 µF；参考 BOM 为 3×22 µF/16 V X6S 0805（检索确认）。
- **后果**：在升降压过渡区和负载阶跃（ESP32 发射、喇叭）时，环路相位裕量和输出纹波处于下限，-50% 降额的最坏情况可能低于 15 µF。
- **修复**：V3D 加 1 颗 22 µF（或换成 16 V/1206），首样测负载阶跃。
- **置信度**：中。

### PWR-09【info】U1401 封装库引用不一致

- **证据**
  - 网表和 PCB 用的是 `SmartVioV25:TI_YFF0009_Official`；`native-components.json` 的 footprintAudit 写的是 `SmartVio_Audio_Official:TI_YFF0009_Official`（`footprints/SmartVio_Audio_Official.pretty`），而包内没有这个库。
  - 同一库里还有未使用的 `TI_YFF0009_TPD2S300`（钢网 = Ø0.23 圆，阻焊 +0.025）。
- **后果**：「EXACT_LAND_GEOMETRY_VERIFIED」的审计对象与实际使用的封装文件对不上。
- **修复**：统一库名，删除未用的变体，重新绑定 SHA。
- **置信度**：高。

其他已检查、未立项的小项：
- PWR_ONT 走线约 19 mm，最近处离 BUCK_L1/L2 0.26 mm（In2/F.Cu）。只在开机计时时有意义，而那时 buck 尚未工作，影响很小。
- BUCK_FB 高阻节点走线约 10 mm、离 SW 1.75 mm，属于 PCB-07 的范畴。
- RISET 线总长约 70 mm、跨 5 层（接到监测 TMUX），属于 SCH-ISET-SWITCHED-CAP 的范畴。

---

## 4. TI 数据手册事实核对（findings_digest.json 中依赖手册的假设）

| 既有条目 / 假设 | 核对结果 | 置信度 |
|---|---|---|
| A1 撤回、FW-NO-CHARGE-PATH「U1921 窗口接法本身正确」 | **确认**：DDC 管脚为 1 OUTA、2 GND、3 INA+、4 INB−、5 VDD、6 OUTB；INA+ 低于 400 mV 时 OUTA 拉低，INB− 高于 400 mV 时 OUTB 拉低，迟滞 5.5 mV（最大 12 mV）。按 2.5 V 基准、R1924 30.1k、RT1921 10k/B3435、R1921+R1922 258k 负载计算：热端 RT = 5.86 k，约 **39.5 °C**；冷端 RT = 23.1 k，约 **4.8 °C**。窗口非空，接法正确 | 检索确认 + 计算 |
| B2「TPD2S300 VPWR/VM 来自 V3D，无电池（dead-battery）时 Rd 是否存在？」 | **问题不成立**：VPWR 不上电时内部提供高压 dead-battery Rd（约 4.1–6.1 kΩ），USB 源因此输出 VBUS。之后链路依次为 VBUS → eFuse → BQ24074 → SYS → USB_WAKE_A → TPS63070 → V3D；VPWR 上电后 ≤200 µs 内撤掉内部 Rd、打开 OVP FET，改由外部 R401/R402 5.1k 呈现 Rd。VM 接 VPWR 合法（CC/PD 模式 2.7–4.5 V）。真正的问题是去耦电容位置（PWR-02） | 检索确认 |
| HB-08「可评估取消 TPD2S300」 | 只是成本建议，不涉及手册事实。注意：取消后 CC 脚失去短接 VBUS（20 V）的保护 | — |
| SCH-PINAUDIT-POWER「U1001.3 AUXOFF 可能是输入，悬空可能不导通」 | **纠正**：470x 的 3 脚是 AUXOFF **开漏输出**（在 472x/474x 上是 PG），输入有效且浪涌完成后释放为高，用于优先级电源切换。悬空无害 | 检索确认 |
| SCH-PINAUDIT-POWER「ITIMER 悬空时消隐最短」 | **确认**：手册明确说悬空可得到最快的断路响应，ITIMER 接地不推荐。计时电流 1.8 µA。 | 检索确认 |
| SCH-PINAUDIT-POWER「L 版本是锁死型，一旦触发就要拔线才能恢复」 | **部分纠正**：470x 过流时主动限流，不锁死，FLT 指示；只有过热关断（TSD 154 °C）在 L 版锁死。解锁方法是 VIN 掉电，或把 EN/UVLO 拉到 VSD 以下；本设计 EN/UVLO 只接 VBUS，所以 TSD 后要拔线。与 PWR-01 叠加时，这种情况更容易发生 | 检索确认 |
| SCH-PINAUDIT-POWER「复核 R1005 6.65k 对应的 ILIM」 | **已复核**：I_LIM = 3334/6650 = 0.50 A，是允许范围的最低点，见 PWR-01 | 检索确认 |
| SCH-PINAUDIT-POWER「U1101.6 FB2 悬空需核对」 | **确认合法**：VSEL 为低时 FB2 高阻，手册允许悬空或接地 | 检索确认 |
| SCH-VBUS-NOTVS「TPS25947 绝对最大值较高」 | 未取得 IN 的绝对最大值。工作范围 2.7–23 V。缺 TVS 的结论不变 | 未核实 |
| PCB-01 / HB-02「充电时 USB 输入可达 BQ24074 ILIM ≈ 1.03 A / 约 1.2 A」 | **需修正**：BQ24074 ILIM = 1550/1500 = 1.03 A 是对的，但前级 eFuse 把电流限在约 0.50 A。改大 R1005（PWR-01）之后，1 A 级电流的发热结论才成立 | 检索确认 |
| FW-NO-CHARGE-PATH「EN1=EN2=0 为 USB100」 | **确认**（手册 ITERM 段原文「USB100 mode (EN1 = EN2 = Low)」） | 检索确认 |
| PCB-03 复核「ISET 2.0k → 445 mA」 | **确认**：KISET 797/890/975 A·Ω，ICHG 399–488 mA，与固件 SV27_CHARGE_WORST_MA 491 一致 | 检索确认 |
| SCH-ITERM-TMR（uncertain）「KTMR ≈ 48 s/kΩ，tPRE ≈ 54 min，tMAX ≈ 9.1 h；ITERM ≈ 1.7%」 | **确认，可由 uncertain 改为 confirmed（low）**：KTMR 36/48/60 s/kΩ，快充定时 = 10×tPRE，即 6.8–11.4 h；ITERM = 0.03×RITERM/RISET = 7.5 mA（USB100 模式 0.01 系数，2.5 mA），RITERM < 15 k。R2351 建议改为约 3.3 kΩ（终止电流约 50 mA，C/20） | 检索确认 |
| SCH-PSYNC-PFM「PS/SYNC 低 = 省电模式」 | **错误**，见 PWR-06：低 = 强制 PWM。原修复建议（接 V3D）会打开 PFM，应撤回 | 检索确认 |
| FW-USB-SHUTDOWN-LATCH「LTC2954 开 EN 后约 512 ms 被持续为低的 KILL 关掉」 | **确认**：tKILL,ON BLANK 为 400/512/650 ms，到时 KILL 仍为低则释放 EN | 检索确认 |
| FW-RESET-KILL（uncertain）「KILL 去抖未知」 | KILL 为 0.6 V 精密阈值输入；开机消隐结束后的去抖时间仍未检索到，维持 uncertain | 部分 |
| FW-PWR-TAP「LTC2954 自带 INT 去抖」 | INT 低脉冲最短 32 ms，按住期间保持为低；长按 PDT（本设计约 3.1 s）后强制关机 | 检索确认 |

---

## 5. 来源（检索到的 TI/ADI 官方文档页面）

- TPS25947 数据手册 SLVSFC9B/C 与 ZHCSL91B：https://www.ti.com/document-viewer/lit/html/SLVSFC9C/GUID-B28BEBBA-B2D9-4AB6-8766-FDB5D7000705 ，https://www.ti.com/document-viewer/lit/html/SLVSFC9C/GUID-C4682EDF-DD3B-47F9-A79D-4D8C602FADFA ，https://www.ti.com/document-viewer/lit/html/SLVSFC9B/GUID-348A416F-B75D-4756-9F3B-5385B4CED6F9 ，https://www.ti.com/document-viewer/lit/html/SLVSFC9B/GUID-09176C8A-1E1F-435C-A154-41B8242201C0 ，https://www.ti.com.cn/document-viewer/cn/lit/html/ZHCSL91
- TPD2S300 数据手册 SLVSDL1/ZHCSGS3：https://www.ti.com/document-viewer/TPD2S300/datasheet/pin-configuration-and-functions ，https://www.ti.com/document-viewer/TPD2S300/datasheet/power-supply-recommendations ，E2E：https://e2e.ti.com/support/interface-group/interface/f/interface-forum/925289/tpd2s300-cc-dead-battery-resistor
- BQ2407x 数据手册 ZHCSIF0N：https://www.ti.com.cn/document-viewer/cn/lit/html/ZHCSIF0N/GUID-02776FFD-03F5-41C5-85A0-CB69B8B8EC11 ，https://www.ti.com.cn/document-viewer/cn/lit/html/ZHCSIF0N/GUID-7E7F3E26-6FD1-4F1D-88D7-C9B9363D0CB5 ，https://www.ti.com.cn/document-viewer/cn/lit/html/ZHCSIF0N/GUID-9A1BC7B9-20ED-44A4-B809-124973E77761 ；BQ24076（同族 KTMR）：https://www.ti.com.cn/document-viewer/cn/BQ24076/datasheet/34-ZHCSGY5A
- TPS63070 数据手册 SLVSC58B：https://www.ti.com/document-viewer/TPS63070/datasheet/ps-sync-slvsc58-pssync ，https://ti.com/document-viewer/TPS63070/datasheet/vsel-and-fb2-pins-slvsc58-vsel ，https://www.ti.com/document-viewer/lit/html/SLVSC58B/inductor-selection-slvsc584854 ，E2E：https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/940940/tps63070-about-ps-sync-pin
- LTC2954 数据手册：https://www.analog.com/media/en/technical-documentation/data-sheets/2954fb.pdf ，https://www.analog.com/jp/ltc2954/datasheet.html
- TPS3700 数据手册 SBVS187G：https://www.ti.com/document-viewer/TPS3700/datasheet/outputs-outa-outb-slvsci77050 ，https://www.ti.com/document-viewer/ja-jp/TPS3700/datasheet/6-JAJSBS5G
