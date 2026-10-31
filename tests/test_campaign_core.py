import ast
import json
import os
import re
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path


SOURCE_PATH = Path(__file__).resolve().parents[1] / "qoder_daily.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCTIONS = {
    node.name: node
    for node in TREE.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}


def load_functions(*names, **globals_):
    # Legacy cases only exercise the auth path; quota cases load the real classifier.
    globals_.setdefault("quota_cooldown", lambda response: ("", 0))
    globals_.setdefault("quota_cooldown_message", lambda kind, seconds: "quota")
    namespace = {"__builtins__": __builtins__, **globals_}
    body = [FUNCTIONS[name] for name in names]
    module = ast.Module(body=body, type_ignores=[])
    exec(compile(module, str(SOURCE_PATH), "exec"), namespace)
    return namespace


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}

    def json(self):
        return self.payload


class CampaignCoreTests(unittest.TestCase):
    def test_campaigns_url_has_no_force_refresh_query(self):
        captured = {}

        def request(method, url, headers=None, retries=3):
            captured["method"] = method
            captured["url"] = url
            return FakeResponse()

        module = load_functions(
            "fetch_campaigns", "_fetch_campaigns_once", "auth_dead_response",
            "campaign_response_is_empty", "minimal_sash_headers",
            "first_text", "region_key",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="10",
            SASH_USER_AGENT="Qoder",
            risky_sash_headers=lambda account, uid="": ({}, None),
            request=request,
            refresh_account=lambda account: None,
            json_of=lambda response: response.payload,
        )
        account = {"base": "https://example.test", "refresh": ""}
        module["fetch_campaigns"](account)
        self.assertEqual(
            "https://example.test/sash/api/v1/me/campaigns",
            captured["url"],
        )
        self.assertNotIn("forceRefresh", captured["url"])

    def test_business_code_105_forces_refresh_and_one_retry(self):
        calls = {"request": 0, "refresh": 0}
        responses = [
            FakeResponse(200, {"code": 105, "message": "token expired"}),
            FakeResponse(200, {"data": {"campaigns": [{"id": "daily"}]}}),
        ]

        def request(method, url, headers=None, retries=3):
            calls["request"] += 1
            return responses.pop(0)

        def refresh(account):
            calls["refresh"] += 1
            return True

        module = load_functions(
            "fetch_campaigns", "_fetch_campaigns_once", "auth_dead_response",
            "campaign_response_is_empty", "minimal_sash_headers",
            "first_text", "region_key",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="10",
            SASH_USER_AGENT="Qoder",
            risky_sash_headers=lambda account, uid="": ({}, None),
            request=request,
            refresh_account=refresh,
            json_of=lambda response: response.payload,
        )
        response, _note = module["fetch_campaigns"](
            {"base": "https://example.test", "refresh": "drt-test"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, calls["request"])
        self.assertEqual(1, calls["refresh"])

    def test_cn_full_headers_empty_then_minimal_headers_success(self):
        original = FakeResponse(200, {
            "showCampaign": False,
            "campaigns": [],
        })
        recovered = FakeResponse(200, {
            "showCampaign": True,
            "campaigns": [{"campaignId": "daily", "claimStatus": "CLAIMABLE"}],
        })
        calls = []

        def request(method, url, headers=None, retries=3):
            calls.append({
                "method": method,
                "url": url,
                "headers": headers,
                "retries": retries,
            })
            return original if len(calls) == 1 else recovered

        module = load_functions(
            "fetch_campaigns", "_fetch_campaigns_once", "auth_dead_response",
            "campaign_response_is_empty", "minimal_sash_headers", "first_text",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="10",
            SASH_USER_AGENT="Qoder",
            risky_sash_headers=lambda account, uid="": (
                {"authorization": "Bearer dt-current",
                 "cosy-machineid": "device-id"}, None),
            request=request,
            refresh_account=lambda account: None,
            json_of=lambda response: response.payload,
            region_key=lambda region: (
                "global" if region in ("global", "intl", "international")
                else "cn"),
        )
        response, _note = module["fetch_campaigns"]({
            "region": "cn",
            "base": "https://cn.example.test",
            "access": "dt-current",
            "refresh": "",
        })

        self.assertIs(recovered, response)
        self.assertEqual(2, len(calls))
        self.assertEqual({
            "authorization": "Bearer dt-current",
            "cosy-clienttype": "10",
            "user-agent": "Qoder",
            "content-type": "application/json",
        }, calls[1]["headers"])
        self.assertEqual(1, calls[1]["retries"])

    def test_cn_minimal_headers_also_empty_preserves_original(self):
        original = FakeResponse(200, {
            "showCampaign": False,
            "campaigns": [],
        })
        fallback_empty = FakeResponse(200, {"campaigns": []})
        calls = []

        def request(method, url, headers=None, retries=3):
            calls.append(headers)
            return original if len(calls) == 1 else fallback_empty

        module = load_functions(
            "fetch_campaigns", "_fetch_campaigns_once", "auth_dead_response",
            "campaign_response_is_empty", "minimal_sash_headers", "first_text",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="10",
            SASH_USER_AGENT="Qoder",
            risky_sash_headers=lambda account, uid="": (
                {"authorization": "Bearer dt-current"}, None),
            request=request,
            refresh_account=lambda account: None,
            json_of=lambda response: response.payload,
            region_key=lambda region: "cn",
        )
        response, _note = module["fetch_campaigns"]({
            "region": "cn",
            "base": "https://cn.example.test",
            "access": "dt-current",
        })

        self.assertIs(original, response)
        self.assertEqual(2, len(calls))

    def test_empty_campaign_fallback_is_limited_to_cn(self):
        cases = [
            ("global", {"campaigns": []}, 1),
            ("cn", {"campaigns": [{"campaignId": "daily"}]}, 1),
        ]
        for region, payload, expected_calls in cases:
            with self.subTest(region=region, payload=payload):
                calls = []

                def request(method, url, headers=None, retries=3):
                    calls.append(headers)
                    return FakeResponse(200, payload)

                module = load_functions(
                    "fetch_campaigns", "_fetch_campaigns_once",
                    "auth_dead_response",
                    "campaign_response_is_empty",
                    "minimal_sash_headers", "first_text",
                    CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
                    SASH_CLIENT_TYPE="10",
                    SASH_USER_AGENT="Qoder",
                    risky_sash_headers=lambda account, uid="": (
                        {"authorization": "Bearer dt-current"}, None),
                    request=request,
                    refresh_account=lambda account: None,
                    json_of=lambda response: response.payload,
                    region_key=lambda value: (
                        "global" if value in ("global", "intl", "international")
                        else "cn"),
                )
                module["fetch_campaigns"]({
                    "region": region,
                    "base": "https://example.test",
                    "access": "dt-current",
                })
                self.assertEqual(expected_calls, len(calls))

    def test_minimal_fallback_errors_are_not_masked(self):
        failures = [
            FakeResponse(401, {"code": 401}),
            FakeResponse(200, {"code": 105}),
            FakeResponse(429, {"message": "rate limited"}),
            FakeResponse(503, {"message": "unavailable"}),
        ]
        for failure in failures:
            with self.subTest(status=failure.status_code, payload=failure.payload):
                responses = [
                    FakeResponse(200, {"showCampaign": False, "campaigns": []}),
                    failure,
                ]

                module = load_functions(
                    "fetch_campaigns", "_fetch_campaigns_once",
                    "auth_dead_response",
                    "campaign_response_is_empty",
                    "minimal_sash_headers", "first_text",
                    CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
                    SASH_CLIENT_TYPE="10",
                    SASH_USER_AGENT="Qoder",
                    risky_sash_headers=lambda account, uid="": (
                        {"authorization": "Bearer dt-current"}, None),
                    request=lambda method, url, headers=None, retries=3: (
                        responses.pop(0)),
                    refresh_account=lambda account: None,
                    json_of=lambda response: response.payload,
                    region_key=lambda region: "cn",
                )
                response, _note = module["fetch_campaigns"]({
                    "region": "cn",
                    "base": "https://cn.example.test",
                    "access": "dt-current",
                })
                self.assertIs(failure, response)

    def test_unsuccessful_campaigns_do_not_trigger_minimal_fallback(self):
        failures = [
            FakeResponse(401, {"code": 401}),
            FakeResponse(200, {"code": 105, "campaigns": []}),
            FakeResponse(429, {"message": "rate limited"}),
            FakeResponse(500, {"message": "server error"}),
        ]
        for failure in failures:
            with self.subTest(status=failure.status_code, payload=failure.payload):
                calls = []

                def request(method, url, headers=None, retries=3):
                    calls.append(headers)
                    return failure

                module = load_functions(
                    "fetch_campaigns", "_fetch_campaigns_once",
                    "auth_dead_response",
                    "campaign_response_is_empty",
                    "minimal_sash_headers", "first_text",
                    CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
                    SASH_CLIENT_TYPE="10",
                    SASH_USER_AGENT="Qoder",
                    risky_sash_headers=lambda account, uid="": (
                        {"authorization": "Bearer dt-current"}, None),
                    request=request,
                    refresh_account=lambda account: None,
                    json_of=lambda response: response.payload,
                    region_key=lambda region: "cn",
                )
                response, _note = module["fetch_campaigns"]({
                    "region": "cn",
                    "base": "https://cn.example.test",
                    "access": "dt-current",
                })
                self.assertIs(failure, response)
                self.assertEqual(1, len(calls))

    def test_minimal_fallback_105_reuses_token_refresh_path(self):
        responses = [
            FakeResponse(200, {"showCampaign": False, "campaigns": []}),
            FakeResponse(200, {"code": 105}),
            FakeResponse(200, {"campaigns": [{"campaignId": "daily"}]}),
        ]
        calls = {"request": 0, "refresh": 0}

        def request(method, url, headers=None, retries=3):
            calls["request"] += 1
            return responses.pop(0)

        def refresh(account):
            calls["refresh"] += 1
            account["access"] = "dt-renewed"
            return True

        module = load_functions(
            "fetch_campaigns", "_fetch_campaigns_once", "auth_dead_response",
            "campaign_response_is_empty", "minimal_sash_headers", "first_text",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="10",
            SASH_USER_AGENT="Qoder",
            risky_sash_headers=lambda account, uid="": (
                {"authorization": "Bearer %s" % account["access"]}, None),
            request=request,
            refresh_account=refresh,
            json_of=lambda response: response.payload,
            region_key=lambda region: "cn",
        )
        response, _note = module["fetch_campaigns"]({
            "region": "cn",
            "base": "https://cn.example.test",
            "access": "dt-expired",
            "refresh": "drt-current",
        })

        self.assertEqual("daily", response.payload["campaigns"][0]["campaignId"])
        self.assertEqual(3, calls["request"])
        self.assertEqual(1, calls["refresh"])

    def test_campaign_rows_report_auth_rate_limit_and_server_errors(self):
        failures = [
            FakeResponse(401, {"message": "unauthorized"}),
            FakeResponse(200, {"code": 105}),
            FakeResponse(429, {"message": "rate limited"}),
            FakeResponse(503, {"message": "unavailable"}),
        ]
        for failure in failures:
            with self.subTest(status=failure.status_code, payload=failure.payload):
                module = load_functions(
                    "fetch_campaign_rows", "auth_dead_response", "first_text",
                    fetch_campaigns=lambda account: (failure, None),
                    json_of=lambda response: response.payload,
                    campaign_rows_from_payload=lambda payload: [],
                )
                rows, response, _risk_note, error = module[
                    "fetch_campaign_rows"]({"region": "cn"})
                self.assertEqual([], rows)
                self.assertIs(failure, response)
                self.assertTrue(error)

    def test_claim_response_matrix(self):
        module = load_functions(
            "claim_response_verdict", "first_text", "amount_of",
            json_of=lambda response: response.payload,
            CLAIM_FAILURE_TEXT={
                "REDEMPTION_CODE_OUT_OF_STOCK": "今日名额已发完，等待下一轮",
                "SAME_PERSON_ALREADY_CLAIMED": "同一设备身份下的其他账号已领取",
            },
        )
        cases = [
            (200, {"data": {"status": "CLAIMED"}}, "claimed"),
            (200, {"status": "GRANTED"}, "claimed"),
            (200, {"status": "SUCCESS"}, "claimed"),
            (200, {"status": "CLAIMED", "replayed": True}, "already"),
            (409, {"errorCode": "ALREADY_CLAIMED"}, "already"),
            (409, {"errorCode": "OTHER_CONFLICT"}, "error"),
            (200, {"status": "BLOCKED",
                   "failureCode": "SAME_PERSON_ALREADY_CLAIMED"}, "blocked"),
            (200, {"failureCode": "REDEMPTION_CODE_OUT_OF_STOCK"}, "error"),
        ]
        for status, payload, expected in cases:
            verdict, _amount, _message = module["claim_response_verdict"](
                FakeResponse(status, payload))
            self.assertEqual(expected, verdict, payload)

    def test_discover_pro_uses_hidden_reward_probe(self):
        rows = [
            {"campaignId": "daily", "campaignKey": "act-daily",
             "actionType": "CLAIM_BENEFIT", "claimStatus": "CLAIMABLE",
             "benefit": {"kind": "CREDITS", "amount": 100}},
            {"campaignId": "hidden-pro", "campaignKey": "act-hidden",
             "actionType": "VIEW_DETAILS", "claimStatus": "CLAIMABLE"},
        ]
        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_looks_like_pro_upgrade", "campaign_id_of",
            "discover_pro_campaign",
            fetch_campaign_reward=lambda account, campaign_id: (
                {"kind": "CREDITS", "amount": 1800}
                if campaign_id == "hidden-pro" else
                {"kind": "CREDITS", "amount": 100}),
        )
        target, claimed, probes = module["discover_pro_campaign"]({}, rows)
        self.assertEqual("hidden-pro", target["campaignId"])
        self.assertIsNone(claimed)
        self.assertTrue(any("hidden-pro" in item for item in probes))

    def test_daily_pick_excludes_pro_row_and_accepts_empty_action_type(self):
        rows = [
            {"campaignId": "pro", "campaignKey": "pro-upgrade",
             "actionType": "CLAIM_BENEFIT", "claimStatus": "CLAIMABLE",
             "benefit": {"kind": "CREDITS", "amount": 1800}},
            {"campaignId": "daily", "campaignKey": "act-daily",
             "actionType": "", "claimStatus": "CLAIMABLE",
             "benefit": {"kind": "CREDITS", "amount": 100}},
        ]
        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_looks_like_pro_upgrade", "pick_daily_campaign",
        )
        target, claimed = module["pick_daily_campaign"](rows)
        self.assertEqual("daily", target["campaignId"])
        self.assertFalse(claimed)

    def test_global_skips_pro_without_request(self):
        def unexpected(*args, **kwargs):
            raise AssertionError("global must not request campaigns for Pro")

        module = load_functions(
            "do_pro_upgrade",
            fetch_campaign_rows=unexpected,
        )
        result = module["do_pro_upgrade"]({"region": "global"})
        self.assertEqual((True, False, "国际版暂无 Pro 升级活动"), result)

    def test_pro_claim_uses_quota_delta(self):
        rows = [{"campaignId": "pro-1"}]
        target = {
            "campaignId": "pro-1", "campaignKey": "pro-upgrade",
            "actionType": "CLAIM_BENEFIT", "claimStatus": "CLAIMABLE",
            "benefit": {"kind": "CREDITS", "amount": 1800},
        }
        quotas = [100, 1900]

        module = load_functions(
            "do_pro_upgrade",
            fetch_campaign_rows=lambda account: (rows, FakeResponse(), None, ""),
            discover_pro_campaign=lambda account, seen: (target, None, []),
            campaign_id_of=lambda row: "pro-1",
            quota_total_remaining=lambda account: quotas.pop(0),
            claim_campaign=lambda account, campaign_id: FakeResponse(
                200, {"status": "CLAIMED"}),
            claim_response_verdict=lambda response: ("claimed", 1800, "领取成功"),
            time=type("Time", (), {"sleep": staticmethod(lambda seconds: None)}),
        )
        ok, newly_claimed, message = module["do_pro_upgrade"]({"region": "cn"})
        self.assertTrue(ok)
        self.assertTrue(newly_claimed)
        self.assertIn("+1800", message)

    def test_daily_window_boundaries(self):
        class FakeDateTime:
            current = None

            @classmethod
            def now(cls, tz=None):
                return cls.current

        module = load_functions(
            "daily_window_active", datetime=FakeDateTime, CN_TZ=object())
        for hour, minute, expected in (
                (9, 59, False), (10, 0, True), (10, 30, True),
                (10, 59, True), (11, 0, False)):
            FakeDateTime.current = type("Now", (), {"hour": hour, "minute": minute})()
            self.assertEqual(expected, module["daily_window_active"]())

    def test_window_retry_defaults_on_and_can_be_disabled(self):
        enabled_module = load_functions(
            "daily_window_retry_enabled", _env=lambda name: "")
        self.assertTrue(enabled_module["daily_window_retry_enabled"]())
        disabled_module = load_functions(
            "daily_window_retry_enabled", _env=lambda name: "0")
        self.assertFalse(disabled_module["daily_window_retry_enabled"]())

    def test_window_retry_fetches_until_daily_row_appears(self):
        daily = {
            "campaignId": "daily-1", "campaignKey": "act-daily",
            "actionType": "CLAIM_BENEFIT", "claimStatus": "CLAIMABLE",
            "benefit": {"kind": "CREDITS", "amount": 100},
        }
        responses = [[], [daily]]
        calls = {"fetch": 0, "sleep": 0}

        def fetch_rows(account):
            calls["fetch"] += 1
            return responses.pop(0), FakeResponse(), None, ""

        def sleep(seconds):
            calls["sleep"] += 1

        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_looks_like_pro_upgrade", "campaign_id_of",
            "pick_daily_campaign", "do_checkin",
            fetch_campaign_rows=fetch_rows,
            daily_window_retry_enabled=lambda: True,
            daily_window_active=lambda: True,
            _env=lambda name: {"QODER_WINDOW_RETRY_MAX": "2",
                               "QODER_WINDOW_RETRY_GAP": "1"}.get(name, ""),
            log=lambda message: None,
            time=type("Time", (), {"sleep": staticmethod(sleep)}),
            claim_campaign=lambda account, campaign_id: FakeResponse(
                200, {"status": "CLAIMED"}),
            claim_response_verdict=lambda response: ("claimed", 100, "领取成功"),
            json_of=lambda response: response.payload,
        )
        ok, message = module["do_checkin"]({"region": "cn"})
        self.assertTrue(ok)
        self.assertIn("100", message)
        self.assertEqual(2, calls["fetch"])
        self.assertEqual(1, calls["sleep"])

    def test_umid_override_is_region_scoped(self):
        fake_os = type("FakeOS", (), {
            "path": type("FakePath", (), {
                "isfile": staticmethod(lambda path: path.endswith("runtime-info")),
            })(),
        })()
        fake_sys = type("FakeSys", (), {"platform": "linux"})()
        module = load_functions(
            "region_key", "find_umid_component",
            _env=lambda name: {
                "QODERCN_RUNTIME_INFO": "/cn/runtime-info",
                "QODER_RUNTIME_INFO": "/intl/runtime-info",
            }.get(name, ""),
            UMID_RUNTIME_ENV={"cn": 0, "global": 3},
            UMID_OVERRIDE_ENV={
                "cn": "QODERCN_RUNTIME_INFO",
                "global": "QODER_RUNTIME_INFO",
            },
            os=fake_os,
            sys=fake_sys,
        )
        self.assertEqual(
            ("/cn/runtime-info", 0, "env"),
            module["find_umid_component"]("cn"),
        )
        self.assertEqual(
            ("/intl/runtime-info", 3, "env"),
            module["find_umid_component"]("global"),
        )

    def test_cli_runtime_cache_dirs_do_not_mix_regions(self):
        module = load_functions(
            "region_key", "cli_runtime_cache_dirs",
            _env=lambda name: "",
            os=os,
        )
        cn_dirs = module["cli_runtime_cache_dirs"]("cn")
        intl_dirs = module["cli_runtime_cache_dirs"]("global")
        self.assertTrue(cn_dirs[0].endswith(".qoder-cn"))
        self.assertTrue(intl_dirs[0].endswith(".qoder"))
        self.assertNotEqual(cn_dirs[0], intl_dirs[0])

    def test_npm_metadata_uses_region_package(self):
        calls = []

        def fetch(url, timeout=60):
            calls.append(url)
            return (
                '{"version":"1.1.77","dist":{"tarball":"https://example.test/pkg.tgz",'
                '"integrity":"sha512-test"}}'
            ).encode("utf-8")

        module = load_functions(
            "region_key", "npm_meta",
            NPM_PACKAGE_PATHS={
                "cn": "@qodercn-ai%2fqoderclicn",
                "global": "@qoder-ai%2fqodercli",
            },
            http_get_bytes=fetch,
            json=__import__("json"),
            first_text=lambda *values: next(
                (value.strip() for value in values
                 if isinstance(value, str) and value.strip()), ""),
        )
        self.assertEqual("1.1.77", module["npm_meta"]("https://registry.test", "cn")["version"])
        self.assertIn("@qodercn-ai%2fqoderclicn", calls[-1])
        module["npm_meta"]("https://registry.test", "global")
        self.assertIn("@qoder-ai%2fqodercli", calls[-1])

    def test_cn_missing_row_reports_identity_requirement(self):
        module = load_functions(
            "do_checkin",
            fetch_campaign_rows=lambda account: (
                [], FakeResponse(), "本机没有 Qoder CN 的 UMID 组件", ""),
            pick_daily_campaign=lambda rows: (None, False),
            daily_window_retry_enabled=lambda: False,
            region_key=lambda region: "cn" if region == "cn" else "global",
        )
        ok, message = module["do_checkin"]({"region": "cn"})
        self.assertFalse(ok)
        self.assertIn("中国版", message)
        self.assertIn("UMID", message)

    def test_quota_112_and_pricing_url_are_exhausted_not_auth_death(self):
        module = load_functions(
            "quota_cooldown", "auth_dead_response",
            json_of=lambda response: response.payload,
            json=json, re=re, time=time, datetime=datetime, timedelta=timedelta,
            QUOTA_112_COOLDOWN=1800,
            QUOTA_110_MAX_COOLDOWN=21600,
            QUOTA_110_MIN_COOLDOWN=60,
        )
        payloads = (
            {"code": 112},
            {"code": "112"},
            {"data": {"code": "112"}},
            {"code": 403, "pricingUrl": "https://example.test/pricing"},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                response = FakeResponse(403, payload)
                self.assertEqual(
                    ("exhausted", 1800), module["quota_cooldown"](response))
                self.assertFalse(module["auth_dead_response"](response))

    def test_quota_110_cooldown_is_bounded_to_six_hours(self):
        module = load_functions(
            "quota_cooldown", "auth_dead_response",
            json_of=lambda response: response.payload,
            json=json, re=re, time=time, datetime=datetime, timedelta=timedelta,
            QUOTA_112_COOLDOWN=1800,
            QUOTA_110_MAX_COOLDOWN=21600,
            QUOTA_110_MIN_COOLDOWN=60,
        )
        cases = (
            (datetime(2026, 10, 29, 23, 59, 30), 60),
            (datetime(2026, 10, 29, 12, 0, 0), 21600),
            (datetime(2026, 10, 29, 20, 0, 0), 14400),
        )
        for moment, expected in cases:
            with self.subTest(moment=moment):
                response = FakeResponse(
                    403, {"code": 110, "message": "Billing daily count exceeded"})
                kind, seconds = module["quota_cooldown"](
                    response, now=moment.timestamp())
                self.assertEqual("daily", kind)
                self.assertEqual(expected, seconds)
                self.assertLessEqual(seconds, 6 * 3600)
                self.assertGreaterEqual(seconds, 60)
                self.assertFalse(module["auth_dead_response"](response))

    def test_generic_401_and_403_still_require_refresh(self):
        module = load_functions(
            "quota_cooldown", "auth_dead_response",
            json_of=lambda response: response.payload,
            json=json, re=re, time=time, datetime=datetime, timedelta=timedelta,
            QUOTA_112_COOLDOWN=1800,
            QUOTA_110_MAX_COOLDOWN=21600,
            QUOTA_110_MIN_COOLDOWN=60,
        )
        for status in (401, 403):
            with self.subTest(status=status):
                response = FakeResponse(status, {"message": "token expired"})
                self.assertEqual(("", 0), module["quota_cooldown"](response))
                self.assertTrue(module["auth_dead_response"](response))

    def test_quota_403_does_not_trigger_token_refresh(self):
        calls = {"request": 0, "refresh": 0}

        def request(method, url, headers=None, retries=3):
            calls["request"] += 1
            return FakeResponse(403, {"code": 112, "pricingUrl": "/pricing"})

        def refresh(account):
            calls["refresh"] += 1
            return True

        module = load_functions(
            "fetch_campaigns", "_fetch_campaigns_once", "auth_dead_response",
            "campaign_response_is_empty", "minimal_sash_headers", "first_text",
            "quota_cooldown", "region_key",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="10",
            SASH_USER_AGENT="Qoder",
            risky_sash_headers=lambda account, uid="": ({}, None),
            request=request,
            refresh_account=refresh,
            json_of=lambda response: response.payload,
            json=json, re=re, time=time, datetime=datetime, timedelta=timedelta,
            QUOTA_112_COOLDOWN=1800,
            QUOTA_110_MAX_COOLDOWN=21600,
            QUOTA_110_MIN_COOLDOWN=60,
        )
        response, _note = module["fetch_campaigns"]({
            "region": "global",
            "base": "https://example.test",
            "access": "dt-current",
            "refresh": "drt-current",
        })
        self.assertEqual(403, response.status_code)
        self.assertEqual(1, calls["request"])
        self.assertEqual(0, calls["refresh"])

    def test_campaign_rows_report_quota_without_login_failure(self):
        module = load_functions(
            "fetch_campaign_rows", "auth_dead_response", "first_text",
            "quota_cooldown", "quota_cooldown_message",
            fetch_campaigns=lambda account: (
                FakeResponse(403, {"code": 112, "pricingUrl": "/pricing"}), None),
            json_of=lambda response: response.payload,
            campaign_rows_from_payload=lambda payload: [],
            json=json, re=re, time=time, datetime=datetime, timedelta=timedelta,
            QUOTA_112_COOLDOWN=1800,
            QUOTA_110_MAX_COOLDOWN=21600,
            QUOTA_110_MIN_COOLDOWN=60,
        )
        rows, _response, _risk_note, error = module["fetch_campaign_rows"](
            {"region": "global"})
        self.assertEqual([], rows)
        self.assertIn("额度", error)
        self.assertIn("30 分钟", error)
        self.assertNotIn("凭证", error)
        self.assertNotIn("重新登录", error)


if __name__ == "__main__":
    unittest.main()
