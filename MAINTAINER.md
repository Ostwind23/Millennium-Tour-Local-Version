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

## 热更新通道（resources/content 级，免重装）

每次正式发版后 `publish_release.py` 会自动跟进刷新热更新基线。日常的
资源/配置/内容小修（不动 Python 后端和 dex 层的改动）可以**不发新 APK**，
直接热更新推送：

```bash
cd _build && python build_apk_final.py /tmp/qnzl-next.apk   # 只需打包，不用签名安装
python tools/publish_hot.py --hot-only --apk /tmp/qnzl-next.apk
```

机制（与 git 同款思路）：`files.json` 描述全部 1237 个受管文件的最新目标
哈希，提交到 main 分支即发布；改动的文件以 `f_<sha256>` 为名上传到固定的
`hot-pool` Release（内容寻址，天然去重）。玩家端每次启动时比对本地文件
哈希——不一致的下载替换、缺少的补齐、清单移除的删除；全部校验通过才切换，
断网或下载失败自动回退到上一版，不影响游玩。

客户端读取地址（勿改，已硬编码进游戏）：

- 清单：`https://raw.githubusercontent.com/Ostwind23/qnzl-local-dist/main/files.json`
- 文件池：`https://api.github.com/repos/Ostwind23/qnzl-local-dist/releases/tags/hot-pool`

注意：Python 后端模块和 dex 补丁层的改动**不能**走热更新，必须发新 APK。
