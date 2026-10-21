#!/usr/bin/env python3
"""
🧭 Qoder 每日签到（中国版 / 国际版）- 青龙脚本
------------------------------------------------------------

📌 功能
   Qoder 每日签到（活动领取制，中国版 / 国际版）：
   1. GET  /sash/api/v1/me/campaigns?forceRefresh=true  拉实时活动列表
   2. 找 actionType=CLAIM_BENEFIT 且 claimStatus=CLAIMABLE 的活动
   3. POST /sash/api/v1/me/campaigns/{campaignId}/claim  领取 credits
   4. 已领取（CLAIMED / replayed / 409 ALREADY_CLAIMED）识别为今日已领，不算失败
    5. Pro 升级包：GET eligibility → eligible 时 POST claim，一次性 +1800

   国际版（每日 100 Credits）的活动只下发给带设备风控头的请求
   （Cosy-MachineToken / Cosy-MachineCode / Cosy-MachineType，由本机 UMID
   组件生成）。脚本会先找本机组件；Linux 容器里找不到时会从官方
   qodercli 包提取一份（sha512 校验，可用 QODER_UMID_NO_INSTALL=1 关闭）。
   官方活动窗口每天 10:00（UTC+8）开启，没到点或未下发时按中性文案说明。

🔑 环境变量
   QODER_TOKENS        【中国版】多账号用换行或 & 分隔，每条支持三种写法：
       access_token
       access_token|refresh_token
       备注|access_token|refresh_token
   QODER_GLOBAL_TOKENS 【国际版】同上，第 4 段可选填 uid（备注|access|refresh|uid）
   # 国际版风控身份分层（任选其一）：
   #   1) QODER_MACHINE_TOKEN / QODER_MACHINE_CODE / QODER_MACHINE_TYPE 三件套；
   #   2) QODER_UMID_PATH 指向 runtime-info 组件；
   #   3) 本机 Qoder 客户端 / qodercli（找不到时自动从官方包提取，QODER_UMID_NO_INSTALL=1 可关闭）。
       access_token 形如 dt-xxxx；refresh_token 形如 drt-xxxx（可选，配了可自动续期）

   PUSHPLUS_TOKEN    微信推送通道（可选）
   BARK_URL        iOS 推送地址（可选）
   WECOM_WEBHOOK   企微群机器人地址或 key（可选）
   DINGTALK_WEBHOOK  钉钉机器人 webhook（可选）
   DINGTALK_SECRET   钉钉加签密钥（可选）

⌨️ 命令
   python qoder_daily.py                 正常签到
   python qoder_daily.py --only 2        只跑第 2 个账号
   python qoder_daily.py --refresh-only  只刷新 token（结果存入 qoder_tokens.json）
   python qoder_daily.py --no-notify     不推送

📄 依赖：requests
"""
import base64
import hashlib
import hmac
import io
import json
import os
import platform
import subprocess
import sys
import tarfile
import time
import uuid

import requests

import urllib3
urllib3.disable_warnings()

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGIONS = {
    "cn": {"base": "https://openapi.qoder.com.cn", "label": "中国版"},
    "global": {"base": "https://openapi.qoder.sh", "label": "国际版"},
}
CAMPAIGNS_PATH = "/sash/api/v1/me/campaigns"
CAMPAIGNS_QUERY = "?forceRefresh=true"
PRO_ELIGIBILITY_PATH = "/sash/api/v1/me/pro-upgrade/eligibility"
PRO_CLAIM_PATH = "/sash/api/v1/me/pro-upgrade/claim"
DEVICE_REFRESH_PATH = "/api/v1/deviceToken/refresh"
JOB_REFRESH_PATH = "/api/v1/jobToken/refresh"
SASH_CLIENT_TYPE = "10"
SASH_USER_AGENT = "Qoder"
STORE_FILE = os.path.join(SCRIPT_DIR, "qoder_tokens.json")

ONLY = None
REFRESH_ONLY = False
NO_NOTIFY = False


def log(msg):
    print("%s %s" % (time.strftime("[%H:%M:%S]"), msg), flush=True)


def mask(text, keep=6):
    text = str(text or "")
    if len(text) <= keep + 4:
        return text
    return text[:keep] + "****" + text[-4:]


def split_accounts(raw):
    out = []
    for chunk in (raw or "").replace("&", "\n").splitlines():
        chunk = chunk.strip().strip('"\'')
        if chunk and not chunk.startswith("#"):
            out.append(chunk)
    return out


def request(method, url, headers=None, body=None, timeout=20, retries=3):
    last = None
    for attempt in range(retries):
        try:
            session = requests.Session()
            session.trust_env = False
            return session.request(
                method, url,
                headers=headers or {},
                json=body if body is not None else None,
                timeout=timeout, verify=False,
            )
        except Exception as error:
            last = error
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("请求失败: %s" % last)


def json_of(response):
    try:
        return response.json()
    except Exception:
        return {}


def first_text(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return ""


def token_fp(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


# ---------- token 本地存储（续期会轮换 token，必须落盘才能二次运行） ----------

def load_store():
    try:
        with open(STORE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_store(store):
    try:
        with open(STORE_FILE, "w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2)
    except Exception as error:
        log("⚠️ token 存储写入失败: %s" % error)


def _remember_store_keys(account):
    """Keep fingerprints of the configured credentials before restore/rotation."""
    keys = account.setdefault("_store_keys", [])
    for token in (account.get("refresh"), account.get("access")):
        if token:
            key = token_fp(token)
            if key not in keys:
                keys.append(key)
    return keys


def apply_store(account):
    store = load_store()
    keys = _remember_store_keys(account)
    for key in keys:
        saved = store.get(key)
        if not isinstance(saved, dict):
            continue
        if saved.get("access"):
            account["access"] = saved["access"]
            account["refresh"] = saved.get("refresh", account.get("refresh", ""))
            return True
    return False


def persist(account):
    store = load_store()
    value = {
        "access": account["access"],
        "refresh": account.get("refresh", ""),
        "note": account.get("note", ""),
        "at": int(time.time()),
    }
    # The next process still starts with the original environment/Secret values.
    # Update those aliases as well as the current fingerprints, without storing
    # the original credential strings in the payload.
    for key in _remember_store_keys(account):
        store[key] = value
    save_store(store)


# ---------- 上游协议 ----------

# ---------- 设备风控身份（国际版签到依赖） ----------

UMID_DIR = os.path.join(SCRIPT_DIR, "qoder_umid")
MACHINE_ID_FILE = os.path.join(SCRIPT_DIR, "qoder_machine_id")
RISK_TTL = 50 * 60
DEFAULT_CLIENT_VERSION = "0.2.5"
NPM_PACKAGES = ("https://registry.npmmirror.com", "https://registry.npmjs.org")
NPM_AUTHORITY = "https://registry.npmjs.org"
NPM_PACKAGE_PATH = "@qoder-ai%2fqodercli"
RISK_CACHE = {}


def machine_os():
    arch = platform.machine().lower()
    arch = "x86_64" if arch in ("amd64", "x86_64") else (
        "aarch64" if arch in ("arm64", "aarch64") else "unknown")
    if sys.platform.startswith("win"):
        system = "win32"
    elif sys.platform == "darwin":
        system = "darwin"
    else:
        system = "linux"
    return "%s_%s" % (arch, system)


def machine_hostname():
    raw = (os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "").strip()
    if not raw:
        return ""
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    printable = all(0x21 <= ord(ch) <= 0x7e or ch == " " for ch in raw)
    if printable:
        text = raw
    else:
        cleaned = "".join(ch if 0x21 <= ord(ch) <= 0x7e else "-" for ch in raw)
        cleaned = "-".join(part for part in cleaned.split("-") if part)
        text = ("%s-%s" % (cleaned, digest)) if cleaned else ("unknown-%s" % digest)
    if len(text) > 96:
        text = text[:87].rstrip("- ") + "-" + digest
    return text


def machine_id(account):
    device = first_text(account.get("device_id"))
    if device:
        return device
    try:
        with open(MACHINE_ID_FILE, encoding="utf-8") as handle:
            saved = handle.read().strip()
        if saved:
            return saved
    except Exception:
        pass
    value = uuid.uuid4().hex
    try:
        with open(MACHINE_ID_FILE, "w", encoding="utf-8") as handle:
            handle.write(value)
    except Exception:
        pass
    return value


def resource_dirs(region, names):
    dirs = []
    for name in names:
        if sys.platform.startswith("win"):
            roots = []
            local = os.environ.get("LOCALAPPDATA")
            if local:
                roots.append(os.path.join(local, "Programs", name))
            for variable in ("ProgramFiles", "ProgramFiles(x86)"):
                base = os.environ.get(variable)
                if base:
                    roots.append(os.path.join(base, name))
            for install in roots:
                versions = os.path.join(install, ".qoder-versions")
                try:
                    entries = sorted(os.listdir(versions), reverse=True)
                except Exception:
                    entries = []
                for entry in entries[:8]:
                    dirs.append(os.path.join(versions, entry, "resources"))
                dirs.append(os.path.join(install, "resources"))
        elif sys.platform == "darwin":
            dirs.append("/Applications/%s.app/Contents/Resources" % name)
            dirs.append(os.path.join(os.path.expanduser("~"), "Applications",
                                     "%s.app" % name, "Contents", "Resources"))
        else:
            slug = name.lower().replace(" ", "-")
            dirs.append("/opt/%s/resources" % name)
            dirs.append("/opt/%s/resources" % slug)
            dirs.append("/usr/lib/%s/resources" % slug)
            dirs.append("/snap/%s/current/resources" % slug)
    return dirs


def client_version(region):
    names = ("Qoder", "Qoder CN") if region == "global" else ("Qoder CN", "Qoder")
    for resources in resource_dirs(region, names):
        try:
            with open(os.path.join(resources, "build-manifest.json"), encoding="utf-8") as handle:
                value = json.load(handle).get("productVersion")
        except Exception:
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
    return DEFAULT_CLIENT_VERSION


def find_umid_component(region):
    names = ("Qoder", "Qoder CN") if region == "global" else ("Qoder CN", "Qoder")
    exe_name = "runtime-info.exe" if sys.platform.startswith("win") else "runtime-info"
    app_env = 3 if region == "global" else 0
    custom = _env("QODER_UMID_PATH")
    if custom and os.path.isfile(custom):
        return custom, (4 if region == "global" else 0), "env"
    for resources in resource_dirs(region, names):
        path = os.path.join(resources, "umid", exe_name)
        if os.path.isfile(path):
            return path, app_env, "app"
    cli_env = 4 if region == "global" else 0
    home = os.path.expanduser("~")
    for base in (os.path.join(home, ".qoder", ".bin"), os.path.join(home, ".qoder-cn", ".bin")):
        try:
            entries = sorted(os.listdir(base), reverse=True)
        except Exception:
            continue
        for entry in entries:
            if not entry.startswith("umid-"):
                continue
            path = os.path.join(base, entry, exe_name)
            if os.path.isfile(path):
                return path, cli_env, "cli"
    data = os.path.join(UMID_DIR, exe_name)
    if os.path.isfile(data):
        return data, 4, "data"
    return None


def run_umid_component(component, uid):
    path, env, _source = component
    args = [path, str(env)]
    payload = None
    if sys.platform.startswith("win") or sys.platform == "darwin":
        args.append("--account-stdin")
        payload = (json.dumps({"account": uid or ""}) + "\n").encode("utf-8")
    proc = subprocess.run(args, input=payload, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, timeout=25)
    output = proc.stdout or b""
    if len(output) > 1024 * 1024:
        raise RuntimeError("组件输出过大")
    line = output.decode("utf-8", "replace").splitlines()[0].strip() if output else ""
    data = json.loads(line) if line else {}
    values = {}
    for key in ("machineToken", "machineCode", "machineType"):
        value = data.get(key) if isinstance(data, dict) else None
        if not isinstance(value, str) or not value.strip() or len(value) > 4096:
            raise RuntimeError("组件输出缺少 %s" % key)
        values[key] = value.strip()
    return values


def http_get_bytes(url, timeout=60):
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, timeout=timeout, verify=False)
    response.raise_for_status()
    return response.content


def npm_meta(registry):
    body = http_get_bytes("%s/%s/latest" % (registry, NPM_PACKAGE_PATH), timeout=20)
    payload = json.loads(body.decode("utf-8"))
    dist = payload.get("dist") if isinstance(payload.get("dist"), dict) else {}
    tarball = first_text(dist.get("tarball"))
    integrity = first_text(dist.get("integrity"))
    if not tarball or not integrity:
        raise RuntimeError("元数据缺少 tarball / integrity")
    return {"version": first_text(payload.get("version")), "tarball": tarball,
            "integrity": integrity}


def extract_elf(bundle, machine):
    mark = '"f0VMRgIB'
    position = 0
    while True:
        hit = bundle.find(mark, position)
        if hit < 0:
            return None
        end = bundle.find('"', hit + 1)
        if end < 0:
            return None
        encoded = bundle[hit + 1:end]
        try:
            head = base64.b64decode(encoded[:min(4096, len(encoded))])
        except Exception:
            head = b""
        if len(head) >= 20 and int.from_bytes(head[18:20], "little") == machine:
            try:
                return base64.b64decode(encoded)
            except Exception:
                return None
        position = end + 1


def install_umid_component():
    arch = machine_os().rsplit("_", 1)[0]
    machine = {"x86_64": 62, "aarch64": 183}.get(arch)
    if not machine:
        raise RuntimeError("当前 CPU 架构不受支持")
    try:
        authority = npm_meta(NPM_AUTHORITY)
    except Exception:
        authority = None
    errors = []
    for registry in NPM_PACKAGES:
        try:
            meta = npm_meta(registry)
        except Exception as error:
            errors.append("%s：%s" % (registry, error))
            continue
        if registry != NPM_AUTHORITY and authority:
            if authority["version"] and meta["version"] and authority["version"] != meta["version"]:
                errors.append("%s：版本与官方源不一致" % registry)
                continue
            if authority["integrity"] != meta["integrity"]:
                errors.append("%s：integrity 与官方源不一致" % registry)
                continue
        try:
            body = http_get_bytes(meta["tarball"], timeout=180)
        except Exception as error:
            errors.append("%s：下载失败 %s" % (registry, error))
            continue
        if meta["integrity"].startswith("sha512-"):
            actual = base64.b64encode(hashlib.sha512(body).digest()).decode()
            if actual != meta["integrity"][7:]:
                errors.append("%s：下载内容与 integrity 不一致" % registry)
                continue
        try:
            with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
                handle = archive.extractfile("package/bundle/qodercli.js")
                bundle = handle.read().decode("utf-8", "replace") if handle else ""
        except Exception as error:
            errors.append("%s：解包失败 %s" % (registry, error))
            continue
        elf = extract_elf(bundle, machine)
        if not elf:
            errors.append("%s：包里没有本机架构的 UMID 程序" % registry)
            continue
        os.makedirs(UMID_DIR, exist_ok=True)
        path = os.path.join(UMID_DIR, "runtime-info")
        with open(path, "wb") as output:
            output.write(elf)
        try:
            os.chmod(path, 0o755)
        except Exception:
            pass
        log("   ✅ 已从官方 qodercli %s 提取 UMID 组件" % (meta["version"] or "?"))
        return path
    raise RuntimeError("；".join(errors) if errors else "没有可用来源")


def risk_identity(region, uid):
    key = "%s:%s" % (region, uid)
    cached = RISK_CACHE.get(key)
    if cached and time.time() - cached[0] < RISK_TTL:
        return cached[1], None
    env_values = [_env(name) for name in
                  ("QODER_MACHINE_TOKEN", "QODER_MACHINE_CODE", "QODER_MACHINE_TYPE")]
    if any(env_values):
        if all(env_values):
            values = {"machineToken": env_values[0], "machineCode": env_values[1],
                      "machineType": env_values[2]}
            RISK_CACHE[key] = (time.time(), values)
            return values, None
        return None, ("设备风控环境变量不完整（需要 QODER_MACHINE_TOKEN / "
                      "QODER_MACHINE_CODE / QODER_MACHINE_TYPE 三件套）")
    component = find_umid_component(region)
    if component is None and region == "global" and not _env("QODER_UMID_NO_INSTALL"):
        try:
            log("   📦 未找到本机 UMID 组件，尝试从官方 qodercli 包提取（sha512 校验）")
            install_umid_component()
        except Exception as error:
            return None, "设备风控组件安装失败：%s" % error
        component = find_umid_component(region)
    if component is None:
        return None, "本机没有 Qoder 客户端 / qodercli 的 UMID 组件"
    try:
        values = run_umid_component(component, uid)
    except Exception as error:
        return None, "设备风控身份生成失败：%s" % error
    RISK_CACHE[key] = (time.time(), values)
    return values, None


def risky_sash_headers(account, uid=""):
    headers = sash_headers(account["access"])
    region = account.get("region", "cn")
    headers["Cosy-Version"] = client_version(region)
    headers["Cosy-MachineOS"] = machine_os()
    headers["Cosy-MachineId"] = machine_id(account)
    hostname = machine_hostname()
    if hostname:
        headers["Cosy-MachineHostname"] = hostname
    risk, note = risk_identity(region, uid)
    if risk:
        headers["Cosy-MachineToken"] = risk["machineToken"]
        headers["Cosy-MachineCode"] = risk["machineCode"]
        headers["Cosy-MachineType"] = risk["machineType"]
    return headers, note

def sash_headers(token):
    return {
        "authorization": "Bearer %s" % token,
        "cosy-clienttype": SASH_CLIENT_TYPE,
        "accept": "application/json",
        "accept-language": "zh-CN",
        "user-agent": SASH_USER_AGENT,
    }


def refresh_account(account):
    refresh = account.get("refresh", "")
    if not refresh:
        raise RuntimeError("账号没有 refresh_token，无法续期")
    _remember_store_keys(account)
    path = JOB_REFRESH_PATH if refresh.startswith("jrt-") else DEVICE_REFRESH_PATH
    response = request("POST", account["base"] + path,
                       headers={"User-Agent": "qoder-local-proxy"},
                       body={"refresh_token": refresh})
    if response.status_code in (401, 403):
        raise RuntimeError("刷新令牌已失效或与地区不符，请重新登录")
    payload = json_of(response)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    token = first_text(data.get("device_token"), data.get("deviceToken"),
                       data.get("token"), data.get("access_token"))
    if not token:
        raise RuntimeError("续期响应缺少 access token（HTTP %s）" % response.status_code)
    new_refresh = first_text(data.get("refresh_token"), data.get("refreshToken")) or refresh
    account["access"] = token
    account["refresh"] = new_refresh
    persist(account)
    log("   🔄 token 已续期并保存")
    return True


def fetch_campaigns(account):
    headers, risk_note = risky_sash_headers(account, account.get("uid", ""))
    response = request("GET", account["base"] + CAMPAIGNS_PATH + CAMPAIGNS_QUERY,
                       headers=headers)
    if response.status_code in (401, 403) and account.get("refresh"):
        refresh_account(account)
        headers, risk_note = risky_sash_headers(account, account.get("uid", ""))
        response = request("GET", account["base"] + CAMPAIGNS_PATH + CAMPAIGNS_QUERY,
                           headers=headers)
    return response, risk_note


def claim_campaign(account, campaign_id):
    headers, _note = risky_sash_headers(account, account.get("uid", ""))
    headers["content-type"] = "application/json"
    headers["origin"] = account["base"]
    return request("POST", "%s%s/%s/claim" % (account["base"], CAMPAIGNS_PATH, campaign_id),
                   headers=headers, body={})


def do_checkin(account):
    response, risk_note = fetch_campaigns(account)
    if response.status_code in (401, 403):
        return False, "签到活动查询失败（HTTP %s），请确认凭证有效且地区选择正确" % response.status_code
    if response.status_code == 429:
        return False, "签到活动查询失败（HTTP 429），请稍后重试"
    payload = json_of(response)
    if response.status_code != 200:
        return False, "活动列表返回 HTTP %s" % response.status_code

    rows = payload.get("campaigns")
    if not isinstance(rows, list):
        data = payload.get("data")
        rows = data.get("campaigns") if isinstance(data, dict) else None
    rows = rows if isinstance(rows, list) else []

    target = None
    claimed = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("actionType") != "CLAIM_BENEFIT":
            continue
        status = row.get("claimStatus")
        if status == "CLAIMABLE" and target is None:
            target = row
        elif status == "CLAIMED":
            claimed = True

    if target is None:
        if claimed:
            return False, "今日已领取"
        if account.get("region") == "global":
            if risk_note:
                return False, "未领取：%s。国际版签到需要本机 Qoder 客户端或 qodercli 的 UMID 组件" % risk_note
            return False, "上游暂未给该账号下发每日积分活动（官方活动窗口每天 10:00 UTC+8 开启；若今天已在客户端领过则活动行会消失），稍后再试"
        return False, "当前没有可领取的签到活动"

    campaign_id = first_text(target.get("campaignId"), target.get("campaignKey"))
    if not campaign_id:
        return False, "活动数据里没有 campaignId，无法领取"

    claim = claim_campaign(account, campaign_id)
    body = json_of(claim)
    if claim.status_code == 409 or body.get("result") == "ALREADY_CLAIMED" or body.get("replayed") is True:
        return False, "今日已领取"
    if claim.status_code not in (200, 201):
        message = first_text(body.get("errorMessage"), body.get("message"), body.get("msg"))
        if claim.status_code in (401, 403):
            return False, "领取失败（HTTP %s），请确认凭证有效且地区选择正确 %s" % (claim.status_code, message)
        if claim.status_code == 429:
            return False, "领取失败（HTTP 429），请稍后重试 %s" % message
        return False, "领取失败 HTTP %s %s" % (claim.status_code, message)
    if first_text(body.get("status")) != "CLAIMED":
        return False, "签到未完成（上游状态 %s）" % (first_text(body.get("status")) or "未知")

    benefit = body.get("benefit") if isinstance(body.get("benefit"), dict) else {}
    amount = benefit.get("amount", target.get("benefit", {}).get("amount") if isinstance(target.get("benefit"), dict) else None)
    days = None
    validity = benefit.get("validity") if isinstance(benefit.get("validity"), dict) else {}
    if validity.get("days") is not None:
        days = validity.get("days")
    text = "获得 %s credits" % (amount if amount is not None else "?")
    if days:
        text += "，%s 天有效" % days
    return True, text


def do_pro_upgrade(account):
    """领取一次性 Pro 升级包。返回 (ok, newly_claimed, message)。"""
    headers, _note = risky_sash_headers(account, account.get("uid", ""))
    eligibility = request("GET", account["base"] + PRO_ELIGIBILITY_PATH,
                          headers=headers, retries=1)
    if eligibility.status_code == 401:
        return False, False, "Pro 资格查询鉴权失败"
    if eligibility.status_code in (403, 404, 410):
        return True, False, "Pro 升级包未开放或已领取"
    payload = json_of(eligibility)
    if eligibility.status_code != 200:
        return False, False, "Pro 资格查询失败 HTTP %s" % eligibility.status_code
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    eligible = payload.get("eligible")
    if eligible is None:
        eligible = data.get("eligible")
    if not eligible:
        return True, False, "Pro 升级包不可领取（已领或活动未开放）"

    headers["content-type"] = "application/json"
    headers["origin"] = account["base"]
    response = request("POST", account["base"] + PRO_CLAIM_PATH,
                       headers=headers, body={}, retries=1)
    body = json_of(response)
    text = json.dumps(body, ensure_ascii=False).upper()
    if response.status_code == 409 or "ALREADY" in text:
        return True, False, "Pro 升级包已领取过，本次不计新增"
    if response.status_code != 200:
        return False, False, "Pro 升级包领取失败 HTTP %s" % response.status_code
    if body.get("success") is False:
        return False, False, "Pro 升级包领取失败：%s" % first_text(
            body.get("message"), body.get("msg"), "上游返回失败")
    return True, True, "Pro 升级包领取成功 +1800"


# ---------- 推送 ----------

def post_json(url, payload, timeout=20):
    session = requests.Session()
    session.trust_env = False
    return session.post(url, json=payload, timeout=timeout, verify=False)


def _env(name):
    return os.environ.get(name, "").strip()


def notify_pushplus(title, content):
    token = _env("PUSHPLUS_TOKEN")
    if not token:
        return False
    try:
        text = (content[:18000] + "\n...(已截断)") if len(content) > 18000 else content
        answer = post_json("https://www.pushplus.plus/send",
                           {"token": token, "title": title, "content": text, "template": "txt"})
        return str(json_of(answer).get("code")) == "200"
    except Exception:
        return False


def notify_bark(title, content):
    endpoint = _env("BARK_URL").rstrip("/")
    if not endpoint:
        return False
    try:
        answer = post_json(endpoint, {"title": title, "body": content, "group": "Qoder"})
        return json_of(answer).get("code") == 200
    except Exception:
        return False


def notify_wecom(title, content):
    hook = _env("WECOM_WEBHOOK")
    if not hook:
        return False
    if not hook.startswith("http"):
        hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + hook
    try:
        answer = post_json(hook, {"msgtype": "text",
                                  "text": {"content": ("%s\n%s" % (title, content))[:2000]}})
        return json_of(answer).get("errcode") == 0
    except Exception:
        return False


def notify_dingtalk(title, content):
    hook = _env("DINGTALK_WEBHOOK")
    if not hook:
        return False
    try:
        secret = _env("DINGTALK_SECRET")
        if secret:
            stamp = str(int(time.time() * 1000))
            digest = hmac.new(secret.encode(), ("%s\n%s" % (stamp, secret)).encode(),
                              hashlib.sha256).digest()
            hook += ("&" if "?" in hook else "?") + "timestamp=%s&sign=%s" % (
                stamp, requests.utils.quote(base64.b64encode(digest)))
        answer = post_json(hook, {"msgtype": "text",
                                  "text": {"content": "%s\n%s" % (title, content)}})
        return json_of(answer).get("errcode") == 0
    except Exception:
        return False


def notify_ql(title, content):
    try:
        from notify import send as panel_send
        panel_send(title, content)
        return True
    except Exception:
        pass
    endpoint = _env("QL_URL").rstrip("/")
    token = _env("QL_TOKEN")
    if not endpoint or not token:
        return False
    try:
        session = requests.Session()
        session.trust_env = False
        answer = session.post(endpoint + "/api/system/notify?token=" + token,
                              json={"title": title, "content": content}, timeout=15, verify=False)
        return str(json_of(answer).get("code")) in ("0", "200")
    except Exception:
        return False


def notify_all(title, content):
    handlers = (notify_pushplus, notify_bark, notify_wecom, notify_dingtalk, notify_ql)
    if not any(handler(title, content) for handler in handlers):
        log("（未配置推送渠道，本次只记录日志）")


# ---------- 账号解析与主流程 ----------

def looks_like_token(value):
    value = (value or "").strip()
    return (value.startswith(("dt-", "drt-", "jt-", "jrt-", "eyJ"))
            or value.count(".") >= 2 or len(value) > 80)


def parse_accounts(raw, region="cn"):
    accounts = []
    for index, line in enumerate(split_accounts(raw), 1):
        parts = [part.strip() for part in line.split("|")]
        fallback = ("账号%d" if region == "cn" else "国际版账号%d") % index
        note = fallback
        uid = ""
        if len(parts) >= 4:
            note, access, refresh, uid = parts[0], parts[1], parts[2], parts[3]
        elif len(parts) == 3:
            note, access, refresh = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            first, second = parts[0], parts[1]
            if looks_like_token(first) and looks_like_token(second):
                access, refresh = first, second          # access|refresh
            elif looks_like_token(second):
                note, access, refresh = first, second, ""  # 备注|access
            else:
                access, refresh = first, second          # access|（空 refresh）
        else:
            access, refresh = parts[0], ""
        if access:
            accounts.append({"note": note or fallback, "access": access, "refresh": refresh,
                             "uid": uid, "region": region, "base": REGIONS[region]["base"]})
    return accounts


def main():
    global ONLY, REFRESH_ONLY, NO_NOTIFY
    args = sys.argv[1:]
    if "--refresh-only" in args:
        REFRESH_ONLY = True
    if "--no-notify" in args:
        NO_NOTIFY = True
    if "--only" in args:
        try:
            ONLY = int(args[args.index("--only") + 1])
        except Exception:
            ONLY = None

    accounts = parse_accounts(os.environ.get("QODER_TOKENS", ""), "cn")
    accounts += parse_accounts(os.environ.get("QODER_GLOBAL_TOKENS", ""), "global")
    if not accounts:
        log("❌ 未配置 QODER_TOKENS / QODER_GLOBAL_TOKENS（多条用换行或 & 分隔；每条: access_token 或 access_token|refresh_token）")
        return

    log("╔════════════════════════════════════╗")
    log("║ 🧭 Qoder 每日签到（中国版 / 国际版）║")
    log("╚════════════════════════════════════╝")
    cn_total = len([item for item in accounts if item["region"] == "cn"])
    log("👥 账号数: %d（中国版 %d / 国际版 %d）" % (len(accounts), cn_total, len(accounts) - cn_total))

    report = []
    for index, account in enumerate(accounts, 1):
        if ONLY and index != ONLY:
            continue
        apply_store(account)
        log("👤 [%d] %s [%s] token=%s" % (index, account["note"],
            REGIONS[account["region"]]["label"], mask(account["access"])))
        if REFRESH_ONLY:
            try:
                refresh_account(account)
                report.append("账号%d %s: ✅ token 续期成功" % (index, account["note"]))
            except Exception as error:
                report.append("账号%d %s: ❌ token 续期失败: %s" % (index, account["note"], error))
            continue
        try:
            success, message = do_checkin(account)
            icon = "✅" if success else "ℹ️"
            log("   %s %s" % (icon, message))
            report.append("账号%d %s: %s %s" % (index, account["note"], icon, message))
            pro_ok, pro_new, pro_message = do_pro_upgrade(account)
            pro_icon = "✅" if pro_ok and pro_new else ("ℹ️" if pro_ok else "❌")
            log("   %s %s" % (pro_icon, pro_message))
            report.append("账号%d %s: %s %s" % (index, account["note"], pro_icon, pro_message))
        except Exception as error:
            log("   ❌ 异常: %s" % error)
            report.append("账号%d %s: ❌ %s" % (index, account["note"], error))
        time.sleep(1.5)

    summary = "🧭 Qoder 签到报告\n" + "\n".join(report) + "\n🕐 " + time.strftime("%Y-%m-%d %H:%M")
    log(summary)
    if not NO_NOTIFY and not REFRESH_ONLY:
        notify_all("🧭 Qoder 签到报告", summary)


if __name__ == "__main__":
    main()
