# 千年之旅 · 本地版 发布仓库

本仓库是《千年之旅》本地离线版的**分发与更新仓库**，只存放发布产物与发版工具，不含游戏源代码。

- 玩家侧：在 [Releases](../../releases) 页下载最新 APK，覆盖安装即可，本地存档自动保留。
- 最新版本清单（供游戏内"检查更新"功能读取，地址固定不变）：

  ```
  https://github.com/<OWNER>/<REPO>/releases/latest/download/update.json
  ```

- 维护者侧：发版流程见 [tools/publish_release.py](tools/publish_release.py) 的文件头注释。

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
