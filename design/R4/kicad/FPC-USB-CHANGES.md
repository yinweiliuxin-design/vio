# R4 FPC / USB / 音频板 / 盖板 版图修改说明（ECO-R4-pcb-fpc 执行记录）

> **R4 ENGINEERING SAMPLE — 未发布（NOT RELEASED unless DRC/parity 0）**
> 工具：KiCad 10.0.6（kicad-cli DRC，`--severity-all`，即错误和警告都计入）、pcbnew Python、Freerouting 2.1.0（只用于 USB 板、音频板和盖板中被改动的网络）。
> 本文中的“通过”只指 DRC 或 parity 脚本通过。没有做过任何实物、纸样、3D 装配或供应商确认的内容，一律标为“未验证”。

## 1. 交付文件

| 板 | 原生文件（`design/R4/kicad/pcb/`） | 基线（R3） | 制造输出（`design/R4/kicad/fab/<board>/`） |
|---|---|---|---|
| USB 板 | `SmartVio-usb-r4.kicad_pcb` | usb-r2-synced | usb-r4：Gerber（4 层）、钻孔（PTH/NPTH/F–In1 激光盲孔）、坐标、PDF、STEP |
| 音频板 | `SmartVio-audio-r4.kicad_pcb` | audio-r2-final | audio-r4 |
| 盖板 | `SmartVio-cover-r4.kicad_pcb` | cover-r2-final4 | cover-r4 |
| KEYS6 FPC | `SmartVio-fpc-keys6-r4-bus.kicad_pcb` | keys6-r3-bus | fpc-keys6-r4 |
| **USB16 FPC（新）** | `SmartVio-fpc-usb16-r4.kicad_pcb` | — | fpc-usb16-r4 |
| **AUDIO4 FPC（新）** | `SmartVio-fpc-audio4-r4.kicad_pcb` | — | fpc-audio4-r4 |
| COVER6 FPC | `SmartVio-fpc-cover6-r4.kicad_pcb` | cover6-r2-bus | fpc-cover6-r4 |
| POTS3 FPC | `SmartVio-fpc-pots3-r4.kicad_pcb` | pots3-r2-bus | fpc-pots3-r4 |
| AUDIO6 FPC | `SmartVio-fpc-audio6-r4.kicad_pcb` | audio6-r2-bus | fpc-audio6-r4 |

- 每块板都附带同名的 `.kicad_pro/.kicad_dru/.kicad_prl`。USB 板的 `.kicad_dru` 新增两条规则：VBUS_RAW ≥0.8 mm（J401 引脚颈部除外）；USB D± 禁止走 In1。
- DRC JSON：`design/R4/kicad/drc/*.drc.json`。Parity 的焊盘–网络导出：`drc/*.pads.json`。
- 新封装放在 `design/R4/kicad/footprints/SmartVioV26.pretty/`，包括 `FPC_USB16`、`FPC_AUDIO4`、`FPC_USB16_HotBar_Main_P0.70`（主板落点，由本 agent 编写，主板 agent 只负责放置）、`FPC_KEYS6_R4`、更新后的 `FPC_AUDIO6`，以及安装孔封装 `NPTH_*`、`SLOT_2.5x1.5`、`KEEPOUT_D4.4_F`。
- `pcb/fp-lib-table` 增加了 KiCad 10 标准库 `Connector_FFC-FPC` 和 `Diode_SMD`，供 J3412 与 D401 使用。
- 主板接口：`design/R4/kicad/main-board-interface.json`，副本在 `K/work/r4/main-board-interface.json`。
- 生成脚本：`design/R4/kicad/scripts/fpc-usb/`（build_*.py、stitch/padvias/parity 等），可以完全复现。

## 2. DRC 与 parity 结果（2026-10-17 最后一次运行）

| 板 | DRC 违规（错误+警告） | 未连接 | 原理图 parity（R4 网表，按板） |
|---|---|---|---|
| usb-r4 | **0** | 0 | **0**（D401、J3412 已在板上） |
| audio-r4 | 0 错误 / **1 警告** | 0 | **0**（R323、J3402、J3404） |
| cover-r4 | **0** | 0 | **0**（J3406/J3408/J3410） |
| fpc-keys6-r4 | **0** | 0 | **0**（FPC3403） |
| fpc-usb16-r4 | **0** | 0 | **0**（FPC3406） |
| fpc-audio4-r4 | **0** | 0 | **0**（FPC3402） |
| fpc-cover6-r4 | **0** | 0 | **0**（FPC3404） |
| fpc-pots3-r4 | **0** | 0 | **0**（FPC3405） |
| fpc-audio6-r4 | **0** | 0 | **0**（FPC3401） |

- audio-r4 的唯一警告是 `lib_footprint_mismatch`，出在 J3404（WirePads_4_P1.5）。原因：ECO L-13 的芯序从西到东为 3/2/1/4，第 4 脚（GND）必须移到最东端；主板 J3403 也是这样摆的，同样会有这条警告。如果要清零，需要库里另建一个 4 焊盘非单调封装，并由原理图改封装字段。这件事要原理图 agent 决定。
- **关于 parity 的方法**：R4 原理图是 9 块板共用的一张原理图，`kicad-cli pcb drc --schematic-parity` 只能用于与原理图同名的工程（主板），对子板会把其他板的器件全部报为缺失。因此子板用脚本 `fpcparity.py` 对照 `r4-netlist.xml`，逐个封装检查 4 项：位号是否存在、库封装名、Value、逐焊盘网络。打了 board-only 属性的安装孔不参加比对。表中的 0 就是这个脚本的结果，不是 KiCad 原生 parity 的结果。
- 端点位号已按 `sch-endpoint-refmap.json` 改名（H_* → J34xx / FPC34xx），FPC 的 Value 也与网表一致。

## 3. 逐条 ECO 状态

| L-id | 内容 | 状态 | 说明 / 数据 |
|---|---|---|---|
| **L-09** | KEYS6 去镜像 | **已完成（DRC 0）**，有 1 处偏差 | S 端按 ECO 改为 y_R4 = 50.3 − y_R3，顶部段为 50.6 − y_R3，T 行在 y 10.277。S 端手性 cross(1→3,1→4) = **+4.125**（R3 为 −4.5），与主板 J3405 同号。尾端按机构说明缩短到 y 37.45（物理 7.45，避开 C605）。为保证铜到板边 0.3 mm，第 2 排触点改为 0.75×0.55，第 1 排改为 0.75×0.60，仍落在主板 0.9 mm 焊盘内。GND 全程 B 层 0.6 mm，只在 S2 出口处颈缩为 0.25 mm、长 1.6 mm。触点内过孔 R3 为 11 个，R4 为 **0**。**偏差**：S 端舌片只有 4.5×2.85 mm，单层最多引出 5 根线。KEY_FX 必须在舌片内换层，过孔距 S4/S1/S5 开窗 **0.23 mm**，达不到 ECO 要求的 ≥0.5 mm。信号在颈部走 B 层（与 GND 共面），KEY_FX 走 F 层，与 ECO 写的“信号走 F”不同，这样全板只用 4 个过孔（R3 为 16 个）。T 端加了 2 个 Ø1.0 对位孔（74.4,9.6）和（60.0,9.6），盖板 B 面对应位置加了丝印/Fab 对位圈 |
| **L-10** | 新 FPC-USB16 | **已完成（DRC 0）** | 平面图按 ECO 路线展开：主板端 16 个触点 0.30×1.30（B 面），节距 0.70，接 J3411；Z 折区（平面 y 5.45–11.5）只走单层、不放过孔；L 形平面转弯处内角 R1；S 形上升区（平面 x 82.3–86.7）不放过孔；ZIF 端 16 根金手指 0.3 mm、节距 0.5，在 **F 面**，FPC 宽 8.5、伸入 3.5 mm。导体宽度：VBUS 4 个触点在 B 层并为 2.4 mm，经 6 个过孔转到 F 层，F 层母线 **1.8 mm**（ECO 要求 ≥1.2 mm）；GND（5/8/10–12 芯）为 B 层整片铺铜；V3D 和 5V_SAFE 0.25 mm；信号 0.15 mm。D+/D− 在 F 层，下方是 B 层地平面，两侧有 5、8 两芯护地，**长度差 0.04 mm**。叠层：覆盖膜 27.5 µm + RA 铜 18 µm + PI 25 µm + 铜 18 µm + 覆盖膜 27.5 µm = **0.116 mm**。补强画在 User.1 层：ZIF 端在 B 面，按 Hirose 要求总厚 0.30 ±0.03，**需供应商确认**；热压焊端在 F 面，0.2 mm。主板端放不下 2 个 Ø1.0 对位孔，原因见接口 JSON |
| **L-02** | USB VBUS ≥0.8 mm | **已完成** | R3 的 0.2 mm 线全部删除。VBUS 从 J401 的 4 个引脚经 4 个过孔（0.6/0.3）汇入 B 层和 In2 层铺铜，铜宽 ≥2 mm，通到 J3412 的 13–16 脚。B 层约 12 mm × ≥2 mm × 35 µm，估算 **约 3 mΩ**，没有计入 In2 的并联，也未实测。DRU 已加 ≥0.8 mm 规则，J401 引脚颈部 0.3 mm 除外 |
| **L-11** | USB 板重布 | **已完成（DRC 0）**，部分偏差 | 删除 H_USB_1_R 和 H_USB_2_R，在 B 面放 **J3412 = Hirose FH12-16S-0.5SH(55)**，用 KiCad 官方库 `Connector_FFC-FPC:Hirose_FH12-16S-0.5SH_1x16-1MP_P0.50mm_Horizontal`，位置（5.2, 13.0），旋转 90°，插口朝 −x（本地 x 0.8），1 脚在 +y 端（y 16.75），与 FPC 第 1 芯对应。C1401（VBIAS）与 A2 球的边距约 0.9 mm；C1402 与 C2/C3 约 0.8 mm。D± 从 J401 到 TPD2S703、USBLC6 全部在 F 层，只在 R403/R404（放在 B 面紧贴 ZIF）前各换层一次。J401 的 A7/B7 交叉线走 **In2**，In1 保持整片地，DRU 禁止 D± 走 In1。D+ 与 D− 总长相差约 0.8 mm（估算，ECO 要求 ±0.5 mm；全速 USB 12 Mbps 对此不敏感），**未精确等长**。GND 过孔：通孔 74 个，另有 F–In1 激光填孔微孔 4 个，分别在 U1401.B2（沿用 R3）、U1501.3（焊盘内，需填孔电镀）以及两处孤岛缝合点。**偏差**：U1401 到 J401 CC 脚的距离为 5.5 mm（CC2）和约 7.8 mm（CC1，经过孔），超出 ECO 的 ≤5 mm，原因是 J401 四周没有更近的空位 |
| E-07 / D401 | VBUS TVS SMF12A | **已放置** | `Diode_SMD:D_SOD-123F`，**B 面** (12.0, 4.0)，在 J401 正下方，1 脚（K）接 VBUS 铺铜，距 VBUS 脚约 1–2 mm；阳极经 0.5 mm 线和过孔接地。ECO 原写 F 面，但 F 面 3 mm 范围内没有空位。**需机构确认 B 面器件不碰 USB 托架**。C401 也改放 B 面 (16.9, 3.9) |
| 机构孔（USB） | pcb-interface-eco-R4.json | **已完成** | 3 个 Ø1.8 NPTH，位于 (2,3)、(22.3,3)、(22.3,17)，双面 Ø4.4 禁布；(2,17) 为 F 面 Ø4.4 禁布（压柱位置）。ZIF 包络在托架窗口内（本地 x 0.8–6.3，y 6.5–19.5）；ZIF 引脚尾部到 x 7.7 |
| **L-13** | 新 FPC-AUDIO4 | **已完成（DRC 0）** | 4 芯：主板 J3403 → 音频板 J3404，芯序与主板现有 J3403 一致（第 4 脚 GND 在东端）。信号 0.2 mm，B 层；GND 在 B 层 ≥1.0 mm（舌片颈部 0.6/0.75 mm），上段 F 层铺地，用 3 个过孔缝合。Z 折按 R1、升 2.1 mm 计算；平面图在弯折后整体平移，并在 y 28.8–33.0 段向 −x 错位 6.7 mm。平面长度含 0.25 mm 装配余量 |
| L-13（音频板侧） | J3404 横排 | **已完成** | 位于音频板 (35.0–39.5, 2.5)，在 J201 与 J202 之间。删除 H_AUDIO_2_R；RETURN_L/R、SEND_T 重新布线。音频板 F/B 两层地缝合过孔共 50 个（ECO 要求 ≥20） |
| L-13（主板侧） | K1205/C222/K1207 南移 | **转主板 agent** | 写入接口 JSON：这 3 个件北缘须 ≥23.3 mm，当前为 22.43/22.30/22.43 mm |
| E-01 / R323 | J301.6 → HP_DET_B | **已完成** | J301.6 与地铜断开。R323（0 Ω，DNP，B 面 (70.6, 11.0)）距 J301.6 约 2.3 mm |
| **L-14** | D1201–D1207 移到音频板 | **未执行** | 原理图 agent 没有改这些器件的板归属，主板上它们仍然存在；如果在音频板上再放一份会造成重复。是否执行，要由主板 agent 和协调人决定 |
| **L-05** | 盖板天线净空 | **已完成** | 按 ECO 的多边形在 F/B 两层加禁布区（禁铺铜、禁走线、禁过孔），沿边加 7 个缝合过孔。原始 0.45/0.20 小于本板最小过孔 0.6/0.3，因此改为 0.6/0.3。重新灌铜后，地铜到 antenna_box 的最小距离为 **2.10 mm**，出现在扬声器那一段，与 ECO 设计一致；西侧和北侧按多边形计算，**未逐方向复测**。天线 S11/VSWR 需要 VNA 实测 |
| **L-15（盖板）** | 地网格缝合 | **已完成** | RV810–812、SW810–814 的 GND 脚旁各加过孔（共 13 个），另按 10 mm 和 5 mm 两级网格补过孔。全板 GND 过孔 **201 个**（R3 只有 1 个） |
| **L-15（COVER6）** | SPK 与 PWR_PB/LED 去重叠 | **已完成（DRC 0）** | SPK_N 改走 F 层、SPK_P 走 B 层，两者上下对齐（宽边耦合对），LED1–3 和 PWR_PB 放在另一侧。F 层 LED/PWR 与 B 层 SPK 在 XY 投影上的最小间隙：R3 为 **−0.375 mm（重叠）**，R4 为 **+0.333 mm**（要求 ≥0.3）。颈宽保持 3 mm，不需要加宽 |
| 盖板机构孔 | pcb-interface-eco-R4.json | **已完成** | Ø1.8 ×2；USB 柱 Ø4.4 ×3，周围 Ø5.4 范围内禁止走线和铺铜；Ø1.5 圆孔；2.5×1.5 长孔；南侧两个卡扣槽改到 y 44.75。受影响的线已撕掉后自动重布。D851 移到 (34.7, 20.7)。**H905 按机构跟进单（2026-10-17）修改**：从 (88,22) 移到 **(88,21.8)**，孔径 Ø4.4 → **Ø4.0**，禁布区 Ø5.4 → **Ø5.0**，新封装为 `NPTH_D4.0_KO5.0`。修改后实测：孔边到 J3408 焊盘 **0.75 mm**（第 2 脚，原来 0.35 mm），到 PWR_PB 走线 **0.68 mm**，到 COVER6 T 端舌片边缘约 0.4 mm。没有改线。盖板 DRC 0，parity 0，制造输出已重新导出 |
| **L-18** | FPC 触点内不放过孔 | **大部分完成** | 触点开窗内或距开窗 <0.5 mm 的过孔数，R3 → R4：KEYS6 11 → 1（距开窗 0.23 mm，在开窗外）；COVER6 6 → 0（SPK_P 过孔正好 0.50 mm）；AUDIO6 6 → **0**（改为 F 单层布线、无过孔；T 端舌片向东加宽 1.2 mm，**需机构确认**）；POTS3 2 → **1**（S2 V3D 仍在触点内：舌片只有 1.85 mm 高，找不到合法过孔位置，需要主板改落点或加高舌片）；USB16 和 AUDIO4 均为 0。板端焊盘比触点大 0.15 mm（0.75 → 0.90；USB16 为 0.30 → 0.40）。对位孔：KEYS6 的 T 端已加；其余端头没有空间，改用光学或丝印对位，见接口 JSON |
| L-19 | parity | **已完成（按板脚本）** | 见第 2 节 |

## 4. 需要纸样、3D 装配或供应商确认的事项（全部未验证）

1. **FH12-16S-0.5SH(55) 封装**：采用 KiCad 官方库（kicad-footprint-generator 按 Hirose 图纸生成）：信号焊盘 0.3×1.3，MP 焊盘 1.8×2.2 在 ±5.65。本环境**没有拿到 Hirose 原图逐尺寸核对**。另有 3 项需对照原图确认：(a) FH12(55) 为**下接触**（FH12A 为上接触），这决定 FPC ZIF 端触点在 F 面，置信度中；(b) FPC 宽 8.5 ±0.05、伸入 3.5 mm、补强后总厚 0.30 ±0.03，均为未核实的估计；(c) 额定电流 0.5 A/芯。
2. **USB16 FPC 叠层**（18 µm RA 铜、0.116 mm、单层弯折区）、R1.5 静态弯折，以及 1.5 A 时的温升和压降：需要 FPC 厂确认并实测。
3. **USB16 路径**：Z 折、L 形平面、S 形上升，以及与 STM32、ESP32、同轴、USB 托架西轨的间隙，只做了平面图，**没有做 3D 实体或纸样**。另外 R810 侵入第一弯区，见接口 JSON。
4. **KEYS6 R4**：需要用 1:1 纸样或 PET 样折一次，逐芯核对。主板端舌片尾部到 C605 只有 0.03 mm。
5. **AUDIO4**：Z 折位置、主板 K1205/C222/K1207 南移，以及尾端与 R817 只有 0.02 mm 的余量，都需要纸样核对。
6. **AUDIO6** T 端舌片加宽 1.2 mm，需机构复核（与 J201 外形相距约 0.9 mm）。
7. 盖板 USB 柱 H905：已按机构要求改为 (88,21.8) Ø4.0（见第 3 节）。改小以后，柱子的强度和配合要由机构确认。
8. **USB 板 B 面新增 D401、C401、R403、R404**（高 ≤1.1 mm），需确认不碰 USB 托架。
9. 天线 VNA 测试（L-05）、USB 枚举、CC 口 ±8 kV、VBUS 1.5 A 温升：全部要在首样上做。
10. HDI：USB 板 4 个 F–In1 填孔微孔（其中 1 个在 U1501.3 焊盘内）。询价时须写明激光盲孔、填孔电镀。

## 5. 方法说明（如实交代）

- KEYS6、USB16、AUDIO4、COVER6、POTS3、AUDIO6 的走线全部由脚本给定坐标，逐段写明，没有用自动布线。
- USB 板以下走线是手工预布：VBUS 铺铜、CC1 出线、D+ 在两排焊盘之间的交叉、D− 经 In2 的交叉、VBIAS。其余网络用 Freerouting 2.1.0 自动布线：D± 类限制只能走 F/B 层，In1 设为电源层不允许布线。之后用脚本补 GND 过孔，并对每处地铜孤岛做了处理。音频板和盖板只对 ECO 改动所影响的网络做“撕线 → 自动重布”，其余 R3 走线保持锁定。
- 自动布线的结果只通过了 DRC，**没有人工逐线做 SI 审查**。
