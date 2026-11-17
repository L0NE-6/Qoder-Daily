"""Login transport regressions with fake requests sessions."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qoder_login as login


class LoginNetworkTests(unittest.TestCase):
    def test_explicit_proxy_is_forwarded_to_requests(self):
        response = object()
        session = Mock()
        session.request.return_value = response
        with patch.dict(os.environ, {"QODER_PROXY": "http://127.0.0.1:7890"}), \
                patch.object(login.requests, "Session", return_value=session):
            result = login.request("GET", "https://openapi.qoder.sh/test")

        self.assertIs(response, result)
        self.assertTrue(session.trust_env)
        self.assertEqual(
            {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"},
            session.request.call_args.kwargs["proxies"],
        )

    def test_environment_proxy_support_is_enabled(self):
        response = object()
        session = Mock()
        session.request.return_value = response
        env = {"HTTPS_PROXY": "http://proxy-for-test:8080"}
        with patch.dict(os.environ, env, clear=True), \
                patch.object(login.requests, "Session", return_value=session):
            login.request("GET", "https://openapi.qoder.sh/test")

        self.assertTrue(session.trust_env)
        self.assertNotIn("proxies", session.request.call_args.kwargs)

    def test_connection_reset_reports_proxy_guidance(self):
        session = Mock()
        session.request.side_effect = requests.ConnectionError(
            "ConnectionResetError(10054, connection reset by peer)")
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(login.requests, "Session", return_value=session), \
                patch.object(login.time, "sleep"):
            with self.assertRaises(login.NetworkRequestFailure) as raised:
                login.request("GET", "https://openapi.qoder.sh/test")

        self.assertIn("QODER_PROXY", str(raised.exception))
        self.assertEqual(3, session.request.call_count)


if __name__ == "__main__":
    unittest.main()
