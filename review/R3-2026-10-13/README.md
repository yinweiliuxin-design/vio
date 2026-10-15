# SmartVio R3 资料审核与设计建议

完整报告（第二版，含效果图）：`report/index.html`，在线版 https://claude.ai/artifact/AZAdEie6JrY4WN4k6XCv58

第一版（只依据 PDF 和工作簿）保留在 `report/index-v1.html`。

本目录只做审核、建模渲染和方案建议，没有修改任何原设计文件。

## 更正：第一版 A1 撤回

第一版说 U1921（TPS3700）充电温度窗口的两个输入接反。这是我写错了：TPS3700 的 INA+ 是欠压比较器，INB− 是过压比较器，现接法下 CHARGE_GATE 在约 5–40 °C 释放，原设计正确。**不要按第一版 A1 修改**，照改反而会让它永远无法充电。

## 第二版结论（原生工程包，2026-10-15）

输入：完整交付包 1417 个文件（SHA256 全部与 manifest 一致）。审查范围包括：

- KiCad 原理图与 PCB
- CadQuery 结构源与 STEP
- STM32/ESP32 固件源码与构建产物
- 线束和 BOM 数据、交付脚本
- Web V12

审查分 7 个方向，每个方向的发现都由独立复核员尝试推翻。结果是 107 条有效发现：96 条确认，11 条需实物确认；另有 2 条被推翻，已剔除。按严重度分为致命 4、高 17、中 27、低/提示 59。

按现文件做首样，样机会无法装配、开机后无声。最需要先处理的问题：

| ID | 问题 |
|---|---|
| FW-PARSER-WHITELIST | UART 帧解析只接受类型 1..6/0x80，实际用的帧全部被丢弃，开机自检必失败 |
| FW-PORT-ENABLE-HP | 耳机路由没有置 PA3 PORT_ENABLE，耳机无声 |
| M1 | 上盖是一体件，控制板、USB 板、传感器板装不进去 |
| HB-01 | KEYS6 FPC 制造文件是镜像件 |
| SCH-HPDET-J301 | Kycon 原厂图中触点⑤压在插头尖端，现接法把⑤当独立检测脚（待实物确认） |
| M10 | 按键帽两端都是 Ø6，大于 Ø5.2 孔 |
| M5 | 插座与 USB-C 的插拔受力没有闭合路径 |
| FW-NO-UVLO | 没有低电量关机，电池可被深度过放 |
| FW-USB-SHUTDOWN-LATCH | 插 USB 时关机后锁存不清，拔 USB 前无法再开机 |
| PCB-01 | 大电流通路有 0.15 mm 内层细线瓶颈 |
| PCB-05 | 盖板天线窗口三面 1.0 mm 处被 GND 覆铜包围 |
| HB-02 | USB 子板线束物理上无法装配 |
| M7 | 拾音器输入与 16 条导线没有走线孔 |
| FW-FAULT-LATCH | 瞬态故障永久写入 Flash 锁死 |

其余条目、第一版 A2–D8 的复核状态、以及 113 项核对通过的内容见报告。

## 未完成

- PCM1864 时钟与 SAI 配置交叉核对：因额度中断未做。
- 电源 IC（U501/U1001/U1101/U1301）封装逐脚核对：因额度中断未做。
- TPS3700、TPD2S300、TPS259470 的 TI 规格书不在包内，ti.com 被网络策略拦截，相关结论按器件常识判断。

## 目录

| 路径 | 内容 |
|---|---|
| `inputs/` | 第一次收到的原始 PDF/工作簿（ASCII 文件名，哈希见 `SHA256SUMS.txt`）和 5 个交付脚本 |
| `report/` | 第二版报告 `index.html`、第一版 `index-v1.html`，以及 14 张效果图：`cad-*` 为包内 STEP 原生渲染，`r3-*`/`p-*` 为第一版按图纸重建与建议方案 |
| `findings/native-review-r2.json` | 第二轮各方向审查与复核的原始结果 |
| `netlist/` | 第一版从原理图 PDF 还原的网表 |
| `tools/pdf_label_netlist.py` | PDF 网表还原脚本 |
| `tools/render/` | three.js 渲染：`render.html` 是第一版模型；`real.html` 加 `step2mesh.cjs` 用 occt-import-js 把 STEP 转网格后渲染 |
| `tools/gen_report_v2.py` | 用 `findings/` 结果和第一版报告生成第二版：`python3 -I gen_report_v2.py <dir>`（目录内需有 `wf_all.json`、`report_v1.html`、`report2/img/`） |

## 待用户确认

1. 模块装在琴背、滚轮一端朝琴头是否正确。
2. 四弦拾音器型号与是否预留第二颗 ADC。
3. 滚轮操作方式。
4. 外观配色与字符工艺。
5. 续航目标。
6. 是否接受 USB/音频板改 FPC。
7. 用万用表量 Kycon STX-353K7A-6N 实物：插入 TRS 插头前后，4–5、5–6 之间是否导通。
