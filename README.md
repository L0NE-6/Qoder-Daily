<div align="center">

# 🧭 Qoder Daily

**Qoder 中国版 / 国际版每日签到 · 设备授权登录 · 单文件青龙脚本 · 多账号 · Token 自动续期**

<img src="https://img.shields.io/github/v/release/L0NE-6/Qoder-Daily?style=flat-square&label=Release&color=2ea44f" />
<img src="https://img.shields.io/github/stars/L0NE-6/Qoder-Daily?style=flat-square&label=Stars&color=FFC75F" />
<img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/%E9%9D%92%E9%BE%99%E9%9D%A2%E6%9D%BF-%E5%8D%95%E6%96%87%E4%BB%B6%E8%BF%90%E8%A1%8C-4EAA25?style=flat-square" />
<img src="https://img.shields.io/badge/GitHub%20Actions-%E6%94%AF%E6%8C%81-2088FF?style=flat-square&logo=githubactions&logoColor=white" />
<img src="https://img.shields.io/badge/%E5%A4%9A%E8%B4%A6%E5%8F%B7-%E6%8D%A2%E8%A1%8C%E6%88%96%20%26%20%E5%88%86%E9%9A%94-8957E5?style=flat-square" />
<img src="https://img.shields.io/badge/License-MIT-F472B6?style=flat-square" />

</div>

---

## ✨ 这是什么

一个脚本完成 Qoder 中国版 / 国际版的每日签到：读取实时活动列表 → 领取 `CLAIM_BENEFIT` 活动 → 输出中文报告并推送。国际版（每天 100 Credits）只对带设备风控身份（UMID）的请求下发活动，脚本按「环境变量 → 组件 → 官方包提取」分层获取，缺身份时如实提示、不谎报已签。配套登录工具走官方设备授权，浏览器确认一次即可拿到 Token，不需要验证码、不需要抓包。

> 🎯 一句话：**配好 Token，剩下的交给它。**
>
> 📦 单文件自包含：不需要额外模块，青龙上传脚本、填好环境变量就能跑。
>
> ☁️ 除了青龙，也可以直接跑在 **GitHub Actions** 上，零服务器定时执行（见下文部署方式二）。

核心特性：

- ✅ **每日签到**：自动找可领活动并领取 credits，已领取识别为今日完成
- 🎁 **Pro 升级包**：`eligibility → claim` 自动领取一次性 +1800 积分；已领取不重复计数
- 🌍 **国际版签到**：每天 100 Credits，走 `QODER_GLOBAL_TOKENS`；需要 UMID 风控身份（组件 / 环境变量），活动窗口每天 10:00（UTC+8）开启，未开不落已签、后续轮次自动补领
- 🔐 **Token 自动续期**：refresh_token 轮换后自动落盘，长期无人值守
- 👥 **多账号**：环境变量换行或 `&` 分隔，逐账号容错
- 📢 **多渠道推送**：PushPlus / Bark / 企业微信 / 钉钉 / 青龙通知
- 🐧 **青龙 & Actions**：单文件运行，也支持 GitHub Actions 定时

## 📦 文件说明

| 文件 | 作用 |
|---|---|
| `qoder_login.py` | 设备授权登录，浏览器确认后输出 Token |
| `qoder_daily.py` | 每日签到（多账号、自动续期、推送） |

## ⬇️ 下载

不想用 git？直接到 **[Releases](https://github.com/L0NE-6/Qoder-Daily/releases)** 下载：

- 完整包 zip（脚本 + 登录工具 + README + Actions 工作流 + 收款码）
- 各脚本单文件（青龙只需要上传签到脚本）
- `SHA256SUMS.txt` 完整性校验

## 🚀 部署方式一：青龙面板（三步）

| 步骤 | 操作 |
| :---: | :--- |
| 1 | 安装依赖：`pip install -r requirements.txt`（或 `pip3 install requests`） |
| 2 | 把签到脚本上传到青龙「脚本管理」，或把仓库放进脚本目录 |
| 3 | 「环境变量」里添加 Token，新建定时任务（见下方 cron 示例） |

```cron
20 8 * * * python qoder_daily.py
```

## ☁️ 部署方式二：GitHub Actions（可选，默认手动触发）

1. Fork 本仓库（或直接使用本仓库，Secrets 只能配在你自己的仓库里）。
2. 打开 **Settings → Secrets and variables → Actions**，添加下表里的 Secrets。
3. 打开 **Actions** 标签页，选择 `Qoder Daily`，点 **Run workflow** 手动跑一次验证。
4. 默认只支持**手动触发**（上游仓库不跑定时，避免空跑）；fork 后想定时，把 `.github/workflows/daily.yml` 里 `schedule:` 两行取消注释（cron 用 UTC，北京时间减 8 小时），之后就会按该时间自动执行。

| Secret | 对应环境变量 | 必填 |
|---|---|---|
| `QODER_TOKENS` | QODER_TOKENS | 必填 |
| `QODER_GLOBAL_TOKENS` / `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 同名环境变量 | 有国际版账号时填 |
| `PUSHPLUS_TOKEN` / `BARK_URL` / `WECOM_WEBHOOK` / `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | 同名推送变量 | 可选 |

> 公开仓库的 Secrets 是加密的，日志里不会回显；脚本也不会把 Token 写进仓库文件。

### Actions 的轮换令牌状态

- `refresh_token` 轮换后，下一轮进程仍从原始环境变量 / Secret 启动。
  脚本同时保留原始凭据指纹到最新令牌的索引，配置无需每次手动改写。
- **私有仓库的默认分支**会在运行前恢复、运行后保存 `qoder_tokens.json` 和
  `qoder_machine_id` 到 Actions cache；后续任务异常时也会尝试保存已轮换的令牌。
  每次运行 / 重跑使用独立 cache key，并通过共同前缀恢复最新状态。
- **公开仓库不缓存这些凭据文件**。公开仓库默认分支缓存可能被 fork PR 的工作流读取，
  不能把 Secret 注入后的明文令牌直接放进去。需要跨运行自动续期时，请建立私有副本，
  或自行接入经过保护的持久化存储；公开 fork 当前仍需在失效后手动更新凭据。
- Cache 可能被清理或淘汰；丢失轮换状态且原刷新令牌已失效时，需要重新授权。
  状态文件已在 `.gitignore` 中排除，不要手动提交或上传为公开 artifact。

## 🔑 获取 Token

**方式 A（推荐）：设备授权登录工具**

```bash
python qoder_login.py                 # 中国版
python qoder_login.py --region global # 国际版（Token 填 QODER_GLOBAL_TOKENS）
```

在浏览器打开提示的授权页确认一次，工具会自动轮询并输出一行 `access_token|refresh_token`：中国版粘贴进 `QODER_TOKENS`，国际版粘贴进 `QODER_GLOBAL_TOKENS`（工具会直接给出目标变量名）。默认还会调用一次活动列表接口验证 Token。

**方式 B：浏览器抓包**

登录 Qoder 网页版后，在开发者工具里看任意请求的 `authorization: Bearer dt-…`，这是 access token；如果能同时拿到 `drt-…` 刷新串，用 `access|refresh` 一起填，就能自动续期。

## 🧩 环境变量（支持多账号）

> 多账号用 **换行** 或 **`&`** 分隔，两种可以混用。`|` 是单条账号内部的字段分隔符，备注里不要再写 `|`。

| 环境变量 | 单条格式 | 说明 |
|---|---|---|
| `QODER_TOKENS` | `access_token` / `access_token\|refresh_token` / `备注\|access_token\|refresh_token` | 中国版账号，多账号换行或 `&` |
| `QODER_GLOBAL_TOKENS` | 同上，可再加 `\|uid`（`备注\|access\|refresh\|uid`） | 国际版账号，请求走 `openapi.qoder.sh` |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 三件套 | 国际版设备风控身份（与组件二选一） |
| `QODER_UMID_PATH` / `QODER_UMID_NO_INSTALL` | `runtime-info` 路径 / `1` | 指定 UMID 组件；或禁止自动从官方包提取 |

## ⌨️ 命令行参数

| 参数 | 作用 |
|---|---|
| `--only 2` | 只跑第 2 个账号 |
| `--no-notify` | 关闭推送 |
| `--refresh-only` | 只刷新 Token 并保存 |

## 📊 运行效果示例

```text
[08:20:01] 👤 [1] 主号  token=dt-abc****wxyz
[08:20:03]    ✅ 获得 100 credits，30 天有效
[08:20:04] 账号1 主号: ✅ 获得 100 credits，30 天有效
[08:20:04] 🕐 2026-10-09 08:20
```

## 🗂️ 数据文件说明

| 文件 | 内容 | 是否提交 |
|---|---|---|
| `qoder_tokens.json` | 续期后轮换的新 Token | 已忽略 |
| `qoder_machine_id` | 登录工具生成的设备标识 | 已忽略 |

> 以上文件都包含账号凭据，已在 `.gitignore` 中排除，**不要手动提交**。

## ❓ 常见问题

- **Token 多久失效？** 配了 refresh_token 会自动续期；只有 access token 时过期需重新登录。
- **授权页打不开/超时？** 重新运行工具再确认一次；确认时请用要签到的那个账号。
- **国际版能签到吗？** 可以：国际版（每天 100 Credits）只对带设备风控身份（UMID）的请求下发活动。脚本按「环境变量三件套 → `QODER_UMID_PATH` → 本机客户端/qodercli → 官方包提取」获取身份；都没有时如实提示「未领取」，不会记成已签。活动窗口每天 10:00（UTC+8）开启。

## 📁 目录结构

```text
Qoder-Daily/
├── qoder_login.py
├── qoder_daily.py
├── assets/                     # 收款码
├── .github/workflows/daily.yml # GitHub Actions
├── CHANGELOG.md
├── LICENSE
├── README.md
└── requirements.txt
```

## 📦 版本与发布

- 每次更新单独发一个 Release：`v1.0.0` → `v1.0.1` …，历史版本保留可下载。
- 每个 Release 附带：完整包 zip + 各脚本单文件 + `SHA256SUMS.txt`。
- 下载页：<https://github.com/L0NE-6/Qoder-Daily/releases>

## 🔒 隐私说明

- 脚本**不含任何账号、手机号、Token 或设备信息**，全部由环境变量（或 GitHub Secrets）注入。
- 运行期生成的数据文件（见「数据文件说明」）都包含凭据，已被 `.gitignore` 排除。
- 请勿把 Token 写进脚本、提交到仓库或发到 Issue 里。

## ⚠️ 免责声明

本项目仅供**学习与个人自动化**使用。请遵守对应平台的服务条款，使用风险自负。

## ☕ 支持与投喂

脚本是**完全免费、无广告、无功能限制**的，仓库与发布包也不含你的任何数据。
如果它确实帮你省了时间，欢迎请我喝杯咖啡 —— **纯自愿，不影响任何功能**。

<p align="center">
  <img src="assets/donate-wechat.png" width="240" alt="微信赞赏码" />
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/donate-alipay.jpg" width="240" alt="支付宝收款码" />
</p>
<p align="center"><sub>💚 微信支付（左） &nbsp;|&nbsp; 💙 支付宝（右）</sub></p>

> 💡 **不花钱也能帮上忙**：点个 ⭐ Star、提一个带日志的 Issue、发一个 Pull Request，或者把脚本分享给需要的朋友。

## 💬 反馈与贡献

- 提交 [Issue](https://github.com/L0NE-6/Qoder-Daily/issues)：报 bug、提需求
- 发起 [Pull Request](https://github.com/L0NE-6/Qoder-Daily/pulls)：直接贡献代码

> 提 Issue 时附上**运行日志**和**复现步骤**，定位会快很多。

---

<div align="center">
  <sub>🧭 如果这个脚本帮到你，点个 <b>Star</b> 支持一下，或者到 <a href="#-支持与投喂">支持与投喂</a> 请我喝杯咖啡 ✨</sub>
</div>
