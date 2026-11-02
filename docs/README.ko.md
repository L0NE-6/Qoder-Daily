# 🧭 Qoder Daily

**Qoder 중국판 / 글로벌판 일일 보상 도구이며 기기 인증 로그인, 지역별 UMID, 멀티 계정, 복구 가능한 토큰 교체를 지원합니다.**

[简体中文](../README.md) | [English](README.en.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (BR)](README.pt-BR.md)

> 전체 중국어 문서는 [../README.md](../README.md)에서 확인할 수 있습니다.

## 개요

Qoder Daily는 현재 제공되는 혜택 캠페인을 읽고 Qoder 중국판과 글로벌판 계정의 일일 Credits를 수령합니다. 두 지역 모두 해당 지역의 공식 기기 ID가 필요합니다. 스크립트는 환경 변수, runtime-info 구성 요소, 로컬 클라이언트 또는 CLI, 검증된 공식 패키지에서 ID를 확인합니다. ID가 없으면 체크인 완료로 가장하지 않고 중립적인 결과를 반환합니다.

`qoder_login.py`는 공식 기기 인증 흐름을 사용합니다. 브라우저에서 한 번 승인하면 access token과 발급된 경우 refresh token을 출력합니다. 일반 로그인 경로에서는 SMS나 수동 패킷 캡처가 필요하지 않습니다.

## 핵심 기능

- 중국판과 글로벌판의 `CLAIM_BENEFIT` 캠페인을 수령합니다.
- Qoder CN / `qoderclicn`과 Qoder / `qodercli` 기기 ID를 분리합니다.
- 베이징 시간 10:00-11:00 캠페인 창에서 재시도합니다.
- refresh token을 교체하고 실행 간 상태를 복원합니다.
- quota 소진, 일일 과금 한도, 세션 만료를 구분합니다.
- 실제로 발견하고 값을 확인한 Pro 캠페인만 처리합니다.
- PushPlus, Bark, WeCom, DingTalk, Qinglong 알림을 선택적으로 보냅니다.

## 토큰 받기

```bash
python qoder_login.py
python qoder_login.py --region global
```

기본은 중국판입니다. 글로벌판은 `--region global`을 사용합니다. 공식 인증 페이지에서 승인하면 도구가 완료를 확인하고 캠페인 목록으로 토큰을 검증한 뒤 다음 형식을 출력합니다.

```text
access_token|refresh_token
```

중국판은 `QODER_TOKENS`, 글로벌판은 `QODER_GLOBAL_TOKENS`에 넣습니다.

## 최소 Qinglong 설정

1. `pip3 install requests`를 실행합니다.
2. `qoder_daily.py`를 업로드합니다.
3. `QODER_TOKENS` 및/또는 `QODER_GLOBAL_TOKENS`를 설정합니다.
4. 예약 작업을 만듭니다.

```bash
task qoder_daily.py
```

권장 cron:

```cron
5 10 * * *
```

캠페인은 베이징 시간 10:00에 열립니다. 아직 활동 행이 내려오지 않으면 스크립트가 한 시간 창에서 계속 재시도합니다.

## 최소 GitHub Actions 설정

**Settings → Secrets and variables → Actions**에 다음 Secrets를 추가합니다.

| Secret | 필수 | 용도 |
| :--- | :---: | :--- |
| `QODER_TOKENS` | 중국판 필요 | 중국판 계정 |
| `QODER_GLOBAL_TOKENS` | 글로벌판 필요 | 글로벌판 계정 |
| `QODER_CACHE_KEY` | 권장 | Actions 토큰 캐시를 암호화하는 긴 무작위 문자열 |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 조건부 | runtime-info가 없을 때 기기 ID 세트 |
| `QODERCN_RUNTIME_INFO` / `QODER_RUNTIME_INFO` / `QODER_UMID_PATH` | 선택 | 구성 요소 경로 재정의 |
| 알림 Secrets | 선택 | `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK`, `DINGTALK_SECRET` |

포함된 워크플로는 기본적으로 수동 실행만 지원합니다. **Actions → Qoder Daily → Run workflow**를 실행합니다. 예약 실행을 켜려면 다음 주석을 해제합니다.

```yaml
schedule:
  - cron: "5 2 * * *"
```

UTC 기준 `5 2 * * *`는 베이징 시간 매일 10:05입니다. Fork 후 scheduled workflow가 비활성화되어 있으면 Actions 화면에서 활성화해야 하며, schedule은 기본 브랜치에서만 실행됩니다.

## Actions 토큰 상태

workflow는 `qoder_tokens.json`과 `qoder_machine_id`를 묶고 `QODER_CACHE_KEY`로 암호화하여 `actions/cache`에 저장합니다. cache key가 없어도 실행은 가능하지만 교체된 refresh token이 작업 후 사라질 수 있습니다. Cache는 제거될 수 있으며 상태와 이전 refresh token이 모두 무효라면 다시 인증해야 합니다.

## 주요 환경 변수

| 변수 | 형식 또는 기본값 | 설명 |
| :--- | :--- | :--- |
| `QODER_TOKENS` | `access` / `access\|refresh` / `메모\|access\|refresh` | 중국판 계정 |
| `QODER_GLOBAL_TOKENS` | 같은 형식, 선택적으로 `\|uid` 추가 | 글로벌판 계정 |
| `QODER_MACHINE_TOKEN` / `QODER_MACHINE_CODE` / `QODER_MACHINE_TYPE` | 세 값 | 수동 기기 ID |
| `QODERCN_RUNTIME_INFO` | 경로 | 중국판 runtime-info |
| `QODER_RUNTIME_INFO` | 경로 | 글로벌판 runtime-info |
| `QODER_UMID_PATH` | 경로 | 공통 구성 요소 재정의 |
| `QODER_UMID_NO_INSTALL` | `1` | 공식 패키지 자동 추출 비활성화 |
| `QODER_WINDOW_RETRY` | 기본 `1` | 캠페인 창 재시도 |
| `QODER_WINDOW_RETRY_MAX` | 스크립트 기본 `6` | 최대 횟수, 내부 상한 6 |
| `QODER_WINDOW_RETRY_GAP` | 스크립트 기본 `600` | 재시도 간격 초 |
| `QODER_CACHE_KEY` | 무작위 문자열 | Actions cache 암호화 전용 |

현재 workflow는 최대 횟수와 간격을 `16`, `90`초로 재정의하지만 스크립트가 최대 횟수를 6으로 제한하므로 실제 상한은 6회입니다.

## 명령행 옵션

| 옵션 | 동작 |
| :--- | :--- |
| 없음 | 모든 중국판 및 글로벌판 계정 실행 |
| `--only N` | 합친 목록의 N번째 계정만 실행 |
| `--no-notify` | 알림 비활성화 |
| `--refresh-only` | 수령 없이 토큰 갱신과 상태 저장만 수행 |

## 성공 판정

캠페인이 실제로 내려오고 claim이 성공해야 계정을 완료로 보고합니다. 기기 ID 누락, 시간 창 밖, 빈 캠페인 목록은 중립 상태로 남겨 이후 재시도할 수 있습니다. 코드 `112` 또는 `pricingUrl`은 약 30분 quota 냉각, `110`은 일일 과금 한도로 처리하여 로컬 자정까지 냉각하며 최대 6시간입니다. quota가 아닌 401/403 또는 `105` / `10019901001`만 토큰 갱신 경로로 들어갑니다.

## 개인정보 보호

토큰과 기기 ID는 환경 변수 또는 Secrets로 공급합니다. `qoder_tokens.json`, `qoder_machine_id`, 복호화된 cache 상태, 인증 헤더는 민감합니다. 토큰 파일 커밋, 암호화되지 않은 artifact 업로드, Issue에 전체 토큰 게시, 공개 로그의 cache key 노출을 피하세요.

## 사용 범위 및 재배포 안내

공식 저장소, 스크립트, 배포 안내, Release는 무료로 공개됩니다. 저자의 명시적 서면 허가 없이 이 프로젝트를 유료 자료, 유료 배포, 업데이트 대행으로 포장하거나, 출처와 저작자 표시를 삭제하고 원작자로 가장하거나, 저자의 신원, 이름, 아바타, 결제 QR 코드를 사용해 공식 승인으로 오인하게 하는 행위를 금지합니다. 관련 없는 계정, 그룹, 채널, 유료 플랫폼에 옮겨 팔로워 증가, 트래픽 유도, 재판매를 하는 행위도 금지됩니다. 위반 시 게시 중단 요청을 받을 수 있으며 저자는 업데이트 중단, 저장소 보관 또는 삭제를 결정할 수 있습니다. 전체 규칙은 [NOTICE.md](../NOTICE.md)를 확인하세요.

## 링크

- [Releases](https://github.com/L0NE-6/Qoder-Daily/releases)
- [Issues](https://github.com/L0NE-6/Qoder-Daily/issues)
- [중국어 README](../README.md)
- [변경 기록](../CHANGELOG.md)

## 면책 조항

이 프로젝트는 개인 학습과 자동화를 위한 것입니다. Qoder 및 관련 서비스 약관을 확인하고 사용 위험은 사용자 본인이 부담하세요.
