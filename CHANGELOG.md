# 更新日志

## v1.0.13（2026-11-04）

- 文档发行版：同步首屏使用边界、反收费/反搬运声明、`NOTICE.md`、微信/支付宝赞赏码防诈骗提醒与六语导航。
- Release 完整包现在包含最新 README、NOTICE、docs 与图片资产；签到/领取主逻辑未变更，脚本版本仍为 `v1.0.12`。
- 验证：Markdown 渲染、相对链接、二维码资产与发布包清单检查通过；本版未使用真实账号执行签到。

## v1.0.12（2026-10-31）

- 对齐 3.3.0-beta.6 的 Qoder 每日积分窗口行为：活动窗口 10:00 开启后，若上游暂未下发，重试窗口从 30 分钟放宽到 1 小时。
- 默认重试间隔从 90 秒改为 10 分钟，最多 6 次，避免高频重试触发风控；`QODER_WINDOW_RETRY_GAP` / `QODER_WINDOW_RETRY_MAX` 仍可覆盖。

## v1.0.11（2026-10-29）

- 修正额度类 403 与凭证失效混判：HTTP 403 响应含 `pricingUrl` 或业务码 `112` 时按「额度耗尽」处理，账号冷却 30 分钟，不再触发 token 续期，也不按登录失败上报。
- 业务码 `110` / `Billing daily count exceeded` 按「每日计费次数上限」处理，冷却到本地零点，封顶 6 小时（最低 60 秒）。
- `auth_dead_response` 只在非额度类 401/403 或业务码 `105` / `10019901001` 时判为会话失效；成功活动列表与 claim 路径保持不变。
- 新增 5 项离线回归测试，覆盖 `112`、`pricingUrl`、`110` 冷却边界、普通 401/403 与额度 403 不触发续期；测试总数 33 项。
- 实证来源：[shuishuipingan/qoder2api-hub@1033662b](https://github.com/shuishuipingan/qoder2api-hub/commit/1033662b)，对应上游 `v1.7.9`。

## v1.0.10（2026-10-23）

- 跟进 Qoder CN 活动列表按请求头分桶的下发异常：完整设备头返回 HTTP 200 + `showCampaign:false` / `campaigns:[]` 时，改用 `Authorization`、`Cosy-ClientType`、`User-Agent`、`Content-Type` 四件套复取一次。
- 最小头也返回空表时保留首次空响应；最小头自身返回 `401`、业务码 `105`、`429` 或 `5xx` 时原样透传，不伪装成“暂无活动”。
- 空表复取只对中国版启用；国际版路径保持不变。原有 token 失效续期后再请求的流程继续保留。
- 参考上游实证 PR [smart-open/TraeWorkAssistant#133](https://github.com/smart-open/TraeWorkAssistant/pull/133)（merge `6d0056dd93a914d056f81dcf7dfcc7b07725119a`），新增 7 项离线回归测试，完整测试增至 28 项；不执行真实账号领取。

## v1.0.9（2026-10-23）

- 活动列表遇到 HTTP 401/403 或业务码 `105` / `10019901001` 时，不再只看 HTTP 状态；强制续期一次后同号重试，避免令牌“时间未过期但已被上游作废”时一直失败。
- 续期失败仍按原错误返回，不用“续期失败”覆盖上游文案。
- 新增业务码 `105` 强制续期与单次重试回归测试。

## v1.0.8（2026-10-23）

- 跟进 Qoder CN 权益中心/活动下发变更：中国版每日 100 Credits 现在也要求 Qoder CN 自己的官方设备身份。
- UMID 身份改为地区隔离：中国版只读 Qoder CN / `qoderclicn` 并使用环境参数 `0`；国际版只读 Qoder / `qodercli` 并使用环境参数 `3`。
- 中国版新增 CLI 缓存发现（`~/.qoder-cn/.bin/runtime-info-*`）、`/opt/Qoder-CN` 与客户端目录探测，并支持从 `@qodercn-ai/qoderclicn` 自动提取组件；国际版继续使用 `@qoder-ai/qodercli`。
- 无本机客户端时的 `Cosy-Version` 兜底从 `0.2.5` 升到当前桌面 worker runtime `1.1.69`。
- 新增 `QODERCN_RUNTIME_INFO` / `QODER_RUNTIME_INFO` 地区覆盖变量，保留 `QODER_UMID_PATH` 通用覆盖。
- 中国版活动行缺失时也会明确提示 UMID 身份要求，不再只报“没有可领取活动”。
- 新增地区隔离与缺失身份提示回归测试，测试总数 19 项。

## v1.0.7（2026-10-23）

- 开窗延迟重试改为默认开启：10:00-10:30 CST 内暂未发现活动行时，按 90 秒间隔最多重试 16 次。
- 设置 `QODER_WINDOW_RETRY=0` 可恢复单次检查；Qinglong 定时建议仍锚定北京时间 10:05。

## v1.0.6（2026-10-22）

- 活动列表去掉 `forceRefresh=true`：该参数是本地缓存标记，官方客户端从不发送；旧参数会让服务端过滤掉每日活动行。
- Pro 升级包改走 campaigns：移除不存在的 `/pro-upgrade/{eligibility,claim}` 端点，改为筛选 Pro/upgrade 行，或通过只读 `/campaigns/{id}/reward` 核对隐藏面值。
- Pro 对国际版直接跳过，不再发起注定 404 的请求。
- 领取响应兼容 `data` 解包、`CLAIMED/GRANTED/SUCCESS`、`replayed`，只有 409 + `ALREADY_CLAIMED/REPLAYED` 才按已领处理。
- Pro 领取前后读取 `/api/v2/quota/usage`，按真实额度差额报告；不再硬编码“+1800”。
- 新增可选 10:00-10:30 CST 开窗延迟重试；Actions 模板改为北京时间 10:05，并启用最多 16 次、90 秒间隔的延迟重试。
- 新增 8 项 campaign/Pro/窗口边界离线测试，与原 7 项 token 测试合计 15 项。

## v1.0.5（2026-10-22）

- 修复 token 轮换后索引断裂（issue #1）：保存时同时更新原始配置指纹与当前令牌指纹，下一轮仍用原环境变量 / Secret 启动也能恢复最新 access / refresh token；
- 新增 Actions 跨运行状态保存：加密缓存 `qoder_tokens.json` 与 `qoder_machine_id`，配置 `QODER_CACHE_KEY` 后公开 / 私有 fork 都可安全续用；
- Actions 在脚本异常时也会尝试保存已完成的 token 轮换，避免旧 Secret 中的刷新令牌失效后无法恢复；
- 新增无凭据回归测试与 tests workflow（7 项 token store 测试全部通过）。

## v1.0.4（2026-10-20）

- 新增一次性 Pro 升级包：`eligibility → claim`，成功领取 +1800 积分。
- 已领取、活动未开放、404/403/410 均按中性状态处理，不重复计数。
- 复用现有设备风控头与 token 续期链路。

## v1.0.3（2026-10-10）

- 签到脚本支持国际版（qoder-intl）每日 100 Credits：国际版账号用 `QODER_GLOBAL_TOKENS` 单独配置，自动走 `openapi.qoder.sh`。
- 国际版风控身份分层：环境变量三件套（`QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE`）、`QODER_UMID_PATH` 组件、本机 Qoder 客户端 / qodercli；Linux / 青龙缺组件时可从官方包提取（sha512 校验，`QODER_UMID_NO_INSTALL=1` 关闭）。
- 活动窗口（每天 10:00 UTC+8）未开或风控身份缺失时不落「已签」状态、如实提示，后续轮次自动补领；401/403/429 与非 CLAIMED 状态按上游口径回报。

## v1.0.2（2026-10-09）

- 仓库描述与 README 顶栏同步：明确「中国版每日签到 + 国际版设备授权登录」。
- 说明澄清：每日签到活动仅中国版有，国际版用于设备授权登录获取 Token。

## v1.0.1（2026-10-09）

- Actions 工作流默认改为**仅手动触发**：上游仓库不再空跑定时任务。
- fork 后如需定时，取消 `.github/workflows/daily.yml` 里 `schedule:` 的注释即可。
- README 同步补充 fork 启用定时的说明。

## v1.0.0（2026-10-09）

- 首个公开版本
- 首个版本：Qoder 中国版每日签到 + 设备授权登录工具，支持多账号、Token 自动续期、多渠道推送。

> 每个版本单独发布 Release，历史版本保留可下载。
