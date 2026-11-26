# SmartVio R4 主板版图修改记录（终止于中途，仅作参考）

> **状态：未完成，不发布，不出 Gerber。** 产品已改为单板方案，R4 主板版图按负责人指示在中途停止。
> 本文件只作为单板设计的参考。所有结论都以下面列出的 DRC 结果为准。

## 文件
- 版图：`pcb/SmartVio-main-r3-linked.kicad_pcb` + `.kicad_pro` + `.kicad_dru`（KiCad 10.0.6 原生格式）
- 修改过的封装：`pcb/footprints-r4-edited/`（来源为 `footprints/SmartVioV25.pretty` 和 `SmartVioV26.pretty`）
- 脚本：`pcb/scripts-main/`（pcbnew Python 脚本：网表同步、网络拆分、栅格布线器、加宽、主干/支路分类）
- DRC：`drc/main-r4-drc-final.json`（R4 最终状态）；`drc/main-r3-baseline-drc.json`（R3 基线：0 条违规）

## 最终 DRC（`--refill-zones`，全部严重度）
- **错误 51 条**：track_width 32、clearance 13、items_not_allowed 6（ADC_SCK 仍走 In3/In4）
- 警告 50 条：丝印 32、lib_footprint_mismatch 6、dangling 6、其他 6
- **未连接 53 处**，全部列在下方
- 原理图一致性检查（schematic parity）：**没有运行**（本轮在此之前停止）

## 逐条状态
| ECO | 状态 | 说明 |
|---|---|---|
| L-01 大电流通路 | **部分完成** | 已在 .kicad_pro 中新建网络类 PWR_IN 0.6/间距 0.2、PWR_BAT 0.5、PWR_SW 0.9；已在 .kicad_dru 中加入 ECO 规定的外层/内层最小线宽、焊盘颈和小负载支路豁免规则，另加 `R4_SL_BRANCH` 规则区，用于标记由 trunk.py 按主干焊盘表算出的小负载支路（≥0.2 mm）。已自动加宽 40 段。**还没有做**：VBUS_RAW 主干（J3411→U1001.5，尚未连通）、USB_5V_SAFE 和 SYS 主干重新布线（还剩 32 处线宽错误、13 处间距错误）、BUCK_L1/L2 铺铜、换层处 ≥4 个过孔。U1001 一带必须重新布局，脚本无法完成。 |
| L-03 VIPPO | 未做 | 只有设计方案：在 setup 中设 filling/capping = yes，并加制造说明 “IPC-4761 Type VII”。 |
| L-04 散热过孔 | 未做 | — |
| L-06 去耦 | 部分完成 | C1302 已移到 U1301 东侧 (73.0,21.6)，为 SYS 走廊让出空间；C1301 已移到 (68.6,19.6)；R1301 已移到 (71.25,17.75)。U902、U801 等器件的去耦电容没有移动。 |
| L-07 | 未做 | DRU 中已有 ADC_SCK 禁止走 In3/In4 的规则，因此报 6 条错误。R601 和 R812 没有移动。 |
| L-08 | 封装库已改，版图中未全部替换 | TPS63070：阻焊外扩 0、钢网每边 −5%；TSOT-23-8：焊盘 0.40×1.20、中心距 ±1.31；U501、U1001、U1101、U1921 加 1 脚丝印点和 Fab 倒角。版图中只替换了 J3411、J3405，其余实例还需在版图中从库更新。 |
| L-09（主板端） | 完成 | J3405 移到 (2.45,3.05)，焊盘 0.9 mm，6 个焊盘内过孔移到焊盘外。 |
| L-10（主板端） | 已放置，未完成连线 | J3411 USB16 热压焊盘放在 (36.75,1.25)，与 main-board-interface.json 一致；courtyard 缩到焊盘区，FPC 包络画在 F.Fab。删除 H_USB_1_M、H_USB_2_M。按接口要求，R810 改放 B 面 (43.0,3.8)。 |
| L-12 | 已放置 | U1801 放在 B 面 (16.0,5.5)，C1801 放在 B 面 (19.0,2.5)，删除 J1801。TEMP_SCL、TEMP_SDA 已布线；V3D 和 GND 未连接。 |
| L-13（主板端） | 完成 | J3403 为 4 焊盘，GND 焊盘在 (46.8,21.3)，焊盘顺序 3/2/1/4，为已接受的警告。K1205、C222、K1207 南移 0.9 mm。 |
| L-14 | 不做 | 原理图没有改归属，D1201–D1207 留在主板。 |
| L-16 | 未做 | 原理图仍有 J901，不能删除。 |
| L-17 | 不做 | 原理图仍为 0805，要改须先改原理图封装。 |
| L-22 网表同步 | 大部分完成 | 端点改名为 J3401–J3411；补齐值、字段、symbol path；新器件全部落位：Q1202 (53.25,24.75)、Q1203 (49.25,32)、R1212–R1215、R324、R704、C1004 在 B 面 (67.6,3.25)、C1109 (66.4,19.0)、D1303 在 B 面 (37.5,19.5)；拆分 SSR_SINK、V3LOAD 等网络。 |

## 未连接 53 处（按网络）
- GND 17：主要是新器件和 J3411 GND 焊盘的接地过孔。
- VBUS_RAW 4，USB_5V_SAFE 3，SYS 2：属于主干，未完成。
- SSR_SINK 3、SSR_SINK_HP 1、SSR_SINK_RET 1：PhotoMOS 分组后的连线。
- 其余各 1 处：CC_FAULT_N、USB_DATA_DISABLE、USB_DATA_FAULT_N、USB_DP_MCU、V3D、V3LOAD、DAC_UNMUTE、DAC_UNMUTE_MCU、HP_EN_MCU、HP_EN_VALIDATED、HP_PORT_ENABLE、RET_PORT_ENABLE、PWR_PB、PWR_PB_SENSE、ADC_FS、ADC_FS_SRC、LINE_L_PORT、RETURN_R、RET_AC_R、RF_ENABLE、RF_RX。
- J501 的两个 MP 机械焊盘：原理图把两者放在同一个 unconnected-* 网络，应改为不分配网络。

原因：板面过密。自写栅格布线器和 Freerouting 2.1.0 都无法在不拆除既有走线的情况下完成这些连接，Freerouting 停在 40 处未布通。
