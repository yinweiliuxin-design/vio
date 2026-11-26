# SmartVio R4 原理图 ECO 执行记录（KiCad 10.0.6 原生文件）

日期：2026-10-15。基线：R3 原生原理图（`work/r3/eda`，ERC 0 违规，网表 319 器件 / 308 网络）。
结果：R4 原理图 `eda/`，网表 `R4-netlist.xml`（348 器件 / 316 网络），PDF `R4-schematic.pdf`（25 页，新增 A34）。

## 方法

- 用 Python 写的无损 S 表达式编辑器（`scripts/sexp.py`、`schlib.py`、`r4_sch_eco.py`）。每次运行都从 R3 原件重建 R4，
  可重复执行；没改动的 9 张图纸与 R3 逐字节相同（保留原 CRLF 行尾）。
- 每条改网络操作都先核对 ECO 给出的标签坐标、原网络名、该标签只服务这一个引脚，不符就中止。
- 新器件按本设计的风格放置：每颗器件有自己的库符号（同时写入图纸内嵌库和 `SmartVio.kicad_sym`，两者保持一致），
  每个引脚接一段 5.08 mm 导线和一个全局标签，放在相关器件所在图纸的空白行；uuid 用 uuid4，instances 路径为
  `/根 uuid/图纸 uuid`。新增和改值器件都带隐藏字段 `R4_ECO`（ECO 编号）。
- 校验：`scripts/r4_verify.py` 对比 R3/R4 网表，逐条核对 ECO 期望，结果在 `eco-verification.json`：
  **142 项全部通过，0 项无法解释的差异**（每个器件增删、每个字段变化、每个引脚网络变化都对应到某条 ECO）。
- 改动前的备份：`SCRATCH/sch4/backup_r4_eda_pre_eco/`；R3 原件 `work/r3/eda` 未动。

## ERC

`kicad-cli sch erc --severity-all`：**0 个错误，3 个警告**，都是 `footprint_link_issues`（封装库里还没有这几个封装）：

| 警告 | 原因 | 谁来处理 |
|---|---|---|
| `SmartVioV26:FPC_USB16` 不存在 | 新 FPC-USB16 本体封装，由 FPC/USB 板负责人新建 | FPC 负责人 |
| `SmartVioV26:FPC_AUDIO4` 不存在 | 新 FPC-AUDIO4 本体封装 | FPC 负责人 |
| `SmartVioV26:FPC_USB16_HotBar_Main_P0.70` 不存在 | 主板端 16 焊盘热压焊盘（L-10：0.40×1.60，节距 0.70） | 主板负责人（名字可改，改后同步原理图 Footprint 字段） |

这 3 个警告不影响网表连接，封装建好后自动消失。为 D401、J3412 用到的 KiCad 自带库，已在 `eda/fp-lib-table` 增加
`Diode_SMD`、`Connector_FFC-FPC`（`${KICAD10_FOOTPRINT_DIR}`）；PCB 工程的 fp-lib-table 也需要同样两行。

## 逐条结果（eco-schematic.json）

| ECO | 状态 | 实际改动 | 说明 |
|---|---|---|---|
| E-01 | 完成 | R322 1k→100k；C320 10nF C0G→100nF X7R（封装改为 CC0603KRX7R7BB104 焊盘）；J301.6 GND→**HP_DET_B**；新增 **R323 0R（DNP）**，1=HP_DET_B，2=GND（A12） | HP_DET_B 两个节点。R323 默认不装，首样万用表判定后再定 |
| E-02 | 完成 | R1705/R1709 2.2M、R1706/R1710 1.5M、R1707/R1711 10M（1%）；R1103 2.2M；R1304 4.7M；U1921.5 与 C1921.1 SYS→**USB_5V_SAFE** | 已核对：NTC 分压由 U1922（USB_5V_SAFE 供电）激励，TPS3700 输入不会高于其 VDD，断电时不反灌 |
| E-03 | 完成 | R1201–R1207 270R→390R；K1201.2/K1202.2→SSR_SINK_HP，K1206.2/K1207.2→SSR_SINK_RET；新增 Q1202、R1212、R1213、Q1203、R1214、R1215（A22）；U801.61 PD14=HP_PORT_ENABLE，U801.62 PD15=RET_PORT_ENABLE（删 no_connect） | **补充改动**：U801 符号里 PD14/PD15 的引脚电气类型原为 `no_connect`，直接接网会报 ERC 错误，已改为 `bidirectional`（库与内嵌一致）。SSR_SINK 现只剩 K1203–K1205 + Q1201 |
| E-04 | 完成 | R590.2 GND→V3D（CHG_EN1 上拉） | — |
| E-05 | 完成 | R1005 6.65k→2.49k；新增 C1004 10nF C0G，U1001.10 ITIMER=EFUSE_ITIMER（删 no_connect） | U1001.3 AUXOFF 保持悬空（已校验） |
| E-06 | 完成 | R1003 37.4k→39.2k 1% | — |
| E-07 | 完成（有调整） | 新增 D401 SMF12A，K=VBUS_RAW，A=GND（A13） | ECO 写的是 `Device:D_TVS`；本工程只用 SmartVio 库，所以建了同风格的 `SmartVio:D401` 符号（1=K，2=A，与 `Diode_SMD:D_SOD-123F` 焊盘 1=K 一致） |
| E-08 | 完成 | U901.3、C902.1、C903.1、R902.2、J902.1 V3LOAD→V3D | V3LOAD 只剩 U601/U701/FB1101/U1901 等 |
| E-09 | 完成 | 新增 C1109 22µF 0805（CC0805MKX5R6BB226），V3D/GND（A21） | 值写作 “22uF 10V”，与 C1104/C1105 同料号便于 BOM 合并 |
| E-10 | 完成 | U801.22→DAC_UNMUTE_MCU，U801.23→HP_EN_MCU；新增 R704 1k（A16），R324 1k（A12） | DAC_UNMUTE 现为 R703/U701.17/R704.2；HP_EN_VALIDATED 为 R320/U301.13/R324.2 |
| E-11 | 完成 | 新增 D1303 BAS116（A24），1 A=PWR_PB_SENSE，2 NC（打 X），3 K=PWR_PB；U801.51 PB12=PWR_PB_SENSE（删 no_connect，引脚类型同样由 no_connect 改为 bidirectional） | 风险提示：按键按下时 PB12≈BAS116 正向压降（内部上拉约 80 µA 时约 0.6–0.7 V），低于 STM32 VIL（0.3·VDD≈1.0 V）但余量不大，首样需实测 |
| E-12 | 完成 | R2351 499R→3.32k 0.1%（RT0603BRD073K32L） | — |
| E-13 | 完成 | C1707 10nF→100pF C0G 50V（C0603C101J5GACTU），封装按 ECO 改为 `SmartVioV25:C_0603_1608Metric` | 主板需换封装（同为 0603） |
| E-14 | 完成 | U902（MAX98357A）裸焊盘引脚号 EP→17（库与 A19 内嵌一致） | 网表中 U902.17=GND，与 ADI_T1633_4_Official 焊盘 17 一致 |

## PCB/FPC ECO 的原理图部分（eco-pcb.json）

| ECO | 状态 | 实际改动 |
|---|---|---|
| L-10 USB16 | 完成 | 新图纸 **A34** 中加入主板端 J3411（原名 J_USB_M，热压焊盘，不进 BOM）、FPC 本体 FPC3406（FPC_USB16，焊盘 S1–S16 主板端 / T1–T16 USB 板端）、USB 板端 J3412（原名 J_USB_U，Hirose FH12-16S-0.5SH(55)，进 BOM）。16 芯按 L-10 表：1 USB_DATA_FAULT_N、2 USB_DATA_DISABLE、3 CC_FAULT_N、4 V3D、5/8/10/11/12 GND、6 USB_DM_MCU、7 USB_DP_MCU、9 USB_5V_SAFE、13–16 VBUS_RAW（4×VBUS、5×GND，已校验）。R3 的 H_USB_1/H_USB_2 只在 PCB 上存在，原理图中不再有任何对应物，PCB 上应删除 |
| L-12 TMP117 并入主板 | 完成 | 删除 J1801、J1802（及其导线/标签和库符号）；U1801/C1801/R1801/R1802 不变；TEMP_SCL=R1801.2+U1801.1，TEMP_SDA=R1802.2+U1801.6；A29 改名为“A29 主板（电池侧）板温 TMP117 / R4 并入主板” |
| L-13 AUDIO4 | 完成 | A34：J3403（原 H_AUDIO_2_M）、FPC3402（FPC_AUDIO4）、J3404（原 H_AUDIO_2_R），4 脚：1 RETURN_L_PORT、2 RETURN_R_PORT、3 SEND_T_PORT、**4 GND（新增）** |
| L-19 parity | 完成 | 所有板间端点都有符号（A34，共 18 个）：AUDIO6 J3401/FPC3401/J3402，AUDIO4 如上，KEYS6 J3405/FPC3403/J3406，COVER6 J3407/FPC3404/J3408，POTS3 J3409/FPC3405/J3410，USB16 如上。校验：R3 各板上 12 个 H_* 端点焊盘的网络与 R4 符号引脚逐一相同（H_AUDIO_2 另加 4 脚 GND）。FPC3403 的封装已对齐 FPC 负责人新建的 `SmartVioV26:FPC_KEYS6_R4` |

**位号说明（偏离 ECO 文字的地方）**：ECO 用的 `H_AUDIO_1_M`、`J_USB_M`、`FPC_AUDIO6` 这类名字不以数字结尾，
KiCad 会把它们当成“未标注”（导出网表时报 annotation errors，图形界面“从原理图更新 PCB”会要求重新标注并改名）。
所以原理图里用合法位号 J3401–J3412、FPC3401–FPC3406，原名保存在每个符号的 `Endpoint_ID` 字段，
对照表在 `sch-endpoint-refmap.json`。**PCB 侧需要把对应封装的位号改成新位号**，否则 parity 对不上。

其他约定：
- FPC 本体焊盘 S=主板端、T=远端（与 R3 FPC_AUDIO6 等现有封装一致）。
- H_* 焊盘端点、J3411 和 FPC 本体在原理图中都设为 in_bom=no（与 R3 FPC 封装的 exclude_from_bom 一致；FPC 由线束/FPC BOM 管理）。R3 的 H_* 封装属性是 smd（进 BOM），PCB 侧建议改成 exclude_from_bom，否则 parity 会报属性不一致。
- 多板共用一份原理图：对单块板跑 `--schematic-parity` 时，其他板上的器件都会显示“缺封装”。需按板筛选比对（脚本可参考 `scripts/r4_verify.py` 的 L-19 部分）。

## 网表差异摘要（R3 → R4）

- 新增器件 31：12 颗贴装件（Q1202、Q1203、R1212–R1215、R704、R324、C1004、C1109、D401、D1303）+ R323（DNP）+ 18 个端点/FPC 符号。删除 2：J1801、J1802。
- 新增网络 11：HP_DET_B、SSR_SINK_HP、SSR_GATE_HP、HP_PORT_ENABLE、SSR_SINK_RET、SSR_GATE_RET、RET_PORT_ENABLE、EFUSE_ITIMER、DAC_UNMUTE_MCU、HP_EN_MCU、PWR_PB_SENSE。没有删除任何具名网络。
- 改值 21 颗（ECO 文中合计写“22 处”，按条目逐颗数为 21：E-01 2、E-02 8、E-03 7、E-05/E-06/E-12/E-13 各 1；R590 属于改接不是改值），引脚网络变化 21 处（含 U902 EP→17），全部对应到 ECO（详见 `eco-verification.json` 的 diff 部分）。

## 留给人工 / 其他负责人

1. 新建 3 个封装（FPC_USB16、FPC_AUDIO4、主板 USB16 热压焊盘），名字若不同，改原理图 Footprint 字段（`r4_sch_eco.py` 中一处）。
2. PCB 侧：H_*/J_USB_*/FPC_* 位号改为 J34xx/FPC34xx；删 H_USB_*、J1801/J1802、sensor 板；H_AUDIO_2_M/R 改 4 焊盘（原理图暂用 `WirePads_4_P1.5`，L-13 的焊盘顺序 4-1-2-3 需要专用封装时请同步字段）；C320、C1707 换封装；D401 用 `Diode_SMD:D_SOD-123F`。
3. L-16 中“删除 J901 或改 0 Ω DNP”属于版图取舍，本轮原理图**未改** J901；若主板删掉 J901，需要回到原理图同步。
4. 首样实测项：J301 触点 5/6 定义（决定 R323 装否）；PB12 经 BAS116 的低电平余量；关机电流 ≤25 µA；ESP32 改 V3D 后的蓝牙杂散；TPS25947 ITIMER 实际时间常数。
5. 原理图仍是“ENGINEERING CAPTURE / HOLD”状态；以上 ERC/网表校验只证明连接与 ECO 一致，不代表电路已实测验证。
