# SmartVio 项目全量安全归档 / 2026-10-15

本目录保存已定位的项目代码、数据、原生EDA、PCB、图纸、BOM、固件输出、效果图及历史版本。它是研发备份，不是生产放行包。

## 先看这些

- `SNAPSHOT.json`：范围、分片及 SHA256。
- `FILE-MANIFEST.json.gz`：每个恢复路径、原文件与过滤后文件的 SHA256。
- `PRIVACY-REPORT.json.gz`：排除与脱敏清单。
- `preview/`：可直接查看的近期效果图和资料。
- `RESTORE.py`：只使用 Python 标准库的校验恢复工具。

## 恢复

下载或克隆仓库后，在本目录执行：

```text
python RESTORE.py --verify-only
python RESTORE.py --target E:/codex/SmartVio-restored-20261015
```

目标目录必须全新或为空；不会覆盖现有工程。检查每个分片、完整归档、对象哈希和 ZIP CRC 后才开始恢复。文件较多，Windows 建议开启长路径支持。

恢复后的目录：

- `deliveries/`：R3 当前硬件资料及 R1/R2、首样准备包等历次交付。
- `client-current/`：本次读取的客户端、后台、测试、数据库迁移和资源文件。
- `client-reports-history/`：软件历次报告、界面截图和可用历史源文件。
- `engineering-history/`：V27 及更早原理图、PCB、脚本、设计资料。
- `generated-images/`：本研发对话已生成的效果图。
- `visualizations/`、`media/`：相关可视化与媒体。

## 版本说明

硬件存在后续 R3 资料，不能把旧 V27 状态当成最新整机状态；各原报告保留其历史版本含义。最新软件源码也与早期概念客户端不同。本次只备份，不修改功能、不复跑硬件验证，也不将 HOLD 改成 PASS。

原仓库 `CLOUD_HANDOFF.md` 和已存在的检查点保留不变。请以本目录了解此次备份范围；旧交接文档中的日期和工程状态仅代表历史。

## 安全与完整性

旧 ZIP/TAR 的内容先检查，再以 `__contents` 目录恢复，避免把密码或运行数据库藏在压缩包里上传。同一内容只存储一次，但清单保留所有版本路径。
存在敏感信息或无法检查的文件会列入排除清单，保留在本地原位置。脱敏源码中的凭据需要在目标环境自行配置；不会上传真实用户数据库或无关电商资料。
依赖工具链及第三方安装缓存不打包，依赖清单、项目脚本、锁文件按筛选结果保留。所有原件保持不变。

恢复文件数：20259；唯一内容数：7123。
- engineering-history: 5459
- deliveries: 12306
- client-current: 140
- client-reports-history: 2316
- generated-images: 37
- media: 1

## 可直接浏览

- [V16 客户端源码（较新，可直接浏览）](current/client-V16/)
- [V15 客户端源码（全量采集时的历史副本）](current/client/)
- [R3 原生EDA、PCB和元件资料](current/hardware-R3/)
- [机械图与装配效果](preview/R3-mechanical-review.pdf)
- [24页当前原理图](preview/R3-schematic-review.pdf)

![已生成的整机效果图（外观参考，非生产放行）](preview/violin-render-20261009.png)

本次全量采集时的客户端 Git 源提交：`2c7f0a7ce5ffd97372092a1cc4ccaafc36439fbd`（V15）。直接浏览的副本与归档内相同，若脱敏过，以清单记录为准。

采集后另一个任务完成了 V16，源码提交为 `6f461b9612ac69310ec269f289e429fb473664bb`。其已验证备份保留在 [V16 检查点](../../checkpoints/2026-10-15-app-v16-6f461b9612ac/)，不要用本目录的 V15 副本覆盖 V16。历史 V26 及其他已有检查点同样保留，不重写旧交接文档。

V16 的过滤后可浏览副本单独放在 `current/client-V16/`，其源哈希、过滤后哈希及排除项记录于 `V16-DIRECT-FILES.json`。它不改变 20,259 条路径的历史归档清单。
