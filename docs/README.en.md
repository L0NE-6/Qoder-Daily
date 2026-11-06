# 🧭 Qoder Daily

**Daily rewards for Qoder China and Global accounts, with device authorization, region-specific UMID identities, multi-account support, and recoverable token rotation.**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> Complete Chinese documentation: [../README.md](../README.md)

## Overview

Qoder Daily reads the current benefit campaigns and claims the available daily Credits for Qoder China and Global accounts. Both regions require the official device identity for that region. The script resolves identity from environment variables, a runtime-info component, a local client or CLI, or a verified official package. If the identity is missing, it reports a neutral result instead of claiming that the account has checked in.

The companion `qoder_login.py` uses the official device authorization flow. Confirm the authorization in a browser once; it then outputs an access token and, when issued, a refresh token. This avoids SMS and manual traffic capture for the normal login path.

## Core capabilities

- Claims only campaigns classified as daily Credits; model-scoped, Sonus and SOTA benefits are excluded.
- Separates Qoder CN / `qoderclicn` identity from Qoder / `qodercli` identity.
- Retries during the 10:00-11:00 Beijing time campaign window.
- Rotates refresh tokens and restores state across runs.
- Distinguishes quota exhaustion, daily billing limits, and invalid sessions.
- Claims a Pro campaign only when it is actually discovered and its value can be checked.
- Sends optional PushPlus, Bark, WeCom, DingTalk, or Qinglong notifications.

## Get a token

```bash
python qoder_login.py
python qoder_login.py --region global
```

The default command is for Qoder China. Use `--region global` for the international service. The tool opens the official authorization page, polls for completion, verifies the token by requesting the campaign list, and prints a line like:

```text
access_token|refresh_token
```

Put the China result in `QODER_TOKENS` and the Global result in `QODER_GLOBAL_TOKENS`.

## Minimum Qinglong setup

1. Install `requests` with `pip3 install requests`.
2. Upload `qoder_daily.py`.
3. Set `QODER_TOKENS` and/or `QODER_GLOBAL_TOKENS`.
4. Create a scheduled task:

```bash
task qoder_daily.py
```

Suggested cron:

```cron
5 10 * * *
```

The campaign opens at 10:00 Beijing time. The script can continue retrying in the one-hour window when no campaign row has appeared yet.

## Minimum GitHub Actions setup

Add these Secrets under **Settings → Secrets and variables → Actions**:

| Secret | Required | Purpose |
| :--- | :---: | :--- |
| `QODER_TOKENS` | for China | China account credentials |
| `QODER_GLOBAL_TOKENS` | for Global | Global account credentials |
| `QODER_CACHE_KEY` | recommended | Random long key used to encrypt the Actions token cache |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | conditional | Device identity triple when no runtime-info component is available |
| `QODERCN_RUNTIME_INFO` / `QODER_RUNTIME_INFO` / `QODER_UMID_PATH` | optional | Component path overrides |
| Push Secrets | optional | `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK`, `DINGTALK_SECRET` |

The bundled workflow is manual-only by default. Run **Actions → Qoder Daily → Run workflow** first. To enable the schedule, uncomment:

```yaml
schedule:
  - cron: "5 2 * * *"
```

The cron uses UTC and equals 10:05 Beijing time. GitHub may disable a fork's scheduled workflow until it is enabled in Actions. A schedule only runs from the repository's default branch.

## Token state in Actions

The workflow archives `qoder_tokens.json` and `qoder_machine_id`, encrypts the archive with `QODER_CACHE_KEY`, and stores it with `actions/cache`. Without the cache key, the run still works but the rotated refresh token may be lost after the job. Cache entries can be evicted; if both the cache and old refresh token are gone, authorize the account again.

## Key environment variables

| Variable | Format or default | Description |
| :--- | :--- | :--- |
| `QODER_TOKENS` | `access` / `access\|refresh` / `remark\|access\|refresh` | China accounts |
| `QODER_GLOBAL_TOKENS` | same, optionally `remark\|access\|refresh\|uid` | Global accounts. The UID may be omitted; the script reads it from the campaign list. |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | three values | Manual device identity |
| `QODERCN_RUNTIME_INFO` | path | China runtime-info component |
| `QODER_RUNTIME_INFO` | path | Global runtime-info component |
| `QODER_UMID_PATH` | path | General component override |
| `QODER_UMID_NO_INSTALL` | `1` | Disable automatic extraction from official packages |
| `QODER_WINDOW_RETRY` | default `1` | Enable campaign-window retry |
| `QODER_WINDOW_RETRY_MAX` | script default `6` | Maximum attempts, internally capped at 6 |
| `QODER_WINDOW_RETRY_GAP` | script default `600` | Seconds between attempts |
| `QODER_CACHE_KEY` | random string | Actions cache encryption only |

The checked-in workflow currently overrides retry max/gap to `16` and `90`, but the script caps attempts at six, so the effective maximum remains six.

## Command-line options

| Option | Effect |
| :--- | :--- |
| none | Run every configured China and Global account |
| `--only N` | Run the Nth account in the combined list |
| `--no-notify` | Disable notifications |
| `--refresh-only` | Refresh tokens and save state without claiming |

## Success semantics

A campaign must be present and claim successfully before the account is reported as completed. A missing device identity, a closed window, or an empty campaign list remains a neutral state that can be retried. Quota code `112` or `pricingUrl` cools the account for about 30 minutes; code `110` applies the daily billing limit and cools until local midnight, capped at six hours. Only non-quota 401/403 or codes `105` / `10019901001` enter the token-refresh path.

## Privacy

Tokens and device identifiers are supplied through environment variables or Secrets. `qoder_tokens.json`, `qoder_machine_id`, decrypted cache state, and authorization headers are sensitive. Do not commit token files, upload unencrypted artifacts, paste a complete token into an Issue, or expose the cache key in public logs.

## Usage and redistribution

The official repository, scripts, deployment instructions, and releases are and remain free. Without explicit written permission, do not package this project as a paid resource, paid deployment service, or paid update service; do not remove attribution and claim the work as original; do not impersonate the author; and do not use the author's identity, name, avatar, or payment QR codes to imply official endorsement. Do not repost the project through unrelated accounts, groups, channels, or paid platforms for follower growth, traffic diversion, or resale. Violations may lead to a takedown request, and the author may pause updates or archive or delete the repository. Read the full [NOTICE.md](../NOTICE.md).

## Links

- [Releases](https://github.com/L0NE-6/Qoder-Daily/releases)
- [Issues](https://github.com/L0NE-6/Qoder-Daily/issues)
- [Chinese README](../README.md)
- [Changelog](../CHANGELOG.md)

## Disclaimer

This project is intended for personal learning and automation. Follow Qoder and related service terms. Use it at your own risk.
