# 🧭 Qoder Daily

**Qoder 中国版 / 国際版のデイリー報酬取得ツールです。デバイス認可ログイン、地域別 UMID、複数アカウント、復元可能なトークンローテーションに対応します。**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> 完全な中国語ドキュメントは [../README.md](../README.md) にあります。

## 概要

Qoder Daily は現在配信されている特典キャンペーンを読み取り、Qoder 中国版と国際版のアカウントで利用可能なデイリー Credits を取得します。どちらの地域でも、その地域向けの公式デバイス ID が必要です。スクリプトは環境変数、runtime-info コンポーネント、ローカルクライアントまたは CLI、検証済みの公式パッケージから ID を解決します。ID がない場合は、チェックイン済みと偽らず中立的な結果を返します。

`qoder_login.py` は公式デバイス認可フローを使います。ブラウザで一度認可すると access token と、発行されていれば refresh token を出力します。通常のログインでは SMS や手動パケットキャプチャは不要です。

## 主な機能

- 毎日 Credits と判定したキャンペーンだけを取得し、モデル限定・Sonus・SOTA の特典は除外します。
- Qoder CN / `qoderclicn` と Qoder / `qodercli` の ID を分離します。
- 北京時間 10:00-11:00 のキャンペーン時間帯で再試行します。
- refresh token をローテーションし、実行間で状態を復元します。
- クォータ枯渇、日次課金上限、セッション失効を区別します。
- 実際に検出し、値を確認できた Pro キャンペーンだけを処理します。
- PushPlus、Bark、WeCom、DingTalk、Qinglong 通知を任意で送信します。

## トークン取得

```bash
python qoder_login.py
python qoder_login.py --region global
```

既定は中国版です。国際版では `--region global` を指定します。公式認可ページを開き、完了をポーリングし、キャンペーン一覧でトークンを検証して次の形式を出力します。

```text
access_token|refresh_token
```

中国版は `QODER_TOKENS`、国際版は `QODER_GLOBAL_TOKENS` に設定します。

## 最小構成の Qinglong

1. `pip3 install requests` を実行します。
2. `qoder_daily.py` をアップロードします。
3. `QODER_TOKENS` と / または `QODER_GLOBAL_TOKENS` を設定します。
4. 定期タスクを作成します。

```bash
task qoder_daily.py
```

推奨 cron:

```cron
5 10 * * *
```

キャンペーンは北京時間 10:00 に開きます。まだ行が配信されていない場合、スクリプトは 1 時間の時間帯で再試行します。

## 最小構成の GitHub Actions

**Settings → Secrets and variables → Actions** に次の Secrets を追加します。

| Secret | 必須 | 用途 |
| :--- | :---: | :--- |
| `QODER_TOKENS` | 中国版で必須 | 中国版アカウント |
| `QODER_GLOBAL_TOKENS` | 国際版で必須 | 国際版アカウント |
| `QODER_CACHE_KEY` | 推奨 | Actions のトークンキャッシュを暗号化するランダム文字列 |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 条件付き | runtime-info がない場合のデバイス ID |
| `QODERCN_RUNTIME_INFO` / `QODER_RUNTIME_INFO` / `QODER_UMID_PATH` | 任意 | コンポーネントパス上書き |
| 通知 Secrets | 任意 | `PUSHPLUS_TOKEN`、`BARK_URL`、`WECOM_WEBHOOK`、`DINGTALK_WEBHOOK`、`DINGTALK_SECRET` |

同梱ワークフローは既定では手動実行のみです。**Actions → Qoder Daily → Run workflow** を実行します。スケジュールを有効にする場合は次をコメント解除します。

```yaml
schedule:
  - cron: "5 2 * * *"
```

UTC 表記の `5 2 * * *` は北京時間の毎日 10:05 です。Fork 後は scheduled workflow が無効な場合があるため Actions 画面で有効化します。schedule は既定ブランチからのみ実行されます。

## Actions のトークン状態

workflow は `qoder_tokens.json` と `qoder_machine_id` をまとめ、`QODER_CACHE_KEY` で暗号化して `actions/cache` に保存します。cache key がない場合も実行できますが、ローテーション後の refresh token がジョブ後に失われる可能性があります。cache は削除されることがあり、状態と古い refresh token の両方が無効なら再認可が必要です。

## 主要な環境変数

| 変数 | 形式または既定値 | 説明 |
| :--- | :--- | :--- |
| `QODER_TOKENS` | `access` / `access\|refresh` / `メモ\|access\|refresh` | 中国版アカウント |
| `QODER_GLOBAL_TOKENS` | 同形式、必要なら `\|uid` を追加 | 国際版アカウント。UID は省略可能で、スクリプトがキャンペーン一覧から自動取得します。 |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 3 つの値 | 手動デバイス ID |
| `QODERCN_RUNTIME_INFO` | パス | 中国版 runtime-info |
| `QODER_RUNTIME_INFO` | パス | 国際版 runtime-info |
| `QODER_UMID_PATH` | パス | 共通コンポーネント上書き |
| `QODER_UMID_NO_INSTALL` | `1` | 公式パッケージからの自動抽出を無効化 |
| `QODER_WINDOW_RETRY` | 既定 `1` | 時間帯内の再試行 |
| `QODER_WINDOW_RETRY_MAX` | スクリプト既定 `6` | 最大回数。内部上限は 6 |
| `QODER_WINDOW_RETRY_GAP` | スクリプト既定 `600` | 再試行間隔の秒数 |
| `QODER_CACHE_KEY` | ランダム文字列 | Actions cache 暗号化専用 |

現在の workflow は最大回数と間隔を `16`、`90` 秒に上書きしますが、スクリプトが回数を 6 に制限するため実効上限は 6 回です。

## コマンドライン

| オプション | 動作 |
| :--- | :--- |
| なし | 中国版と国際版の全アカウントを実行 |
| `--only N` | 結合リストの N 番目だけを実行 |
| `--no-notify` | 通知を無効化 |
| `--refresh-only` | 取得せずトークン更新と状態保存だけを実行 |

## 成功判定

キャンペーンが実際に配信され、claim が成功した場合だけアカウントを完了として報告します。デバイス ID 不足、時間帯外、空のキャンペーン一覧は中立状態として残し、後続の再試行対象にします。コード `112` または `pricingUrl` は約 30 分のクォータ冷却、`110` はローカル日付の翌日 0 時まで日次課金上限として扱い、最大 6 時間です。非クォータの 401/403 または `105` / `10019901001` だけがトークン更新へ進みます。

## プライバシー

トークンとデバイス ID は環境変数または Secrets から供給します。`qoder_tokens.json`、`qoder_machine_id`、復号後の cache、認可ヘッダーは機密情報です。トークンファイルのコミット、未暗号化 artifact の公開、Issue への完全なトークン掲載、公開ログへの cache key 露出を避けてください。

## 利用範囲と再配布について

公式リポジトリ、スクリプト、デプロイ手順、Release は無料で公開されます。作者の明示的な書面許可なく、本プロジェクトを有料リソース、有料デプロイ、更新代行として販売または包装すること、著作者情報を削除して自作と主張すること、作者になりすますこと、作者の身元、名称、アイコン、支払い用 QR コードを使って公式承認があるように見せることを禁止します。無関係なアカウント、グループ、チャンネル、有料プラットフォームへ転載し、フォロワー増加、流入誘導、転売を図る行為も禁止します。違反時は削除要請の対象となり、作者は更新の停止、リポジトリのアーカイブまたは削除を行う場合があります。詳細は [NOTICE.md](../NOTICE.md) を確認してください。

## リンク

- [Releases](https://github.com/L0NE-6/Qoder-Daily/releases)
- [Issues](https://github.com/L0NE-6/Qoder-Daily/issues)
- [中国語 README](../README.md)
- [変更履歴](../CHANGELOG.md)

## 免責事項

本プロジェクトは個人の学習と自動化を目的としています。Qoder および関連サービスの利用規約を確認し、自己責任で使用してください。
