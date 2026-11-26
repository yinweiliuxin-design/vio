# R5 实体机与 App 联调

更新：2026-11-26。

## 现在用哪个补丁

| 补丁 | 针对 | 状态 |
|---|---|---|
| `0001-R5-device-ble-V39.patch` | smartviolin 仓库 violinapp 分支（提交 `0b03f31`）的 `web-workspace/apps/international` 和 `web-workspace/apps/mainland` 两套工程，即 App 现行源码（V39 检查点，版本标记 V38） | **现用** |
| `0001-R5-device-ble.patch` | dzxtqapp 仓库（Silvio V29） | 旧版，保留备查。dzxtqapp 已不是 App 现行代码 |

两个补丁新增的连接模块、联调页和测试相同；V39 补丁两套工程各放一份，说明文件已按交付包 5.2 更新。

## 结论

| 运行方式 | 能否控制 R5 | 说明 |
|---|---|---|
| 安卓手机 Chrome 打开网页版 | **可行** | 已按 R5 台架固件的蓝牙协议做好连接模块和联调页，仿真通过，待开发板实测 |
| 电脑 Chrome / Edge | 可行 | 适合开发时联调 |
| 安卓 App 外壳（WebView） | **目前不行** | WebView 没有网页蓝牙，要补原生蓝牙桥接，约 3–5 个工作日 |
| iPhone | 不行 | iOS 不支持网页蓝牙，要原生 App；首发只做安卓 |

## V39 补丁的内容和验证

每套工程新增（不改现有文件）：`dist/r5-device.js`、`dist/r5-device.html`、`dist/r5-device-page.js`、`tests/r5-device.test.mjs`、`docs/R5-设备联调与可行性.md`。

2026-11-26 在云端 Linux、Node 22 下验证：

- 补丁在 violinapp 最新提交上能直接打上；
- 国际版、大陆版各 842 / 842 测试通过（原有 830 + 新增 12）；构建正常，`/r5-device.html` 已打进站点；
- 联调页在无头 Chromium 里连模拟 R5，自动联调 19 / 19 通过，没有脚本错误。

真机、安卓外壳、iPhone、站点发布都没有做。App 工作区指定 Node 24，合并后在 Windows 上用 Node 24 再跑一遍。

用法：在 smartviolin 仓库切到 violinapp 分支，`git am 0001-R5-device-ble-V39.patch`。补丁没有推送到 violinapp。

## App 还要改的其他内容

见 `App联动更新清单-20261126.pdf`：现在就能做 9 项，等电子厂《BLE 接口文档》后做 8 项，可选 2 项；每项写了改哪个文件和合格标准。复核发现的主要问题：

1. “将当前预设保存至琴”走 `storePreset`，要求琴声明“预设存储”；已定 R5 不存预设，接上 R5 后会一直失败，要改成逐项写参数；
2. 这个按钮只发音量、混响两个值，R5 的参数是音量、音色、效果、伴奏比例；
3. “我的设备”页仍是概念图和“待硬件验证”。

## 真机联调（约 30 分钟）

需要 ESP32-S3-DevKitC-1 开发板一块、安卓手机（Chrome）、R5 台架固件（`verify/firmware/`，不接编解码器也能跑蓝牙）。

1. 用 esptool 把台架固件烧进开发板，串口能看到 `ready`。
2. 手机 Chrome 打开 App 站点的 `/r5-device.html`（必须 HTTPS）。
3. 点“搜索并连接”，选 `SmartVio-R5-bench`，电量显示 87 %（假数据）。
4. 点“开始自动联调”，19 项全部通过，往返时间平均 200 ms 以内。
5. 串口输入 `vol 40`、`out spk`，页面数值 1 秒内跟着变。
6. 点“复制联调记录”存档。
