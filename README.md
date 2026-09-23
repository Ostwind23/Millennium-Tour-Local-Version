# Millennium Tour local version · 发布仓库

本仓库是《千年之旅》本地离线版（学习版）的**分发与更新仓库**，只存放发布产物与发版工具，不含游戏源代码。

## 免责声明（请务必先读）

- 本项目是**学习交流用途的技术研究产物**，仅供个人学习、研究与体验使用，完全免费，**不得用于任何商业用途、公开传播或二次分发**。
- **下载后请于 24 小时内自行删除**。
- 使用本产物产生的一切后果由使用者自行承担。

## 玩家侧

- 在 [Releases](../../releases) 页下载最新 APK，覆盖安装即可，本地存档自动保留。
- 首次启动需要导入原始游戏资源（约 6GB 解压空间）：
  - **本机导入**：自行准备完整的资源压缩包（7z/ZIP），在启动页选择导入；
  - **云端下载**：在启动页选择「云端下载基底资源」，从本仓库的 `base-data` 发行页拉取（GitHub 直连，**国内需要海外网络加速**）。
- 游戏内的存档管理页提供「检查更新」，可自行查看是否有资源热更新或整包更新。
- 最新版本清单（供游戏内"检查更新"功能读取，地址固定不变）：

  ```
  https://github.com/<OWNER>/<REPO>/releases/latest/download/update.json
  ```

## 维护者侧

发版流程见 [tools/publish_release.py](tools/publish_release.py) 的文件头注释。

## update.json 格式约定

```json
{
  "versionCode": 152,
  "versionName": "v152",
  "apkFile": "qnzl-local-v152-signed.apk",
  "size": 803577152,
  "sha256": "<小写十六进制>",
  "minVersionCode": 0,
  "publishedAt": "2026-09-22",
  "changelog": "本次更新的玩家可读说明"
}
```

- `versionCode` 单调递增，是游戏内比较新旧版本的唯一依据。
- `sha256` 校验下载完整性；游戏内下载完成后先校验再安装。
- `minVersionCode` 预留给强制整包更新的下限（当前恒为 0）。
