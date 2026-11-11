"""Token rotation regressions: fake credentials and HTTP mocks only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qoder_daily as daily


class TokenStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store_path = Path(self.temp.name) / 'qoder_tokens.json'
        self.store_patch = patch.object(daily, 'STORE_FILE', str(self.store_path))
        self.store_patch.start()
        self.addCleanup(self.store_patch.stop)
        self.log_patch = patch.object(daily, 'log')
        self.log_patch.start()
        self.addCleanup(self.log_patch.stop)

    def account(self, name='primary'):
        # These deliberately fake values never reach an actual network request.
        return daily.parse_accounts('%s|dt-%s-original|drt-%s-original' % (name, name, name))[0]

    def refresh(self, account, access, refresh=None):
        payload = {'device_token': access}
        if refresh is not None:
            payload['refresh_token'] = refresh
        response = Mock(status_code=200)
        response.json.return_value = payload
        with patch.object(daily, 'request', return_value=response) as request:
            daily.refresh_account(account)
        self.assertTrue(request.call_args.args[1].endswith(daily.DEVICE_REFRESH_PATH))

    def response(self, status, payload, text=None):
        response = Mock(status_code=status)
        response.json.return_value = payload
        response.text = text if text is not None else json.dumps(payload)
        return response

    def test_unchanged_environment_restores_after_two_rotations(self):
        for generation in (1, 2):
            current = self.account()
            restored = daily.apply_store(current)
            if generation == 2:
                self.assertTrue(restored, 'unchanged Secret must locate the rotated credential')
                self.assertEqual(current['refresh'], 'drt-rotated-1')
            self.refresh(current, 'dt-rotated-%d' % generation, 'drt-rotated-%d' % generation)
        next_run = self.account()
        self.assertTrue(daily.apply_store(next_run))
        self.assertEqual(next_run['access'], 'dt-rotated-2')
        self.assertEqual(next_run['refresh'], 'drt-rotated-2')

    def test_refresh_without_prior_apply_store_keeps_original_alias(self):
        self.refresh(self.account(), 'dt-new', 'drt-new')
        next_run = self.account()
        self.assertTrue(daily.apply_store(next_run))
        self.assertEqual(next_run['refresh'], 'drt-new')

    def test_unchanged_refresh_token_still_works(self):
        current = self.account()
        daily.apply_store(current)
        self.refresh(current, 'dt-new')
        next_run = self.account()
        self.assertTrue(daily.apply_store(next_run))
        self.assertEqual(next_run['access'], 'dt-new')
        self.assertEqual(next_run['refresh'], 'drt-primary-original')

    def test_rotating_accounts_remain_isolated(self):
        for name in ('primary', 'secondary'):
            current = self.account(name)
            daily.apply_store(current)
            self.refresh(current, 'dt-%s-new' % name, 'drt-%s-new' % name)
        for name in ('primary', 'secondary'):
            next_run = self.account(name)
            self.assertTrue(daily.apply_store(next_run))
            self.assertEqual(next_run['access'], 'dt-%s-new' % name)

    def test_legacy_store_entry_remains_readable(self):
        current = self.account()
        self.store_path.write_text(json.dumps({daily.token_fp(current['refresh']): {
            'access': 'dt-legacy', 'refresh': 'drt-legacy', 'note': 'old format', 'at': 1}}), encoding='utf-8')
        self.assertTrue(daily.apply_store(current))
        self.assertEqual(current['refresh'], 'drt-legacy')

    def test_fresh_runner_requires_restoring_the_state_file(self):
        current = self.account()
        daily.apply_store(current)
        # Keep the refresh token unchanged to isolate runner state loss from
        # the independent rotating-token index regression.
        self.refresh(current, 'dt-new-runner')
        saved_state = self.store_path.read_bytes()
        clean_runner_path = Path(self.temp.name) / 'clean-runner' / 'qoder_tokens.json'
        clean_runner_path.parent.mkdir()
        with patch.object(daily, 'STORE_FILE', str(clean_runner_path)):
            self.assertFalse(daily.apply_store(self.account()))
            clean_runner_path.write_bytes(saved_state)
            restored = self.account()
            self.assertTrue(daily.apply_store(restored))
            self.assertEqual(restored['access'], 'dt-new-runner')

    def test_original_credentials_are_not_persisted_as_alias_values(self):
        current = self.account()
        original_access, original_refresh = current['access'], current['refresh']
        daily.apply_store(current)
        self.refresh(current, 'dt-new', 'drt-new')
        contents = self.store_path.read_text(encoding='utf-8')
        self.assertNotIn(original_access, contents)
        self.assertNotIn(original_refresh, contents)
        self.assertTrue(all(len(key) == 16 for key in json.loads(contents)))

    def test_drt_http_415_retries_once_with_form_and_persists_rotation(self):
        current = self.account()
        responses = [
            self.response(415, {'rawMessage': 'Unsupported Media Type'}),
            self.response(200, {
                'device_token': 'dt-form',
                'refresh_token': 'drt-form',
            }),
        ]
        with patch.object(daily, 'request', side_effect=responses) as request:
            self.assertTrue(daily.refresh_account(current))

        self.assertEqual(2, request.call_count)
        first, second = request.call_args_list
        self.assertEqual(
            {'refresh_token': 'drt-primary-original'}, first.kwargs['body'])
        self.assertNotIn('body', second.kwargs)
        self.assertEqual(
            {'refresh_token': 'drt-primary-original'}, second.kwargs['form'])
        self.assertEqual(
            'application/x-www-form-urlencoded',
            second.kwargs['headers']['Content-Type'])
        self.assertEqual('dt-form', current['access'])
        self.assertEqual('drt-form', current['refresh'])

        next_run = self.account()
        self.assertTrue(daily.apply_store(next_run))
        self.assertEqual('dt-form', next_run['access'])
        self.assertEqual('drt-form', next_run['refresh'])

    def test_drt_wrapped_http_400_code_415_retries_with_form(self):
        current = self.account()
        wrapped = {
            'errorCode': 'BadRequest',
            'errorMessage': 'Bad request',
            'rawMessage': 'code=415, message=Unsupported Media Type',
        }
        responses = [
            self.response(400, wrapped),
            self.response(200, {'device_token': 'dt-wrapped'}),
        ]
        with patch.object(daily, 'request', side_effect=responses) as request:
            self.assertTrue(daily.refresh_account(current))

        self.assertEqual(2, request.call_count)
        self.assertEqual(
            {'refresh_token': 'drt-primary-original'},
            request.call_args_list[1].kwargs['form'])
        self.assertEqual('dt-wrapped', current['access'])

    def test_plain_http_400_does_not_switch_to_form(self):
        current = self.account()
        failure = self.response(400, {'errorCode': 'BadRequest'})
        with patch.object(daily, 'request', return_value=failure) as request:
            with self.assertRaisesRegex(RuntimeError, 'HTTP 400'):
                daily.refresh_account(current)

        self.assertEqual(1, request.call_count)
        self.assertEqual('dt-primary-original', current['access'])
        self.assertEqual('drt-primary-original', current['refresh'])

    def test_jrt_http_415_does_not_use_unproven_form_shape(self):
        current = self.account()
        current['refresh'] = 'jrt-primary-original'
        failure = self.response(415, {'rawMessage': 'Unsupported Media Type'})
        with patch.object(daily, 'request', return_value=failure) as request:
            with self.assertRaisesRegex(RuntimeError, 'HTTP 415'):
                daily.refresh_account(current)

        self.assertEqual(1, request.call_count)
        self.assertTrue(request.call_args.args[1].endswith(daily.JOB_REFRESH_PATH))
        self.assertEqual('dt-primary-original', current['access'])

    def test_refresh_persist_failure_is_not_reported_as_success(self):
        current = self.account()
        success = self.response(200, {
            'device_token': 'dt-new',
            'refresh_token': 'drt-new',
        })
        with patch.object(daily, 'request', return_value=success), \
                patch.object(daily, 'persist', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(RuntimeError, '状态写入失败'):
                daily.refresh_account(current)

        self.assertEqual('dt-primary-original', current['access'])
        self.assertEqual('drt-primary-original', current['refresh'])

    def test_atomic_store_failure_preserves_existing_file(self):
        self.store_path.write_text('{"old": true}', encoding='utf-8')
        with patch.object(daily.os, 'replace', side_effect=OSError('replace failed')):
            with self.assertRaisesRegex(OSError, 'replace failed'):
                daily.save_store({'new': True})
        self.assertEqual('{"old": true}', self.store_path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
