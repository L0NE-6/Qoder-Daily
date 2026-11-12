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


def _quota_sequence(values):
    remaining = iter(values)
    return lambda account: next(remaining)


class CampaignCoreTests(unittest.TestCase):
    def test_campaigns_url_keeps_official_cache_behavior(self):
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

    def test_global_discovers_uid_then_refetches_with_risk_headers(self):
        calls = []
        risk_uids = []
        first = FakeResponse(200, {
            "uid": "uid-from-campaigns",
            "campaigns": [{"actionType": "VIEW_DETAILS", "claimStatus": "CLAIMABLE"}],
        })
        second = FakeResponse(200, {
            "uid": "uid-from-campaigns",
            "campaigns": [{"actionType": "CLAIM_BENEFIT", "claimStatus": "CLAIMABLE"}],
        })

        def request(method, url, headers=None, retries=3):
            calls.append(headers)
            return first if len(calls) == 1 else second

        def risky_headers(account, uid=""):
            risk_uids.append(uid)
            return {
                "authorization": "Bearer dt-current",
                "Cosy-MachineToken": "machine-token",
            }, None

        module = load_functions(
            "fetch_campaigns", "_fetch_campaigns_once", "auth_dead_response",
            "campaign_response_is_empty", "minimal_sash_headers", "first_text",
            "region_key", "campaign_uid_from_payload",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="10",
            SASH_USER_AGENT="Qoder",
            sash_headers=lambda token: {"authorization": "Bearer %s" % token},
            risky_sash_headers=risky_headers,
            request=request,
            refresh_account=lambda account: None,
            json_of=lambda response: response.payload,
        )
        account = {
            "region": "global",
            "base": "https://example.test",
            "access": "dt-current",
            "refresh": "drt-current",
            "uid": "configured-stale",
        }
        response, note = module["fetch_campaigns"](account)

        self.assertIs(second, response)
        self.assertIsNone(note)
        self.assertEqual("uid-from-campaigns", account["uid"])
        self.assertEqual(["uid-from-campaigns"], risk_uids)
        self.assertEqual(2, len(calls))
        self.assertNotIn("Cosy-MachineToken", calls[0])
        self.assertEqual("machine-token", calls[1]["Cosy-MachineToken"])

    def test_global_refresh_repeats_uid_discovery_sequence(self):
        calls = []
        responses = [
            FakeResponse(401, {"code": 401}),
            FakeResponse(200, {
                "uid": "uid-after-refresh",
                "campaigns": [],
            }),
            FakeResponse(200, {
                "uid": "uid-after-refresh",
                "campaigns": [{"actionType": "CLAIM_BENEFIT", "claimStatus": "CLAIMED"}],
            }),
        ]
        refreshes = {"count": 0}

        def request(method, url, headers=None, retries=3):
            calls.append(headers)
            return responses.pop(0)

        def refresh(account):
            refreshes["count"] += 1

        module = load_functions(
            "fetch_campaigns", "_fetch_campaigns_once", "auth_dead_response",
            "campaign_response_is_empty", "minimal_sash_headers", "first_text",
            "region_key", "campaign_uid_from_payload",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="10",
            SASH_USER_AGENT="Qoder",
            sash_headers=lambda token: {"authorization": "Bearer %s" % token},
            risky_sash_headers=lambda account, uid="": (
                {"authorization": "Bearer dt-current", "uid-header": uid}, None),
            request=request,
            refresh_account=refresh,
            json_of=lambda response: response.payload,
        )
        account = {
            "region": "global",
            "base": "https://example.test",
            "access": "dt-current",
            "refresh": "drt-current",
        }
        response, _note = module["fetch_campaigns"](account)

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, refreshes["count"])
        self.assertEqual(3, len(calls))
        self.assertEqual("uid-after-refresh", calls[2]["uid-header"])

    def test_global_empty_uid_does_not_generate_unbound_risk_identity(self):
        module = load_functions(
            "risk_identity", "first_text", "region_key",
            RISK_CACHE={},
            _env=lambda name: "",
            find_umid_component=lambda region: self.fail(
                "UID-less global accounts must not invoke UMID"),
        )
        values, note = module["risk_identity"]("global", "")
        self.assertIsNone(values)
        self.assertIn("UID", note)

    def test_global_manual_risk_env_does_not_require_uid(self):
        values = {
            "QODER_MACHINE_TOKEN": "manual-token",
            "QODER_MACHINE_CODE": "manual-code",
            "QODER_MACHINE_TYPE": "manual-type",
        }
        module = load_functions(
            "risk_identity", "first_text", "region_key",
            RISK_CACHE={},
            RISK_TTL=3000,
            time=time,
            _env=lambda name: values.get(name, ""),
            find_umid_component=lambda region: self.fail(
                "Manual risk credentials must not invoke UMID"),
        )
        identity, note = module["risk_identity"]("global", "")
        self.assertEqual("manual-token", identity["machineToken"])
        self.assertIsNone(note)

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
            ("global", {"uid": "uid-current", "campaigns": []}, 2),
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
                    "minimal_sash_headers", "first_text", "campaign_uid_from_payload",
                    CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
                    SASH_CLIENT_TYPE="10",
                    SASH_USER_AGENT="Qoder",
                    sash_headers=lambda token: {"authorization": "Bearer %s" % token},
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

    def test_quota_readback_sums_all_remaining_buckets(self):
        payload = {
            "userQuota": {"remaining": 100},
            "addOnQuota": {"remaining": 50},
            "dedicatedResourcePackages": [{"remaining": 25}, {"remaining": 5}],
            "orgResourcePackage": {"remaining": 20},
        }
        module = load_functions(
            "quota_total_remaining",
            QUOTA_USAGE_PATH="/api/v2/quota/usage",
            risky_sash_headers=lambda account, uid="": ({}, None),
            request=lambda method, url, headers=None, retries=1: FakeResponse(
                200, payload),
            json_of=lambda response: response.payload,
            amount_of=lambda value: float(value),
        )
        self.assertEqual(
            200.0,
            module["quota_total_remaining"](
                {"base": "https://example.test", "uid": "user-1"},
            ),
        )

    def test_claim_campaign_uses_minimal_headers_and_empty_body(self):
        captured = {}

        def request(method, url, headers=None, body=None, **_kwargs):
            captured.update({
                "method": method, "url": url, "headers": headers, "body": body,
            })
            return FakeResponse()

        module = load_functions(
            "claim_campaign", "minimal_sash_headers", "region_key",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="qoder", SASH_USER_AGENT="test-agent",
            request=request,
        )
        module["claim_campaign"](
            {"base": "https://example.test", "access": "access-token"}, "daily-1")

        self.assertEqual("POST", captured["method"])
        self.assertEqual(
            "https://example.test/sash/api/v1/me/campaigns/daily-1/claim",
            captured["url"])
        self.assertIsNone(captured["body"])
        self.assertEqual(
            {
                "authorization": "Bearer access-token",
                "cosy-clienttype": "qoder",
                "user-agent": "test-agent",
                "content-type": "application/json",
            },
            captured["headers"])

    def test_claim_campaign_global_uses_risk_headers_and_json_body(self):
        captured = {}

        def request(method, url, headers=None, body=None, **_kwargs):
            captured.update({"headers": headers, "body": body})
            return FakeResponse()

        module = load_functions(
            "claim_campaign", "region_key",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            minimal_sash_headers=lambda token: {"authorization": "Bearer %s" % token},
            risky_sash_headers=lambda account, uid="": (
                {"authorization": "Bearer %s" % account["access"],
                 "Cosy-MachineToken": "risk-token"}, None),
            request=request,
        )
        module["claim_campaign"](
            {"base": "https://example.test", "access": "access-token",
             "region": "global", "uid": "user-1"}, "daily-1")

        self.assertEqual({}, captured["body"])
        self.assertEqual("risk-token", captured["headers"]["Cosy-MachineToken"])

    def test_machine_hostname_explicit_override_and_hostname_fallback(self):
        module = load_functions(
            "machine_hostname",
            os=__import__("types").SimpleNamespace(environ={
                "QODER_MACHINE_HOSTNAME": "qoder-account2-actions",
                "HOSTNAME": "runner-dynamic-host",
            }),
            hashlib=__import__("hashlib"),
        )
        self.assertEqual("qoder-account2-actions", module["machine_hostname"]())

        module = load_functions(
            "machine_hostname",
            os=__import__("types").SimpleNamespace(
                environ={"HOSTNAME": "runner-dynamic-host"}),
            hashlib=__import__("hashlib"),
        )
        self.assertEqual("runner-dynamic-host", module["machine_hostname"]())

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
            "campaign_scope_is_limited", "campaign_title",
            "discover_pro_campaign",
            re=re,
            fetch_campaign_reward=lambda account, campaign_id: (
                {"kind": "CREDITS", "amount": 1800}
                if campaign_id == "hidden-pro" else
                {"kind": "CREDITS", "amount": 100}),
        )
        target, claimed, probes = module["discover_pro_campaign"]({}, rows)
        self.assertEqual("hidden-pro", target["campaignId"])
        self.assertIsNone(claimed)
        self.assertTrue(any("hidden-pro" in item for item in probes))

    def test_daily_pick_requires_semantic_daily_campaign(self):
        rows = [
            {"campaignId": "claimed-daily", "campaignKey": "act-daily",
             "actionType": "CLAIM_BENEFIT", "claimStatus": "CLAIMED",
             "title": "每日签到",
             "benefit": {"kind": "CREDITS", "amount": 100}},
            {"campaignId": "pro", "campaignKey": "pro-upgrade",
             "actionType": "CLAIM_BENEFIT", "claimStatus": "CLAIMABLE",
             "benefit": {"kind": "CREDITS", "amount": 1800}},
            {"campaignId": "legacy-empty-action", "campaignKey": "act-old",
             "actionType": "", "claimStatus": "CLAIMABLE",
             "title": "每日签到",
             "benefit": {"kind": "CREDITS", "amount": 100}},
            {"campaignId": "daily", "campaignKey": "act-daily",
             "actionType": "CLAIM_BENEFIT", "claimStatus": "CLAIMABLE",
             "title": "每日签到",
             "benefit": {
                 "kind": "CREDITS", "amount": 100,
                 "modelScope": {"modelSeries": {"key": "ALL_MODELS"}},
             }},
        ]
        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_title", "campaign_time_ms", "campaign_scope_is_limited",
            "campaign_is_daily", "campaign_is_active", "pick_daily_campaign",
            ONE_DAY_MS=24 * 60 * 60 * 1000,
            datetime=datetime, CN_TZ=None, math=__import__("math"), time=time,
        )
        target, claimed = module["pick_daily_campaign"](rows)
        self.assertEqual("daily", target["campaignId"])
        self.assertFalse(claimed)

    def test_daily_pick_returns_active_claimed_row_for_replay(self):
        now = time.time()
        rows = [{
            "campaignId": "batch-daily",
            "campaignKey": "act-batch-daily",
            "actionType": "CLAIM_BENEFIT",
            "claimStatus": "CLAIMED",
            "title": "每日签到",
            "benefit": {"kind": "CREDITS", "amount": 100},
            "startAt": now - 60,
            "endAt": now + 60,
        }]
        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_title", "campaign_time_ms", "campaign_scope_is_limited",
            "campaign_is_daily", "campaign_is_active", "pick_daily_campaign",
            ONE_DAY_MS=24 * 60 * 60 * 1000,
            datetime=datetime, CN_TZ=None, math=__import__("math"), time=time,
        )
        target, claimed = module["pick_daily_campaign"](rows)
        self.assertEqual("batch-daily", target["campaignId"])
        self.assertTrue(claimed)

    def test_daily_pick_ignores_expired_claimed_row(self):
        now = time.time()
        rows = [{
            "campaignId": "expired-daily",
            "campaignKey": "act-expired-daily",
            "actionType": "CLAIM_BENEFIT",
            "claimStatus": "CLAIMED",
            "title": "每日签到",
            "benefit": {"kind": "CREDITS", "amount": 100},
            "startAt": now - 120,
            "endAt": now - 60,
        }]
        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_title", "campaign_time_ms", "campaign_scope_is_limited",
            "campaign_is_daily", "campaign_is_active", "pick_daily_campaign",
            ONE_DAY_MS=24 * 60 * 60 * 1000,
            datetime=datetime, CN_TZ=None, math=__import__("math"), time=time,
        )
        target, claimed = module["pick_daily_campaign"](rows)
        self.assertIsNone(target)
        self.assertFalse(claimed)

    def test_daily_claimed_row_is_resubmitted_and_replay_is_neutral(self):
        row = {
            "campaignId": "batch-daily",
            "campaignKey": "act-batch-daily",
            "actionType": "CLAIM_BENEFIT",
            "claimStatus": "CLAIMED",
            "title": "每日签到",
            "benefit": {"kind": "CREDITS", "amount": 100},
        }
        calls = []

        def claim(account, campaign_id):
            calls.append(campaign_id)
            return FakeResponse(200, {"status": "CLAIMED", "replayed": True})

        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_title", "campaign_time_ms", "campaign_scope_is_limited",
            "campaign_is_daily", "campaign_is_active", "campaign_id_of",
            "pick_daily_campaign", "claim_response_verdict", "do_checkin",
            ONE_DAY_MS=24 * 60 * 60 * 1000,
            datetime=datetime, CN_TZ=None, math=__import__("math"), time=time,
            CLAIM_FAILURE_TEXT={},
            fetch_campaign_rows=lambda account: (
                [row], FakeResponse(), None, ""),
            daily_window_retry_enabled=lambda: False,
            daily_window_active=lambda: False,
            daily_before_reset=lambda: False,
            claim_campaign=claim,
            json_of=lambda response: response.payload,
        )
        ok, message = module["do_checkin"]({"region": "cn"})
        self.assertFalse(ok)
        self.assertEqual("今日已领取", message)
        self.assertEqual(["batch-daily"], calls)

    def test_daily_claimed_row_replay_false_reports_new_claim(self):
        row = {
            "campaignId": "batch-daily",
            "campaignKey": "act-batch-daily",
            "actionType": "CLAIM_BENEFIT",
            "claimStatus": "CLAIMED",
            "title": "每日签到",
            "benefit": {"kind": "CREDITS", "amount": 100},
        }
        calls = []

        def claim(account, campaign_id):
            calls.append(campaign_id)
            return FakeResponse(200, {"status": "CLAIMED", "replayed": False})

        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_title", "campaign_time_ms", "campaign_scope_is_limited",
            "campaign_is_daily", "campaign_is_active", "campaign_id_of",
            "pick_daily_campaign", "claim_response_verdict", "do_checkin",
            ONE_DAY_MS=24 * 60 * 60 * 1000,
            datetime=datetime, CN_TZ=None, math=__import__("math"),
            CLAIM_FAILURE_TEXT={},
            fetch_campaign_rows=lambda account: (
                [row], FakeResponse(), None, ""),
            daily_window_retry_enabled=lambda: False,
            daily_window_active=lambda: False,
            daily_before_reset=lambda: False,
            quota_total_remaining=_quota_sequence([100, 200]),
            claim_campaign=claim,
            json_of=lambda response: response.payload,
            time=type("Time", (), {
                "sleep": staticmethod(lambda seconds: None),
                "time": staticmethod(time.time),
            }),
        )
        ok, message = module["do_checkin"]({"region": "cn"})
        self.assertTrue(ok)
        self.assertIn("+100", message)
        self.assertIn("100 → 200", message)
        self.assertEqual(["batch-daily"], calls)

    def test_daily_claim_is_pending_without_quota_increase(self):
        row = {
            "campaignId": "daily-pending",
            "campaignKey": "act-daily-pending",
            "actionType": "CLAIM_BENEFIT",
            "claimStatus": "CLAIMABLE",
            "title": "每日签到",
            "benefit": {"kind": "CREDITS", "amount": 100},
        }
        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_title", "campaign_time_ms", "campaign_scope_is_limited",
            "campaign_is_daily", "campaign_is_active", "campaign_id_of",
            "pick_daily_campaign", "claim_response_verdict", "do_checkin",
            ONE_DAY_MS=24 * 60 * 60 * 1000,
            datetime=datetime, CN_TZ=None, math=__import__("math"),
            time=type("Time", (), {
                "sleep": staticmethod(lambda seconds: None),
                "time": staticmethod(time.time),
            }),
            CLAIM_FAILURE_TEXT={},
            fetch_campaign_rows=lambda account: (
                [row], FakeResponse(), None, ""),
            daily_window_retry_enabled=lambda: False,
            daily_window_active=lambda: False,
            daily_before_reset=lambda: False,
            quota_total_remaining=_quota_sequence([1200, 1200]),
            claim_campaign=lambda account, campaign_id: FakeResponse(
                200, {"status": "CLAIMED", "replayed": False}),
            json_of=lambda response: response.payload,
        )
        ok, message = module["do_checkin"]({"region": "cn"})
        self.assertFalse(ok)
        self.assertIn("待确认", message)
        self.assertIn("1200 → 1200", message)

    def test_daily_claim_is_pending_when_quota_readback_is_unavailable(self):
        row = {
            "campaignId": "daily-unreadable",
            "campaignKey": "act-daily-unreadable",
            "actionType": "CLAIM_BENEFIT",
            "claimStatus": "CLAIMABLE",
            "title": "每日签到",
            "benefit": {"kind": "CREDITS", "amount": 100},
        }
        module = load_functions(
            "first_text", "amount_of", "campaign_benefit",
            "campaign_title", "campaign_time_ms", "campaign_scope_is_limited",
            "campaign_is_daily", "campaign_is_active", "campaign_id_of",
            "pick_daily_campaign", "claim_response_verdict", "do_checkin",
            ONE_DAY_MS=24 * 60 * 60 * 1000,
            datetime=datetime, CN_TZ=None, math=__import__("math"),
            time=type("Time", (), {
                "sleep": staticmethod(lambda seconds: None),
                "time": staticmethod(time.time),
            }),
            CLAIM_FAILURE_TEXT={},
            fetch_campaign_rows=lambda account: (
                [row], FakeResponse(), None, ""),
            daily_window_retry_enabled=lambda: False,
            daily_window_active=lambda: False,
            daily_before_reset=lambda: False,
            quota_total_remaining=lambda account: None,
            claim_campaign=lambda account, campaign_id: FakeResponse(
                200, {"status": "CLAIMED", "replayed": False}),
            json_of=lambda response: response.payload,
        )
        ok, message = module["do_checkin"]({"region": "cn"})
        self.assertFalse(ok)
        self.assertIn("待确认", message)
        self.assertIn("100 credits", message)

    def test_before_daily_instance_stops_before_http(self):
        def unexpected(*args, **kwargs):
            raise AssertionError("before 10:00 must not request campaigns")

        module = load_functions(
            "do_checkin",
            daily_before_reset=lambda: True,
            fetch_campaign_rows=unexpected,
        )
        ok, message = module["do_checkin"]({"region": "cn"})
        self.assertFalse(ok)
        self.assertIn("10:00", message)
        self.assertIn("10:05", message)
        self.assertNotEqual("今日已领取", message)

    def test_daily_instance_reset_boundary(self):
        class FakeDateTime:
            current = None

            @classmethod
            def now(cls, tz=None):
                return cls.current

        module = load_functions(
            "daily_before_reset", datetime=FakeDateTime, CN_TZ=object())
        for hour, minute, expected in (
                (0, 0, True), (9, 59, True), (10, 0, False),
                (10, 5, False), (23, 59, False)):
            FakeDateTime.current = type(
                "Now", (), {"hour": hour, "minute": minute})()
            self.assertEqual(expected, module["daily_before_reset"]())

    def test_campaign_daily_classification_matrix(self):
        module = load_functions(
            "first_text", "amount_of", "campaign_benefit", "campaign_title",
            "campaign_time_ms", "campaign_scope_is_limited", "campaign_is_daily",
            ONE_DAY_MS=24 * 60 * 60 * 1000,
            datetime=datetime, CN_TZ=None, math=__import__("math"),
        )

        def row(**overrides):
            value = {
                "campaignId": "daily",
                "actionType": "CLAIM_BENEFIT",
                "title": "每日签到",
                "benefit": {
                    "kind": "CREDITS",
                    "amount": 100,
                    "validity": {"days": 30},
                    "modelScope": {"modelSeries": {"key": "ALL_MODELS"}},
                },
            }
            value.update(overrides)
            return value

        scoped = row()
        scoped["benefit"] = {
            "kind": "CREDITS",
            "amount": 100,
            "validity": {"days": 30},
            "modelScope": {"modelSeries": {"key": "SONUS"}},
        }
        empty_scope = row()
        empty_scope["benefit"] = {
            "kind": "CREDITS", "amount": 100,
            "validity": {"days": 30}, "modelScope": {},
        }
        non_credit = row()
        non_credit["benefit"] = {
            "kind": "POINTS", "amount": 100,
            "validity": {"days": 30},
        }
        start = 1_790_000_000
        legacy = row(title="", startAt=start, endAt=start + 86_400)
        too_long = row(title="", startAt=start, endAt=start + 86_401)
        wrong_amount = row(title="", startAt=start, endAt=start + 86_400)
        wrong_amount["benefit"] = {
            "kind": "CREDITS", "amount": 101,
            "validity": {"days": 30},
        }
        wrong_days = row(title="", startAt=start, endAt=start + 86_400)
        wrong_days["benefit"] = {
            "kind": "CREDITS", "amount": 100,
            "validity": {"days": 29},
        }
        placement = row(title="")
        placement["placements"] = [{
            "type": "POPUP",
            "content": {"zh": {"title": "每日签到"}, "en": {"title": "Daily"}},
        }]

        cases = [
            ("zh_daily", row(), True),
            ("en_daily", row(title="Daily check-in"), True),
            ("every_day", row(title="Every Day"), True),
            ("placement", placement, True),
            ("sonus", row(title="Sonus daily"), False),
            ("sota", row(title="SOTA daily"), False),
            ("scoped", scoped, False),
            ("empty_scope", empty_scope, True),
            ("non_credit", non_credit, False),
            ("wrong_action", row(actionType=""), False),
            ("empty_id", row(campaignId="  "), False),
            ("legacy", legacy, True),
            ("too_long", too_long, False),
            ("wrong_amount", wrong_amount, False),
            ("wrong_days", wrong_days, False),
            ("not_daily_high_amount", row(title="限时福利", benefit={
                "kind": "CREDITS", "amount": 1800,
                "validity": {"days": 30},
            }), False),
            ("substring_risk", row(title="Not daily"), True),
        ]
        for name, value, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(expected, module["campaign_is_daily"](value))

    def test_campaign_rows_require_unique_nonempty_ids(self):
        module = load_functions("validate_campaign_rows")
        self.assertEqual("", module["validate_campaign_rows"]([
            {"campaignId": "one"}, {"campaignId": "two"},
        ]))
        self.assertIn("格式异常", module["validate_campaign_rows"]([
            {"campaignId": "one"}, {"title": "missing"},
        ]))
        self.assertIn("格式异常", module["validate_campaign_rows"]([
            {"campaignId": "one"}, "not-an-object",
        ]))
        self.assertIn("重复", module["validate_campaign_rows"]([
            {"campaignId": "one"}, {"campaignId": "one"},
        ]))

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
            "title": "每日签到",
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
            "campaign_title", "campaign_time_ms", "campaign_scope_is_limited",
            "campaign_is_daily", "campaign_is_active", "campaign_id_of",
            "pick_daily_campaign", "do_checkin",
            ONE_DAY_MS=24 * 60 * 60 * 1000,
            datetime=datetime, CN_TZ=None, math=__import__("math"),
            fetch_campaign_rows=fetch_rows,
            daily_window_retry_enabled=lambda: True,
            daily_window_active=lambda: True,
            daily_before_reset=lambda: False,
            _env=lambda name: {"QODER_WINDOW_RETRY_MAX": "2",
                               "QODER_WINDOW_RETRY_GAP": "1"}.get(name, ""),
            log=lambda message: None,
            time=type("Time", (), {
                "sleep": staticmethod(sleep),
                "time": staticmethod(time.time),
            }),
            claim_campaign=lambda account, campaign_id: FakeResponse(
                200, {"status": "CLAIMED"}),
            claim_response_verdict=lambda response: ("claimed", 100, "领取成功"),
            quota_total_remaining=_quota_sequence([0, 100]),
            json_of=lambda response: response.payload,
        )
        ok, message = module["do_checkin"]({"region": "cn"})
        self.assertTrue(ok)
        self.assertIn("+100", message)
        self.assertEqual(2, calls["fetch"])
        self.assertEqual(2, calls["sleep"])

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
            UMID_CLI_RUNTIME_ENV={"cn": 0, "global": 4},
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

    def test_global_cli_and_data_components_use_singapore_env(self):
        fake_os = type("FakeOS", (), {
            "path": type("FakePath", (), {
                "isfile": staticmethod(
                    lambda path: path.endswith("runtime-info")),
                "isdir": staticmethod(
                    lambda path: path.endswith("umid-linux")),
                "join": staticmethod(os.path.join),
            })(),
            "listdir": staticmethod(lambda path: ["umid-linux"]),
        })()
        fake_sys = type("FakeSys", (), {"platform": "linux"})()
        module = load_functions(
            "region_key", "find_umid_component",
            _env=lambda name: "",
            os=fake_os,
            sys=fake_sys,
            UMID_RUNTIME_ENV={"cn": 0, "global": 3},
            UMID_CLI_RUNTIME_ENV={"cn": 0, "global": 4},
            UMID_OVERRIDE_ENV={
                "cn": "QODERCN_RUNTIME_INFO",
                "global": "QODER_RUNTIME_INFO",
            },
            resource_dirs=lambda region, names: [],
            region_names=lambda region: (region,),
            cli_runtime_cache_dirs=lambda region: ["/home/test/.qoder"],
            umid_directory=lambda region: "/data/qoder-umid/global",
        )
        cli = module["find_umid_component"]("global")
        self.assertEqual(4, cli[1])
        self.assertEqual("cli", cli[2])
        self.assertTrue(cli[0].endswith("runtime-info"))

        module["cli_runtime_cache_dirs"] = lambda region: []
        data = module["find_umid_component"]("global")
        self.assertEqual(4, data[1])
        self.assertEqual("data", data[2])
        self.assertTrue(data[0].endswith("runtime-info"))

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
            daily_before_reset=lambda: False,
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
            "campaign_uid_from_payload", "quota_cooldown", "region_key",
            CAMPAIGNS_PATH="/sash/api/v1/me/campaigns",
            SASH_CLIENT_TYPE="10",
            SASH_USER_AGENT="Qoder",
            sash_headers=lambda token: {"authorization": "Bearer %s" % token},
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
