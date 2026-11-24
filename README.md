<div align="center">

<sub><strong>L0NE-6 · DAILY SIGNAL</strong></sub>

# 🧭 Qoder Daily

**Qoder 中国版 / 国际版每日奖励领取工具，支持设备授权登录、双地区 UMID、多账号与 Token 轮换恢复**

> 当前版本：**v1.0.24**（2026-11-17） · 认证方式：Access Token + Refresh Token + 地区设备身份

**[简体中文](README.md)** · [English](docs/README.en.md) · [繁體中文](docs/README.zh-Hant.md) · [日本語](docs/README.ja.md) · [한국어](docs/README.ko.md) · [Português (BR)](docs/README.pt-BR.md)

双地区 · UMID · 设备授权 · Token 轮换 · 多账号 · 青龙 · Actions

<img src="https://img.shields.io/badge/Version-v1.0.24-2ea44f?style=for-the-badge&logo=github" alt="Version v1.0.24" />
<img src="https://img.shields.io/github/stars/L0NE-6/Qoder-Daily?style=for-the-badge&label=Stars&color=FFC75F&logo=github" alt="Stars" />
<img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+" />
<img src="https://img.shields.io/badge/Qinglong-ready-4EAA25?style=for-the-badge" alt="Qinglong" />
<img src="https://img.shields.io/badge/GitHub%20Actions-supported-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions" />

[边界](#policy) · [速览](#overview) · [协议](#protocol) · [凭据](#credentials) · [快速开始](#quickstart) · [青龙](#qinglong) · [Actions](#actions) · [CLI](#cli) · [结果码](#result-codes) · [成功判据](#success) · [测试](#tests) · [目录](#layout) · [版本](#release) · [赞赏](#donate) · [反馈](#feedback)

</div>

---

<a id="policy"></a>
## 🚫 使用边界

### 🚫 使用边界与转载声明

> [!IMPORTANT]
> **官方版本永久免费。** 未经作者书面许可，禁止付费包装、搬运引流、冒充作者，或使用作者身份与二维码制造官方授权假象。违规内容可能被要求下架；作者可暂停更新、归档或删除仓库及相关 Release。

本项目仓库、脚本、部署说明和 Release 下载始终免费公开。未经作者明确书面许可，禁止将本项目包装为付费资源、内部版、独家版、会员权益、收费课程、付费部署或包更新服务；禁止搬运到其他账号、群组、频道、网盘、电商或付费平台进行涨粉、截流、倒卖和引流；禁止删除作者与版权信息后冒充原创；禁止使用作者昵称、头像、二维码和项目名称制造官方授权假象。

> 如需商业合作、品牌授权、联合分发或使用作者名义提供付费服务，请先取得作者明确书面授权。完整规则、收款码防诈骗说明和违规处理方式见 **[NOTICE.md](NOTICE.md)**。

> 官方仓库和 Release 始终免费。第三方以“下载费 / 激活费 / 内部版 / 代部署 / 会员门槛”等名义收费，均与作者无关，请停止付款并保留证据。

> 对上述违规行为，作者有权要求立即停止传播、删除内容并下架相关商品或页面；并可视情况暂停更新、归档或删除本仓库及相关 Release、向平台投诉或采取进一步必要措施。

---

---

<a id="overview"></a>
## ✨ 30 秒速览

### ✨ 30 秒速览

| 维度 | 说明 |
| :--- | :--- |
| **用途** | 领取 Qoder 中国版 / 国际版当前下发的每日 Credits 活动，并处理可发现的 Pro 升级活动。 |
| **输入** | 中国版 `QODER_TOKENS`、国际版 `QODER_GLOBAL_TOKENS`，以及对应地区的官方设备身份。 |
| **输出** | 分账号签到结果、Credits / 额度变化、Token 续期状态、Pro 活动结果与可选多渠道推送。 |
| **部署** | 青龙面板、GitHub Actions、Windows / Linux 本地运行。 |
| **依赖** | Python 3.8+ 与 `requests`。 |
| **成功判据** | 活动实际下发并完成 claim 后才按成功报告；缺设备身份、窗口未开或没有活动行时保留中性状态，不虚报已签。 |

---

<a id="what"></a>
## 🧭 这是什么

### ✨ 核心能力

- **双地区签到**：中国版请求 Qoder CN，国际版请求 `openapi.qoder.sh`。
- **地区隔离设备身份**：中国版读取 Qoder CN / `qoderclicn`，国际版读取 Qoder / `qodercli`；客户端组件使用环境 `3`，CLI / 下载组件使用环境 `4`。
- **国际版 UID 两段拉取**：先无风控头读取活动列表 UID，再生成对应 UMID 身份并二次拉取。
- **每日活动语义分类**：按 Credits、标题和模型作用域识别签到，排除 Sonus、SOTA 与限定模型权益。
- **开窗补拉**：默认在北京时间 10:00-11:00 内每 10 分钟检查，最多 6 次。
- **Token 轮换恢复**：refresh_token 轮换后写入本地状态；Actions 可再用 `QODER_CACHE_KEY` 加密缓存。
- **额度类 403 分流**：区分额度耗尽、每日计费上限和真实登录失效。
- **Pro 活动谨慎领取**：只在 campaigns 实际发现或只读 reward 核对面值后才 claim。
- **claim 地区差异**：国际版使用完整设备风控头 + JSON body；中国版沿用最小鉴权头 + 空 body，避免触发 503。
- **多账号与推送**：支持中国版 / 国际版混合账号，以及 PushPlus、Bark、企业微信、钉钉和青龙通知；同一设备身份下每日只允许一个账号领取，其余账号按 blocked 报告。

---

<a id="protocol"></a>
## 🔁 协议与回读

### 活动领取链

```text
GET  /sash/api/v1/me/campaigns
GET  /sash/api/v1/me/campaigns/{campaignId}/reward
POST /sash/api/v1/me/campaigns/{campaignId}/claim
GET  /api/v2/quota/usage
```

中国版基址为 `https://openapi.qoder.com.cn`，国际版基址为 `https://openapi.qoder.sh`。两个区域使用独立设备身份。

### 回读

脚本识别每日 Credits 活动后领取，再读取额度与使用量。`replayed`、`BLOCKED`、额度耗尽与真实登录失效会分开报告。

### 🧩 工作流程

```text
读取 Token
  → 按地区选择官方端点与 UMID 身份
  → 获取 campaigns
  → 识别每日 CLAIM_BENEFIT / CREDITS 活动
  → claim
  → 读取额度 / 使用量复核
  → 轮换并保存 refresh_token
  → 输出中文报告
```

中国版和国际版的活动窗口、设备身份与 API 域名彼此独立。脚本不会拿中国版组件去跑国际版账号，也不会在缺少对应身份时编造签到成功。

---

<a id="credentials"></a>
## 🔑 凭据与账号

| 变量 | 必需 | 说明 |
| :--- | :---: | :--- |
| `QODER_TOKENS` | 中国版 | `备注|access|refresh` 多账号 |
| `QODER_GLOBAL_TOKENS` | 国际版 | `备注|access|refresh|uid` 多账号 |
| `QODER_MACHINE_*` / `QODER_RUNTIME_INFO` / `QODER_UMID_PATH` | 身份二选一 | 官方设备身份来源 |
| `QODER_PROXY` | 否 | 登录工具与运行代理 |

Token 轮换后会写入 `qoder_tokens.json`；Actions 使用加密缓存持久化状态。

### 🔑 获取 Token

#### 方式一：设备授权登录工具

```bash
python qoder_login.py
python qoder_login.py --region global
```

浏览器会打开官方授权页。确认与目标账号一致的授权后，工具轮询结果并输出：

```text
access_token|refresh_token
```

中国版写入 `QODER_TOKENS`，国际版写入 `QODER_GLOBAL_TOKENS`。工具默认还会调用活动列表接口验证 Token。

#### 方式二：浏览器网络请求

登录 Qoder 网页版后，在开发者工具中查看请求的 `authorization: Bearer ...`：

- `dt-...` 是 access token。
- 如能同时取得 `drt-...` refresh token，使用 `access|refresh` 填写。

只有 access token 也能运行，但过期后需要重新授权；配置 refresh token 才能自动续期。

---

<a id="quickstart"></a>
## 🚀 快速开始

### ❓ 常见问题

<details>
<summary><b>Token 多久失效</b></summary>

配置 refresh_token 后，遇到普通会话失效会尝试自动续期。只配置 access token 时，过期后需要重新运行 `qoder_login.py`。
</details>

<details>
<summary><b>授权页打不开、轮询超时或连接被重置</b></summary>

重新运行登录工具并确认授权账号正确。中国版使用默认命令，国际版加 `--region global`。

如果日志出现 `ConnectionResetError(10054)` 或“远程主机强迫关闭了一个现有的连接”，通常是本机到 `qoder.com` / `openapi.qoder.sh` 的网络链路被重置。`v1.0.24` 会读取系统与环境代理，也可以显式设置 `QODER_PROXY`：

```powershell
$env:QODER_PROXY="http://127.0.0.1:7890"
python qoder_login.py --region global
```

连续 3 次网络失败后工具会停止轮询并返回非零，不再等到 300 秒超时。
</details>

<details>
<summary><b>为什么中国版和国际版不能共用 UMID</b></summary>

两个地区要求不同的官方客户端身份。中国版读取 Qoder CN / `qoderclicn`，国际版读取 Qoder / `qodercli`；脚本会隔离客户端、CLI 缓存与提取目录。
</details>

<details>
<summary><b>同一台电脑上多个账号，为什么只有一个能领</b></summary>

服务端按设备身份限额：同一台机器上的账号共用 `qoder_machine_id`、UMID 组件生成的 `machineCode` 与主机名，当天第一个账号领取后，其他账号的 claim 会返回 `200 + status=BLOCKED`、`failureCode=SAME_PERSON_ALREADY_CLAIMED`，每日活动行也可能被隐藏。

要分别领取，需要让账号使用不同的设备身份：换一台电脑，或在手机客户端领取另一个账号；也可以使用该独立工作流，让账号2 在单独的 GitHub Actions runner 上运行。账号2 工作流固定使用 `qoder-account2-actions` 主机名，账号1 不设置该专用值。不建议在脚本里伪造或轮换设备标识来绕过限制。
</details>

<details>
<summary><b>HTTP 403 是否一定是登录失效</b></summary>

不是。`112` / `pricingUrl` 与 `110` 分别代表额度耗尽和每日计费上限。只有非额度类 401 / 403 或 `105` / `10019901001` 才进入续期路径。
</details>

<details>
<summary><b>Actions 恢复不到最新 Token</b></summary>

检查 `QODER_CACHE_KEY` 是否配置且跨运行保持一致，cache 是否被清理，以及同一前缀下是否有可恢复状态。没有 cache 时，原始 Secret 中的旧 refresh_token 可能已经失效；如果服务端已经按新设备身份拒绝旧 RT，请用 `qoder_login.py` 重新登录并更新 `QODER_TOKENS`。
</details>

<details>
<summary><b>Pro 升级是否固定加 1800 Credits</b></summary>

官方已不再常规投放。脚本只处理真实发现并核对面值的活动，不保证固定额度，也不会请求已知不存在的端点。
</details>

---

<a id="qinglong"></a>
## 🐧 青龙面板

### 🚀 青龙面板

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

---

<a id="actions"></a>
## ☁️ GitHub Actions

### 🚀 GitHub Actions

仓库内置 [`.github/workflows/daily.yml`](.github/workflows/daily.yml)，当前默认只保留 `workflow_dispatch` 手动触发。

| Secret | 必填 | 说明 |
| :--- | :---: | :--- |
| `QODER_TOKENS` | 中国版必填 | 中国版账号。 |
| `QODER_GLOBAL_TOKENS` | 国际版必填 | 国际版账号。 |
| `QODER_CACHE_KEY` | Actions 必填 | 加密 Actions 中 `qoder_tokens.json` 与 `qoder_machine_id` 的随机长字符串；未配置时 workflow 会直接失败，不运行账号。 |
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

#### 多账号：账号2 用独立工作流

同一台机器上多个账号只能领一个，最省事的隔离方式是让账号2 跑在独立的云端 runner 上。仓库内置 [`.github/workflows/account2.yml`](.github/workflows/account2.yml)：

| 项目 | 说明 |
| :--- | :--- |
| Secret | `QODER_GLOBAL_TOKENS_2` 存账号2 的 `备注\|dt-...\|drt-...`；`QODER_CACHE_KEY` 可与其他工作流复用。 |
| 缓存 | 独立前缀 `qoder-account2-state-v2-`，持久化账号2 自己的 `qoder_machine_id` 与轮换 Token。 |
| 主机名 | 工作流固定 `HOSTNAME=qoder-account2-actions`，并设置 `QODER_MACHINE_HOSTNAME` 明确覆盖；账号1 不使用该专用值。 |
| 运行 | `python qoder_daily.py --only 1`（该工作流里只有账号2 一个账号）。 |
| 定时 | 默认启用，每天北京时间 10:05；也可在 Actions 页手动 Run workflow。 |

工作流刻意不注入 `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE`，也不注入 `QODER_RUNTIME_INFO` / `QODER_UMID_*`，否则会复用账号1 的设备身份。首次运行会生成账号2 自己的 `qoder_machine_id`，后续由独立 cache 恢复；主机名固定为 `qoder-account2-actions`。官方 UMID 生成的 `machineToken` / `machineCode` / `machineType` 仍由组件按账号与运行环境产生，可能随服务端策略轮换，不能把 cache 理解为整套设备指纹永久不变。

#### Actions 中的重试覆盖

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

#### 加密 Token 状态

- workflow 会把 `qoder_tokens.json` 与 `qoder_machine_id` 打包，用 `QODER_CACHE_KEY` 执行 AES-256-CBC / PBKDF2 加密后写入 Actions cache。
- 每轮并发的 Action 使用独立 cache key，并通过共同前缀恢复最新状态。
- 没有 `QODER_CACHE_KEY` 时，workflow 会在运行前直接失败，避免设备码漂移和账号风控；不会向账号发起签到请求。先在 Secrets 配好稳定密钥，再重跑。
- Cache 可能被淘汰或清理；状态丢失且旧 refresh_token 已失效时需要重新授权。

---

<a id="cli"></a>
## ⌨️ CLI 与环境变量

### 🔧 环境变量

#### 账号 Token

| 变量 | 单条格式 | 说明 |
| :--- | :--- | :--- |
| `QODER_TOKENS` | `access` / `access\|refresh` / `备注\|access\|refresh` | 中国版账号，换行或 `&` 分隔。 |
| `QODER_GLOBAL_TOKENS` | 同上，可追加 `\|uid` | 国际版账号，格式 `备注\|access\|refresh\|uid`；UID 可省略，脚本会从活动列表自动读取。 |

`|` 用于条目内部字段，备注里不要再写 `|`。

#### 设备身份

| 变量 | 说明 |
| :--- | :--- |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 手动提供完整设备身份三件套。 |
| `QODERCN_RUNTIME_INFO` | 中国版 `runtime-info` 组件路径。 |
| `QODER_RUNTIME_INFO` | 国际版 `runtime-info` 组件路径。 |
| `QODER_UMID_PATH` | 通用组件路径，在地区专用变量后作为覆盖。 |
| `QODER_UMID_NO_INSTALL` | 设为 `1` 时禁止自动从官方包提取。 |

#### 重试、缓存与通知

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `QODER_WINDOW_RETRY` | `1` | 10:00-11:00 CST 内是否补拉。 |
| `QODER_WINDOW_RETRY_MAX` | `6` | 最多尝试次数，脚本内部上限为 6。 |
| `QODER_WINDOW_RETRY_GAP` | `600` | 两次尝试间隔秒数。 |
| `QODER_CACHE_KEY` | 无 | 仅 workflow 使用，加密 Actions token 状态。 |
| `QODER_PROXY` | 系统 / 环境代理 | 仅 `qoder_login.py` 使用；显式指定 `http://` / `https://` 代理，覆盖系统或环境代理。 |
| `PUSHPLUS_TOKEN` | 无 | PushPlus。 |
| `BARK_URL` | 无 | Bark。 |
| `WECOM_WEBHOOK` | 无 | 企业微信群机器人。 |
| `DINGTALK_WEBHOOK` / `DINGTALK_SECRET` | 无 | 钉钉 webhook 与加签密钥。 |

> [!NOTE]
> 脚本会把 `QODER_WINDOW_RETRY_MAX` 限制在 `1..6`。workflow 中写 `16`，最终仍受脚本的 6 次上限约束。
### ⌨️ 命令行参数

| 参数 | 作用 |
| :--- | :--- |
| （无） | 运行所有中国版 / 国际版账号。 |
| `--only N` | 只运行合并列表中的第 N 个账号。 |
| `--no-notify` | 关闭本轮推送。 |
| `--refresh-only` | 只刷新 Token 并保存状态。 |

`--only` 按「中国版账号在前、国际版账号在后」的合并顺序计数。

---

<a id="result-codes"></a>
## 🚦 结果码

| 状态 | 含义 |
| :--- | :--- |
| claim 成功且额度可回读 | 成功 |
| `SAME_PERSON_ALREADY_CLAIMED` | 同设备身份下已有账号领取 |
| `REDEMPTION_CODE_OUT_OF_STOCK` | 当日名额已发完 |
| `CAMPAIGN_NOT_ACTIVE` | 活动未开放或已结束 |
| 401 / 登录失效 | 需要重新登录或恢复 refresh token |
| 429 / 5xx | 按失败或中性状态报告 |

### 🚦 HTTP 与业务码分流

| 状态 | 处理 |
| :--- | :--- |
| 业务码 `112` 或响应含 `pricingUrl` | 按额度耗尽处理，冷却约 30 分钟，不触发 Token 续期。 |
| 业务码 `110` / `Billing daily count exceeded` | 按每日计费上限处理，冷却到本地零点，封顶 6 小时。 |
| 非额度类 401 / 403、业务码 `105` / `10019901001` | 尝试用 refresh_token 续期一次并重试。 |
| claim 返回 `SAME_PERSON_ALREADY_CLAIMED`（HTTP 200，`status=BLOCKED`） | 同一设备身份下其他账号当天已领取；按 blocked 报告，不重试、不换账号重放。 |
| 普通 429 / 5xx | 按服务端错误报告，不伪装成成功。 |

---

<a id="success"></a>
## ✅ 成功判据

只有活动被识别为每日 Credits、claim 完成、且额度或使用量回读一致时才按成功报告。缺设备身份或活动未下发时保持中性。

### 📊 签到与额度语义

- 只有语义分类为每日签到的活动实际下发后才能领取；限定模型、Sonus、SOTA 与已结束活动不会自动领取。
- 中国版完整设备头返回空列表时，只在成功响应明确为空或 `showCampaign:false` 的情况下，用四件套最小鉴权头复取一次。
- 国际版不启用该最小头复取。
- 国际版 claim 需要完整设备风控头和 JSON body；最小鉴权头 + 空 body 会返回 `409 INTERNAL_ERROR`。
- 同一设备身份下当日已有其他账号领取时，claim 返回 `200 + status=BLOCKED`、`failureCode=SAME_PERSON_ALREADY_CLAIMED`，脚本报告“同一设备身份下的其他账号已领取”，不计为成功。
- 每日 claim 前后读取账户总剩余额度；只有确认额度增加才报告成功，回读不可用或未增加时显示“已受理待确认”。
- Pro 活动只在 campaigns 中真实出现或 `/reward` 只读核对面值后才尝试，不承诺固定 `+1800`。
- 窗口未开、身份缺失或没有活动行时不写入“已签”状态，后续轮次可继续补拉。

---

<a id="tests"></a>
## 🧪 测试

```powershell
$env:PYTHONUTF8 = "1"
python -m unittest discover -s tests -v
python -m py_compile qoder_daily.py qoder_login.py
```

测试覆盖活动识别、设备身份、Token 状态与网络分支；真实账号仍受活动窗口和同设备限领约束。

### 🧪 测试与验证

- 仓库包含 `tests/test_token_store.py` 与 `tests/test_campaign_core.py`。
- 测试覆盖 Token 轮换索引、请求头地区隔离、活动行识别、额度类 403、业务码续期与 campaign 处理。
- 工作流 `tests.yml` 在 push / pull_request 时执行 unittest 与 `py_compile`。
- README 不把单元测试通过等同于真实账号一定完成领取；线上仍受活动窗口、设备身份和服务端策略影响。

---

<a id="design"></a>
## 🧱 设计原则

- 中国版与国际版端点、令牌和设备身份硬隔离。
- 活动识别只接受每日 Credits 语义。
- refresh token 轮换后持久化并支持加密缓存恢复。
- 额度类 403 与真实登录失效分开归因。
- 单测通过不等于真实账号已到账。

---

<a id="privacy"></a>
## 🔒 隐私与安全

凭据、状态文件、日志与运行缓存都属于账号级数据。仓库和 Issue 中只保留脱敏片段。

### 🔒 隐私说明

- 仓库不包含真实 Token、UID、设备标识、手机号或 Cookie。
- 凭据来自环境变量或 GitHub Secrets。
- `qoder_tokens.json`、`qoder_machine_id`、解密后的 Actions cache 都属于敏感数据。
- 不要提交 Token 文件、上传未加密 artifact、把 Secret 写进 Issue，或在日志中粘贴完整授权头。

---

<a id="layout"></a>
## 📁 目录结构

### 🗂️ 数据文件与状态

| 文件 / 目录 | 内容 | 是否提交 |
| :--- | :--- | :---: |
| `qoder_tokens.json` | 轮换后的 Token 状态 | ❌ 已忽略 |
| `qoder_machine_id` | 登录工具生成的设备标识 | ❌ 已忽略 |
| `.qoder-cache/` | Actions 加密状态 | ❌ 已忽略 |
| `qoder_umid/` | 自动提取的 UMID 组件 | ❌ 已忽略 |
| `*_result.json` | 运行结果 | ❌ 已忽略 |

本地运行会直接使用脚本目录状态；青龙需要保证脚本目录可写。Actions 则通过加密 cache 跨运行保存状态。

---

<a id="release"></a>
## 📦 版本与发布

当前标签为 `v1.0.24`。发版时同步脚本版本、登录工具、README、测试与 Release 资产，禁止带入 token 状态文件。

### 📦 版本与发布

- 当前发布版：`v1.0.24`（2026-11-17，登录工具代理支持与网络故障快速退出）。
- 历史版本保留在 [Releases](https://github.com/L0NE-6/Qoder-Daily/releases)。
- 每个 Release 附带完整包、单文件脚本与 `SHA256SUMS.txt`。
- 更新记录见 [CHANGELOG.md](CHANGELOG.md)。

---

<a id="disclaimer"></a>
## ⚠️ 免责声明

仓库内容用于账号持有人维护自身权益。使用前应确认账号、服务条款与所在地规则；作者不对账号限制、接口变化、网络失败或第三方部署造成的损失作出保证。

完整展示与转载规则见 [NOTICE.md](NOTICE.md)。

---

<a id="donate"></a>
## ☕ 赞赏码

### 支持与投喂

如果这个项目节省了你的时间，可以扫码支持维护。赞赏完全自愿，不影响代码、文档与 Issue 处理。

<div align="center">
<table>
<tr>
<td align="center"><strong>微信赞赏码</strong><br /><img src="assets/donate-wechat.png" width="260" alt="微信赞赏码" /></td>
<td align="center"><strong>支付宝赞赏码</strong><br /><img src="assets/donate-alipay.jpg" width="260" alt="支付宝赞赏码" /></td>
</tr>
</table>
</div>

---

<a id="feedback"></a>
## 💬 反馈与 Star History

### 反馈与贡献

- [提交 Issue](https://github.com/L0NE-6/Qoder-Daily/issues)
- [提交 Pull Request](https://github.com/L0NE-6/Qoder-Daily/pulls)
- [查看更新日志](CHANGELOG.md)

反馈请附脱敏日志、复现步骤、运行环境与实际结果。不要贴 Token、Cookie、JWT、手机号或运行状态文件。

<a href="https://star-history.com/#L0NE-6/Qoder-Daily&Date">
  <img src="https://api.star-history.com/svg?repos=L0NE-6/Qoder-Daily&type=Date" alt="Qoder-Daily Star History" />
</a>
