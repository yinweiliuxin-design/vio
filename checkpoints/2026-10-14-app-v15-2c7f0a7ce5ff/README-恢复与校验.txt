Silvio / VELLEN 应用完整源码检查点

冻结提交：2c7f0a7ce5ffd97372092a1cc4ccaafc36439fbd
文件数：132
ZIP SHA-256：b33ec4925149abaf84f73aa511fa803162cf25011a601fa0631a7300759150ff

下载此目录全部 source.zip.part-*.b64、FILE-MANIFEST.json、RESTORE-VERIFY.cjs，不修改其名称。
每份分片为 ASCII Base64 文本；解码后的二进制数据最大256 KiB，文本本身约342 KiB。Node脚本会自动解码并合成ZIP。
清单 bytes 与 sha256 指解码后的数据，encodedBytes 是文本文件大小参考。
先校验（Node.js 24）：node RESTORE-VERIFY.cjs --verify-only
恢复到新的空目录：node RESTORE-VERIFY.cjs "D:/Silvio-Restore"
脚本校验每份分片 SHA-256、整包 SHA-256、所有 ZIP CRC 和逐源文件 SHA-256；拒绝覆盖现有目录。

包含当前 Git 提交的所有软件源码、报告、迁移及正式 App 美术素材（35封面、6教学照片、2商标）。
不包含生产数据库、用户录音/视频、浏览器个人记录、账号口令或部署凭据；源码恢复不等于用户云数据恢复。
旧 GitHub V26 等目录由提交方保留，本工具从不删除远端或上传文件。

运行和发布说明位于恢复后的 smartvio-mobile/README.txt；服务器所需环境配置单独设置。
