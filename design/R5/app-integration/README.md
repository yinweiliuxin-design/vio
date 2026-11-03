# R5 实体机与 App 联调（可行性验证）

日期：2026-11-03。App 仓库：`yinweiliuxin-design/dzxtqapp`（Silvio V29）。

## 结论

| 运行方式 | 能否控制 R5 | 说明 |
|---|---|---|
| 安卓手机 Chrome 打开网页版 | **可行** | 已按 R5 台架固件的蓝牙协议做好连接模块和联调页，仿真全部通过，待开发板实测 |
| 电脑 Chrome / Edge | 可行 | 适合开发时联调 |
| 安卓 App 外壳（WebView） | **目前不行** | WebView 没有网页蓝牙，要补原生蓝牙桥接，约 3–5 个工作日 |
| iPhone | 不行 | iOS 不支持网页蓝牙，要原生 App；按方案首发只做安卓 |

## 做了什么

在 App 仓库里新增（没有改动现有页面）：

| 文件 | 作用 |
|---|---|
| `web-source/dist/r5-device.js` | R5 设备连接模块：协议编解码、连接、读写、通知、往返时间 |
| `web-source/dist/r5-device.html`、`r5-device-page.js` | 设备联调页：环境检查、连接、输出切换、四个参数滑条、19 项自动联调、导出联调记录 |
| `web-source/tests/r5-device.test.mjs` | 12 项单元测试，用模拟设备复现台架固件的规则 |
| `docs/R5-设备联调与可行性.md` | 结论、协议、真机联调步骤、原生桥接要做的事 |

验证结果：

- 新增 12 项测试全部通过；全仓库 721 / 721 通过；构建正常。
- 联调页在无头 Chromium 里连模拟设备：自动联调 19 / 19 通过，没有脚本错误。
- 模拟 App 外壳（WebView）和 iPhone 时，页面给出正确提示。

模拟设备代表不了真实无线环境。连接速度、往返时间、断线重连要用开发板实测。

## 真机联调（约 30 分钟）

需要 ESP32-S3-DevKitC-1 开发板一块、安卓手机（Chrome）、R5 台架固件（`verify/firmware/`，不接编解码器也能跑蓝牙）。

1. 用 esptool 把台架固件烧进开发板，串口能看到 `ready`。
2. 手机 Chrome 打开 App 站点的 `/r5-device.html`（必须 HTTPS）。
3. 点“搜索并连接”，选 `SmartVio-R5-bench`，电量显示 87 %（假数据）。
4. 点“开始自动联调”，19 项全部通过，往返时间平均 200 ms 以内。
5. 串口输入 `vol 40`、`out spk`，页面数值 1 秒内跟着变。
6. 点“复制联调记录”存档。

## 代码在哪里

- App 仓库本地分支 `claude/r5-device-ble`，提交 `a9ebd23`。**还没有推送到 GitHub**：这个会话没有 App 仓库的推送权限。
- 同样的改动保存在本目录的 `0001-R5-device-ble.patch`。在 App 仓库里执行：

```bash
git checkout -b claude/r5-device-ble
git am 0001-R5-device-ble.patch
```

## 下一步

1. 用开发板按上面的步骤实测。
2. 乙方在阶段 3 中期给出正式 BLE 接口文档后，App 补齐线路输出、充电状态、固件版本、故障代码和调音器，再接进 App 主界面。
3. 决定安卓 App 外壳首发时是否要控制设备；要的话做原生蓝牙桥接。
