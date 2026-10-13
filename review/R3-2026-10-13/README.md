# SmartVio R3 资料审核与设计建议（2026-10-13）

完整报告（含效果图与对比图）：`report/index.html`，在线版 https://claude.ai/artifact/AZAdEie6JrY4WN4k6XCv58

本目录只做审核、建模渲染和方案建议，没有修改任何原设计文件。R3 的原生 KiCad、STEP、固件源码尚未收到，`inputs/` 里是本次收到的 PDF 和工作簿（哈希见 `inputs/SHA256SUMS.txt`）。

## 结论

资料之间数量、尺寸、位号基本一致，可继续工程评审与 DFM。原理图有 2 处设计错误必须先改，另有 9 项高风险建议投板前处理。

## 必须修改

- **A1** U1921（TPS3700）`INA+ = CELL_NTC_SENSE`、`INB− = NTC_COLD_DIV` 接反（第 24 页 A33）。现接法下任何温度都禁止充电；对调后窗口约 7–40 °C。
- **A2** 关机漏电约 0.48 mA：R1705/R1706、R1709/R1710 两组 25 kΩ 分压常接电池（各 168 µA），R1103 33 kΩ 在 LTC2954 关机时拉低（127 µA）。按 1000 mAh 约 87 天放空。

## 高风险

- **B1** 无 USB-C 供电能力（Rp）识别，ILIM 1.03 A 可能超出默认端口。
- **B2** TPD2S300 由 V3D 供电，需确认关机/亏电时 Rd 仍有效（C-to-C 充电器死锁风险）。
- **B3** V3A 经单个磁珠取自 V3LOAD，与 ESP32 同一节点，蓝牙突发电流进入模拟电源。
- **B4** 7 个 PhotoMOS 开启时约 50 mA 常耗，并串在耳机输出里。
- **B5** 音频 ESD 器件在主板，离插座太远。
- **B6** USB 子板 9 根散线：保护前 VBUS 走线束、单根地、U90 线（Ø3.2、R10）装不进约 6–11 mm 空间。
- **B7** PLAY 总线 MCU / PCM5102A / MAX98357A / ESP32 四方并联且跨电源域，无隔离。
- **B8** FPC 天线距不锈钢格栅约 0.3 mm，旁边是扬声器和无滤波功放线。
- **B9** 四弦独立拾音未实现（第 4 路 ADC 闲置，需 ≥ 6 路）。

中低风险 C1–C14、文件一致性 D1–D8 见报告。

## 目录

| 路径 | 内容 |
|---|---|
| `inputs/` | 本次收到的 5 份原始资料（改为 ASCII 文件名） |
| `report/` | 审核报告 HTML 与 9 张效果图（R3 当前 5 张、建议方案 4 张） |
| `netlist/` | 从原理图 PDF 逐脚标签还原的网表：319 元件 / 1087 引脚 / 221 网络 |
| `tools/pdf_label_netlist.py` | 网表还原脚本：`python3 -I pdf_label_netlist.py <schematic.pdf> <out.json>`（需 pdfplumber） |
| `tools/render/` | three.js 模型与渲染页，尺寸取自 M-R3-01/02 矢量；`npm i three@0.169.0 three-bvh-csg@0.0.16 three-mesh-bvh@0.8.3 playwright-core@1.48.2` 后用本地 HTTP 服务打开 `render.html?view=hero|top|product|exploded|violin&variant=r3|proposal` |

## 待用户确认

1. 模块装在琴背、滚轮一端朝琴头是否正确。
2. 四弦拾音器型号与是否预留第二颗 ADC。
3. 滚轮操作方式。
4. 外观配色与字符工艺。
5. 续航目标。
6. 是否接受 USB/音频板改 FPC。
