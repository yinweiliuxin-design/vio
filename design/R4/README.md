# SmartVio R4 设计方案

在线版（含效果图）：https://claude.ai/artifact/BZ7bgUTucvGM85bej3NQhv ，本地 `report/index.html`。

装琴效果图：`report/img/r4-on-violin-showcase.jpg`（你的实拍琴 + R4 模块按 3.18 px/mm 合成）。整机方案（琴 + 模块 + App）：https://claude.ai/artifact/1Rpw8Ssot14Bnj9UHH1J9D

基线是 R3 完整交付包和 `review/R3-2026-10-13/` 的两轮审核。R4 只做让样机装得上、能出声、能安全充电、日常好用的修改，不加功能、不换架构、不加芯片。原 R3 文件一律未改。

| 路径 | 内容 | 状态 |
|---|---|---|
| `DECISIONS.md` | 7 个待定问题的定案 | 定稿 |
| `checks/` | PCM1864 时钟与 SAI、电源 IC 逐脚与封装核对 | 完成 |
| `mechanical/` | 改好的 CadQuery 源、R3→R4 补丁、零件 STEP、装配扫掠结果、`CHANGES.md` | 已重建，0 干涉 |
| `firmware/` | R3→R4 补丁、改动源码、Linux 构建脚本、ELF/BIN/MAP、`CHANGES.md` | 已编译，主机测试全过，硬件测试 0 |
| `eco/` | 原理图 ECO（E-01…E-14）、PCB/FPC ECO（L-01…L-22） | 待在 KiCad 10 执行并跑 ERC/DRC |
| `report/` | 设计方案页与 5 张效果图 | — |
| `tools/` | `photo_r4.html` + `shot_alpha.cjs` 渲染模块俯视透明图，`composite_r4.py <照片> <模块图> <输出目录>` 合成装琴效果图；渲染：`step2mesh.cjs <mechanical 目录> r4mesh` 生成网格，`real_r4.html?view=hero|exploded|internal|section|product` | — |

## 还需要做的事

1. 用万用表量 Kycon STX-353K7A-6N：插入 TRS 插头前后 4–5、5–6 是否导通，决定 R323 和固件 `HP_DETECT_ACTIVE_HIGH`。
2. 在 KiCad 10 执行两份 ECO，跑 ERC/DRC/原理图一致性；画 KEYS6、USB16、AUDIO4 FPC 平面图并做纸样。
3. 用 ESP-IDF 5.4.3 重编 ESP32（需补 sdkconfig）；首次配对新耳机需在 ESP32 加搜索和 NVS 保存。
4. 首样台架：FW-RESET-KILL、续航与关机电流、卡扣/按键/异响/插拔力、扬声器音量。
5. 结构：最坏尺寸链、工程图重出、NTC 预压、琴腔配钻。
