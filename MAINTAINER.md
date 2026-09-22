# 维护者发版流程

## 日常发版（本地构建链已产出签名包之后）

```bash
python tools/publish_release.py \
    --apk  ../..	/_build/qnzl-local-vNNN-signed.apk \
    --version-code NNN --version-name vNNN \
    --changelog-file ../../灰度测试发布说明-vNNN.md
```

脚本会自动：算 sha256 和体积 → 生成 `update.json` → 在 GitHub Releases 建
`vNNN` 标签并上传 APK 与清单 → 把清单提交进本仓库。

## 游戏内"检查更新"读取的固定地址

```
https://github.com/<OWNER>/<REPO>/releases/latest/download/update.json
```

GitHub 会自动把 `releases/latest/download/<文件名>` 重定向到最新正式版的同名
附件，所以这个地址永远指向最新版，客户端无需改代码。

## 规则

1. `versionCode` 只能递增；脚本会拒绝发布不比现有清单新的版本。
2. APK 一律进 Releases 附件，**不要提交进 git 历史**（`.gitignore` 已排除）。
3. 游戏源代码不进入本仓库，本仓库只承担分发。
4. 发版前确认已在真机/模拟器完成一轮冒烟测试（启动、登录、签到、战斗一场）。
