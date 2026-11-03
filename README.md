<div align="center">

<sub><strong>L0NE-6 · DAILY SIGNAL</strong></sub>

# 🧭 Qoder Daily

**Qoder 中国版 / 国际版每日奖励领取工具，支持设备授权登录、双地区 UMID、多账号与 Token 轮换恢复。**

[简体中文](README.md) · [English](docs/README.en.md) · [繁體中文](docs/README.zh-Hant.md) · [日本語](docs/README.ja.md) · [한국어](docs/README.ko.md) · [Português (BR)](docs/README.pt-BR.md)

<img src="https://img.shields.io/github/v/release/L0NE-6/Qoder-Daily?style=for-the-badge&label=Release&color=2ea44f&logo=github" />
<img src="https://img.shields.io/github/stars/L0NE-6/Qoder-Daily?style=for-the-badge&label=Stars&color=FFC75F&logo=github" />
<img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/%E9%9D%92%E9%BE%99-Qinglong-4EAA25?style=for-the-badge" />
<img src="https://img.shields.io/badge/GitHub%20Actions-Supported-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" />
<img src="https://img.shields.io/badge/License-MIT-F472B6?style=for-the-badge" />
<a href="https://github.com/L0NE-6/Qoder-Daily/releases"><img src="https://img.shields.io/badge/%E2%AC%87%20Download-Releases-2ea44f?style=for-the-badge&logo=github" /></a>

[✨ 30 秒速览](#-30-秒速览) · [🚀 青龙面板](#-青龙面板) · [☁️ GitHub Actions](#-github-actions) · [🔑 获取 Token](#-获取-token) · [🔧 环境变量](#-环境变量) · [❓ 常见问题](#-常见问题) · [🚫 使用边界](#usage-policy) · [✦ 星轨](#-星轨-star-trail)

</div>

---

<a id="usage-policy"></a>
## 🚫 使用边界与转载声明

> [!IMPORTANT]
> **官方版本永久免费。** 未经作者书面许可，禁止付费包装、搬运引流、冒充作者，或使用作者身份与二维码制造官方授权假象。违规内容可能被要求下架；作者可暂停更新、归档或删除仓库及相关 Release。

本项目仓库、脚本、部署说明和 Release 下载始终免费公开。未经作者明确书面许可，禁止将本项目包装为付费资源、内部版、独家版、会员权益、收费课程、付费部署或包更新服务；禁止搬运到其他账号、群组、频道、网盘、电商或付费平台进行涨粉、截流、倒卖和引流；禁止删除作者与版权信息后冒充原创；禁止使用作者昵称、头像、二维码和项目名称制造官方授权假象。

> 如需商业合作、品牌授权、联合分发或使用作者名义提供付费服务，请先取得作者明确书面授权。完整规则、收款码防诈骗说明和违规处理方式见 **[NOTICE.md](NOTICE.md)**。

> 官方仓库和 Release 始终免费。第三方以“下载费 / 激活费 / 内部版 / 代部署 / 会员门槛”等名义收费，均与作者无关，请停止付款并保留证据。

> 对上述违规行为，作者有权要求立即停止传播、删除内容并下架相关商品或页面；并可视情况暂停更新、归档或删除本仓库及相关 Release、向平台投诉或采取进一步必要措施。

---

## ✨ 30 秒速览

| 维度 | 说明 |
| :--- | :--- |
| **用途** | 领取 Qoder 中国版 / 国际版当前下发的每日 Credits 活动，并处理可发现的 Pro 升级活动。 |
| **输入** | 中国版 `QODER_TOKENS`、国际版 `QODER_GLOBAL_TOKENS`，以及对应地区的官方设备身份。 |
| **输出** | 分账号签到结果、Credits / 额度变化、Token 续期状态、Pro 活动结果与可选多渠道推送。 |
| **部署** | 青龙面板、GitHub Actions、Windows / Linux 本地运行。 |
| **依赖** | Python 3.8+ 与 `requests`。 |
| **成功判据** | 活动实际下发并完成 claim 后才按成功报告；缺设备身份、窗口未开或没有活动行时保留中性状态，不虚报已签。 |

## ✨ 核心能力

- **双地区签到**：中国版请求 Qoder CN，国际版请求 `openapi.qoder.sh`。
- **地区隔离设备身份**：中国版读取 Qoder CN / `qoderclicn`，国际版读取 Qoder / `qodercli`。
- **开窗补拉**：默认在北京时间 10:00-11:00 内每 10 分钟检查，最多 6 次。
- **Token 轮换恢复**：refresh_token 轮换后写入本地状态；Actions 可再用 `QODER_CACHE_KEY` 加密缓存。
- **额度类 403 分流**：区分额度耗尽、每日计费上限和真实登录失效。
- **Pro 活动谨慎领取**：只在 campaigns 实际发现或只读 reward 核对面值后才 claim。
- **多账号与推送**：支持中国版 / 国际版混合账号，以及 PushPlus、Bark、企业微信、钉钉和青龙通知。

## 🧩 工作流程

```text
读取 Token
  → 按地区选择官方端点与 UMID 身份
  → 获取 campaigns
  → 筛选 CLAIM_BENEFIT
  → claim
  → 读取额度 / 使用量复核
  → 轮换并保存 refresh_token
  → 输出中文报告
```

中国版和国际版的活动窗口、设备身份与 API 域名彼此独立。脚本不会拿中国版组件去跑国际版账号，也不会在缺少对应身份时编造签到成功。

## 🔑 获取 Token

### 方式一：设备授权登录工具

```bash
python qoder_login.py
python qoder_login.py --region global
```

浏览器会打开官方授权页。确认与目标账号一致的授权后，工具轮询结果并输出：

```text
access_token|refresh_token
```

中国版写入 `QODER_TOKENS`，国际版写入 `QODER_GLOBAL_TOKENS`。工具默认还会调用活动列表接口验证 Token。

### 方式二：浏览器网络请求

登录 Qoder 网页版后，在开发者工具中查看请求的 `authorization: Bearer ...`：

- `dt-...` 是 access token。
- 如能同时取得 `drt-...` refresh token，使用 `access|refresh` 填写。

只有 access token 也能运行，但过期后需要重新授权；配置 refresh token 才能自动续期。

## 🚀 青龙面板

1. 安装依赖：

   ```bash
   pip3 install requests
   ```

2. 将 `qoder_daily.py` 上传到青龙脚本目录。
3. 添加中国版 / 国际版 Token 环境变量。
4. 新建定时任务：

   ```bash
   task qoder_daily.py
   ```

建议 cron：

```cron
5 10 * * *
```

青龙使用面板本地时间。活动每日 10:00 开窗，10:05 首次检查可以避开边界；暂未下发时脚本会在窗口内继续补拉。

## 🚀 GitHub Actions

仓库内置 [`.github/workflows/daily.yml`](.github/workflows/daily.yml)，当前默认只保留 `workflow_dispatch` 手动触发。

| Secret | 必填 | 说明 |
| :--- | :---: | :--- |
| `QODER_TOKENS` | 中国版必填 | 中国版账号。 |
| `QODER_GLOBAL_TOKENS` | 国际版必填 | 国际版账号。 |
| `QODER_CACHE_KEY` | 建议必填 | 加密 Actions 中 `qoder_tokens.json` 与 `qoder_machine_id` 的随机长字符串。 |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 条件必填 | 没有本地 runtime-info 时提供设备身份三件套。 |
| `QODERCN_RUNTIME_INFO` / `QODER_RUNTIME_INFO` / `QODER_UMID_PATH` | ➖ | 分别覆盖中国版 / 国际版 / 通用组件路径。 |
| `QODER_UMID_NO_INSTALL` | ➖ | 设为 `1` 时禁止从官方包自动提取身份。 |
| `PUSHPLUS_TOKEN` / `BARK_URL` / `WECOM_WEBHOOK` / `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | ➖ | 可选推送。 |

进入 **Actions → Qoder Daily → Run workflow** 手动验证。需要云端定时时，取消工作流中的两行注释：

```yaml
schedule:
  - cron: "5 2 * * *"
```

该 cron 使用 UTC，对应北京时间每天 10:05。Fork 后若 scheduled workflow 默认停用，需要在 Actions 页面启用；GitHub 的 schedule 只从默认分支运行。

### Actions 中的重试覆盖

脚本默认值为：

```text
QODER_WINDOW_RETRY=1
QODER_WINDOW_RETRY_MAX=6
QODER_WINDOW_RETRY_GAP=600
```

当前 workflow 显式覆盖为：

```yaml
QODER_WINDOW_RETRY: "1"
QODER_WINDOW_RETRY_MAX: "16"
QODER_WINDOW_RETRY_GAP: "90"
```

两者都是仓库现状。修改脚本默认值不会自动改变 workflow 的环境覆盖。

### 加密 Token 状态

- workflow 会把 `qoder_tokens.json` 与 `qoder_machine_id` 打包，用 `QODER_CACHE_KEY` 执行 AES-256-CBC / PBKDF2 加密后写入 Actions cache。
- 每轮并发的 Action 使用独立 cache key，并通过共同前缀恢复最新状态。
- 没有 `QODER_CACHE_KEY` 时，workflow 会告警并跳过持久化；本轮仍可签到，但轮换后的 refresh_token 可能无法在下一轮恢复。
- Cache 可能被淘汰或清理；状态丢失且旧 refresh_token 已失效时需要重新授权。

## 🔧 环境变量

### 账号 Token

| 变量 | 单条格式 | 说明 |
| :--- | :--- | :--- |
| `QODER_TOKENS` | `access` / `access\|refresh` / `备注\|access\|refresh` | 中国版账号，换行或 `&` 分隔。 |
| `QODER_GLOBAL_TOKENS` | 同上，可追加 `\|uid` | 国际版账号，格式 `备注\|access\|refresh\|uid`。 |

`|` 用于条目内部字段，备注里不要再写 `|`。

### 设备身份

| 变量 | 说明 |
| :--- | :--- |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 手动提供完整设备身份三件套。 |
| `QODERCN_RUNTIME_INFO` | 中国版 `runtime-info` 组件路径。 |
| `QODER_RUNTIME_INFO` | 国际版 `runtime-info` 组件路径。 |
| `QODER_UMID_PATH` | 通用组件路径，在地区专用变量后作为覆盖。 |
| `QODER_UMID_NO_INSTALL` | 设为 `1` 时禁止自动从官方包提取。 |

### 重试、缓存与通知

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `QODER_WINDOW_RETRY` | `1` | 10:00-11:00 CST 内是否补拉。 |
| `QODER_WINDOW_RETRY_MAX` | `6` | 最多尝试次数，脚本内部上限为 6。 |
| `QODER_WINDOW_RETRY_GAP` | `600` | 两次尝试间隔秒数。 |
| `QODER_CACHE_KEY` | 无 | 仅 workflow 使用，加密 Actions token 状态。 |
| `PUSHPLUS_TOKEN` | 无 | PushPlus。 |
| `BARK_URL` | 无 | Bark。 |
| `WECOM_WEBHOOK` | 无 | 企业微信群机器人。 |
| `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | 无 | 钉钉 webhook 与加签密钥。 |

> [!NOTE]
> 脚本会把 `QODER_WINDOW_RETRY_MAX` 限制在 `1..6`。workflow 中写 `16`，最终仍受脚本的 6 次上限约束。

## ⌨️ 命令行参数

| 参数 | 作用 |
| :--- | :--- |
| （无） | 运行所有中国版 / 国际版账号。 |
| `--only N` | 只运行合并列表中的第 N 个账号。 |
| `--no-notify` | 关闭本轮推送。 |
| `--refresh-only` | 只刷新 Token 并保存状态。 |

`--only` 按「中国版账号在前、国际版账号在后」的合并顺序计数。

## 📊 签到与额度语义

- `CLAIM_BENEFIT` 活动实际下发后才能领取。
- 中国版完整设备头返回空列表时，只在成功响应明确为空或 `showCampaign:false` 的情况下，用四件套最小鉴权头复取一次。
- 国际版不启用该最小头复取。
- 领取成功后按上游活动数据报告 Credits；实际额度变化可从 usage / quota 路径核对时再报告增量。
- Pro 活动只在 campaigns 中真实出现或 `/reward` 只读核对面值后才尝试，不承诺固定 `+1800`。
- 窗口未开、身份缺失或没有活动行时不写入“已签”状态，后续轮次可继续补拉。

## 🚦 HTTP 与业务码分流

| 状态 | 处理 |
| :--- | :--- |
| 业务码 `112` 或响应含 `pricingUrl` | 按额度耗尽处理，冷却约 30 分钟，不触发 Token 续期。 |
| 业务码 `110` / `Billing daily count exceeded` | 按每日计费上限处理，冷却到本地零点，封顶 6 小时。 |
| 非额度类 401 / 403、业务码 `105` / `10019901001` | 尝试用 refresh_token 续期一次并重试。 |
| 普通 429 / 5xx | 按上游错误报告，不伪装成成功。 |

## 🗂️ 数据文件与状态

| 文件 / 目录 | 内容 | 是否提交 |
| :--- | :--- | :---: |
| `qoder_tokens.json` | 轮换后的 Token 状态 | ❌ 已忽略 |
| `qoder_machine_id` | 登录工具生成的设备标识 | ❌ 已忽略 |
| `.qoder-cache/` | Actions 加密状态 | ❌ 已忽略 |
| `qoder_umid/` | 自动提取的 UMID 组件 | ❌ 已忽略 |
| `*_result.json` | 运行结果 | ❌ 已忽略 |

本地运行会直接使用脚本目录状态；青龙需要保证脚本目录可写。Actions 则通过加密 cache 跨运行保存状态。

## 🧪 测试与验证

- 仓库包含 `tests/test_token_store.py` 与 `tests/test_campaign_core.py`。
- 测试覆盖 Token 轮换索引、请求头地区隔离、活动行识别、额度类 403、业务码续期与 campaign 处理。
- 工作流 `tests.yml` 在 push / pull_request 时执行 unittest 与 `py_compile`。
- README 不把单元测试通过等同于真实账号一定完成领取；线上仍受活动窗口、设备身份和上游策略影响。

## 🔒 隐私说明

- 仓库不包含真实 Token、UID、设备标识、手机号或 Cookie。
- 凭据来自环境变量或 GitHub Secrets。
- `qoder_tokens.json`、`qoder_machine_id`、解密后的 Actions cache 都属于敏感数据。
- 不要提交 Token 文件、上传未加密 artifact、把 Secret 写进 Issue，或在日志中粘贴完整授权头。

## ❓ 常见问题

<details>
<summary><b>Token 多久失效</b></summary>

配置 refresh_token 后，遇到普通会话失效会尝试自动续期。只配置 access token 时，过期后需要重新运行 `qoder_login.py`。
</details>

<details>
<summary><b>授权页打不开或轮询超时</b></summary>

重新运行登录工具并确认授权账号正确。中国版使用默认命令，国际版加 `--region global`。
</details>

<details>
<summary><b>为什么中国版和国际版不能共用 UMID</b></summary>

两个地区要求不同的官方客户端身份。中国版读取 Qoder CN / `qoderclicn`，国际版读取 Qoder / `qodercli`；脚本会隔离客户端、CLI 缓存与提取目录。
</details>

<details>
<summary><b>HTTP 403 是否一定是登录失效</b></summary>

不是。`112` / `pricingUrl` 与 `110` 分别代表额度耗尽和每日计费上限。只有非额度类 401 / 403 或 `105` / `10019901001` 才进入续期路径。
</details>

<details>
<summary><b>Actions 恢复不到最新 Token</b></summary>

检查 `QODER_CACHE_KEY` 是否配置且跨运行保持一致，cache 是否被清理，以及同一前缀下是否有可恢复状态。没有 cache 时，原始 Secret 中的旧 refresh_token 可能已经失效。
</details>

<details>
<summary><b>Pro 升级是否固定加 1800 Credits</b></summary>

官方已不再常规投放。脚本只处理真实发现并核对面值的活动，不保证固定额度，也不会请求已知不存在的端点。
</details>

## 📦 版本与发布

- 当前发布版：`v1.0.13`（2026-11-04，文档发行版；脚本逻辑仍为 `v1.0.12`）。
- 历史版本保留在 [Releases](https://github.com/L0NE-6/Qoder-Daily/releases)。
- 每个 Release 附带完整包、单文件脚本与 `SHA256SUMS.txt`。
- 更新记录见 [CHANGELOG.md](CHANGELOG.md)。

## ⚠️ 免责声明

本项目用于个人学习与自动化实践。请遵守 Qoder 及相关服务条款，并自行承担账号与自动化使用风险。

## ☕ 支持与反馈

遇到 Token 轮换、地区身份或活动窗口问题，欢迎提交 [Issue](https://github.com/L0NE-6/Qoder-Daily/issues)。请附上脱敏日志、复现步骤、运行环境、所在地区与时间窗口；代码改进可通过 [Pull Request](https://github.com/L0NE-6/Qoder-Daily/pulls) 提交。

项目免费开源。如果它节省了你的时间，可以自愿扫码支持；Star、真实运行反馈和测试补充同样重要。

<p align="center">
  <img src="assets/donate-wechat.png" width="260" alt="微信赞赏码" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/donate-alipay.jpg" width="260" alt="支付宝赞赏码" />
</p>
<p align="center"><sub>💚 微信支付（左） &nbsp;|&nbsp; 💙 支付宝（右，支持信用卡 / 花呗）</sub></p>

> ⚠️ 收款码仅用于向作者自愿赞赏。任何第三方以代下载、代部署、内部资源或会员群为由收费，均与作者无关，请停止付款并保留证据。

---

## ✦ 星轨 Star Trail

> 每颗 Star 都是一枚方位信号，标记 Qoder Daily 在双地区、长周期自动签到与可恢复状态之间的航迹。

<a href="https://star-history.com/#L0NE-6/Qoder-Daily&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=L0NE-6/Qoder-Daily&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=L0NE-6/Qoder-Daily&type=Date&theme=light" />
    <img alt="Qoder Daily Star Trail" src="https://api.star-history.com/svg?repos=L0NE-6/Qoder-Daily&type=Date&theme=light" />
  </picture>
</a>

---

<div align="center">
  <a href="https://github.com/L0NE-6/Qoder-Daily/releases">Releases</a> ·
  <a href="https://github.com/L0NE-6/Qoder-Daily/issues">Issues</a> ·
  <a href="https://github.com/L0NE-6/Qoder-Daily">Star</a>
  <br />
  <sub>L0NE-6 · DAILY SIGNAL · 双地区有界，Token 有续，结果有回读</sub>
</div>
