# 🧭 Qoder Daily

**Qoder 中國版 / 國際版每日獎勵領取工具，支援裝置授權登入、雙地區 UMID、多帳號與可恢復的 Token 輪換。**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> 完整中文文件請見 [../README.md](../README.md)。

## 概覽

Qoder Daily 會讀取目前下發的權益活動，為 Qoder 中國版與國際版帳號領取可用的每日 Credits。兩個地區都需要各自官方裝置身份。腳本會依序從環境變數、runtime-info 元件、本機客戶端或 CLI、經驗證的官方套件取得身份；缺少身份時保留中性結果，不把帳號謊報成已簽。

配套的 `qoder_login.py` 使用官方裝置授權流程。在瀏覽器確認一次授權後，工具會輸出 access token，並在服務下發時一併給出 refresh token，不需要驗證碼或手動抓包。

## 核心能力

- 只領取分類為每日 Credits 的活動，排除限定模型、Sonus 與 SOTA 權益。
- 分離 Qoder CN / `qoderclicn` 與 Qoder / `qodercli` 裝置身份。
- 在北京時間 10:00-11:00 活動視窗內補拉。
- 輪換 refresh token，並跨執行恢復狀態。
- 區分額度耗盡、每日計費上限與登入失效。
- 只有實際發現並可核對面值時才處理 Pro 活動。
- 可選 PushPlus、Bark、企業微信、釘釘或青龍通知。

## 取得 Token

```bash
python qoder_login.py
python qoder_login.py --region global
```

預設為 Qoder 中國版，國際版加上 `--region global`。工具會開啟官方授權頁、輪詢完成狀態、呼叫活動列表驗證 Token，最後輸出一行：

```text
access_token|refresh_token
```

中國版結果填入 `QODER_TOKENS`，國際版填入 `QODER_GLOBAL_TOKENS`。

## 最短青龍設定

1. 執行 `pip3 install requests`。
2. 上傳 `qoder_daily.py`。
3. 設定 `QODER_TOKENS` 與 / 或 `QODER_GLOBAL_TOKENS`。
4. 建立定時任務：

```bash
task qoder_daily.py
```

建議 cron：

```cron
5 10 * * *
```

活動在北京時間 10:00 開窗。若上游暫未下發活動行，腳本會在一小時視窗內繼續重試。

## 最短 GitHub Actions 設定

在 **Settings → Secrets and variables → Actions** 新增：

| Secret | 必填 | 用途 |
| :--- | :---: | :--- |
| `QODER_TOKENS` | 中國版需要 | 中國版帳號憑據 |
| `QODER_GLOBAL_TOKENS` | 國際版需要 | 國際版帳號憑據 |
| `QODER_CACHE_KEY` | 建議 | 加密 Actions Token 快取的隨機長字串 |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 條件需要 | 無 runtime-info 元件時的手動裝置身份 |
| `QODERCN_RUNTIME_INFO` / `QODER_RUNTIME_INFO` / `QODER_UMID_PATH` | 否 | 元件路徑覆蓋 |
| 推送 Secrets | 否 | `PUSHPLUS_TOKEN`、`BARK_URL`、`WECOM_WEBHOOK`、`DINGTALK_WEBHOOK`、`DINGTALK_SECRET` |

內建工作流程預設只能手動觸發。先執行 **Actions → Qoder Daily → Run workflow**。需要定時時，取消註解：

```yaml
schedule:
  - cron: "5 2 * * *"
```

此 cron 使用 UTC，等於北京時間每天 10:05。Fork 後 GitHub 可能預設停用 scheduled workflow，需在 Actions 頁面啟用；schedule 只從預設分支執行。

## Actions Token 狀態

工作流程會打包 `qoder_tokens.json` 與 `qoder_machine_id`，使用 `QODER_CACHE_KEY` 加密後存入 `actions/cache`。沒有 cache key 時仍可執行，但輪換後的 refresh token 可能在作業結束後遺失。Cache 也可能被淘汰；如果狀態與舊 refresh token 都已失效，需要重新授權。

## 關鍵環境變數

| 變數 | 格式或預設 | 說明 |
| :--- | :--- | :--- |
| `QODER_TOKENS` | `access` / `access\|refresh` / `備註\|access\|refresh` | 中國版帳號 |
| `QODER_GLOBAL_TOKENS` | 同上，可再追加 `\|uid` | 國際版帳號；UID 可省略，腳本會從活動列表自動讀取。 |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 三個值 | 手動裝置身份 |
| `QODERCN_RUNTIME_INFO` | 路徑 | 中國版 runtime-info 元件 |
| `QODER_RUNTIME_INFO` | 路徑 | 國際版 runtime-info 元件 |
| `QODER_UMID_PATH` | 路徑 | 通用元件覆蓋 |
| `QODER_UMID_NO_INSTALL` | `1` | 禁止從官方套件自動提取 |
| `QODER_WINDOW_RETRY` | 預設 `1` | 啟用活動視窗補拉 |
| `QODER_WINDOW_RETRY_MAX` | 腳本預設 `6` | 最大次數，腳本內部上限為 6 |
| `QODER_WINDOW_RETRY_GAP` | 腳本預設 `600` | 兩次嘗試間隔秒數 |
| `QODER_CACHE_KEY` | 隨機長字串 | 僅供 Actions cache 加密 |

目前 workflow 將重試次數與間隔覆蓋為 `16` 與 `90` 秒，但腳本會把最大次數限制在 6，因此實際最多仍為 6 次。

## 命令列參數

| 參數 | 作用 |
| :--- | :--- |
| 無 | 執行全部中國版與國際版帳號 |
| `--only N` | 只執行合併列表中的第 N 個帳號 |
| `--no-notify` | 關閉推送 |
| `--refresh-only` | 只刷新 Token 並保存狀態 |

## 成功語義

只有活動實際下發且 claim 成功，才會把帳號報告為完成。缺少裝置身份、視窗未開或活動列表為空時保留中性狀態，後續仍可補拉。業務碼 `112` 或 `pricingUrl` 按額度耗盡冷卻約 30 分鐘；`110` 按每日計費上限冷卻到本地零點，封頂 6 小時。只有非額度類 401/403 或 `105` / `10019901001` 才進入 Token 續期。

## 隱私提醒

Token 與裝置標識只應透過環境變數或 Secrets 提供。`qoder_tokens.json`、`qoder_machine_id`、解密後的 cache 狀態與授權標頭都屬於敏感資料。請勿提交 Token 檔、上傳未加密 artifact、把完整 Token 貼進 Issue，或在公開日誌中暴露 cache key。

## 使用邊界與轉載聲明

官方倉庫、腳本、部署說明與 Release 均免費公開。未經作者明確書面許可，請勿將本專案包裝為付費資源、付費部署或包更新服務，請勿刪除署名後冒充原創，請勿冒充作者，亦請勿使用作者身分、名稱、頭像或收款碼製造背書假象；請勿搬運到無關帳號、群組、頻道或付費平台以漲粉、截流、轉賣或引流。違規時，作者可要求下架，並可視情況暫停更新、封存或刪除倉庫。完整規則見 [NOTICE.md](../NOTICE.md)。

## 連結

- [Releases](https://github.com/L0NE-6/Qoder-Daily/releases)
- [Issues](https://github.com/L0NE-6/Qoder-Daily/issues)
- [簡體中文完整文件](../README.md)
- [更新記錄](../CHANGELOG.md)

## 免責聲明

本專案供個人學習與自動化使用。請遵守 Qoder 與相關服務條款，並自行承擔使用風險。
