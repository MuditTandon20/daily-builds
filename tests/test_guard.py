from datetime import datetime, timezone
import unittest
from unittest.mock import patch
import urllib.error

from daily_builds import IST, audit, contribution_count, day_start, report_path, run


class GuardTests(unittest.TestCase):
    def test_india_day_boundary(self):
        now = datetime(2026, 11, 15, 19, 0, tzinfo=timezone.utc)
        self.assertEqual(str(day_start(now).date()), '2026-11-16')
        self.assertEqual(report_path(now), 'reports/2026-11-16.json')

    def test_private_names_never_published(self):
        self.assertEqual(audit([{'private': True, 'full_name': 'owner/secret'}]), [])

    def test_graphql_errors_fail_closed(self):
        class API:
            def request(self, *args):
                return {'errors': [{'message': 'unavailable'}]}
        with self.assertRaises(RuntimeError):
            contribution_count(API(), datetime.now(IST))

    def test_existing_contribution_skips_all_writes(self):
        class API:
            def request(self, path, *args, **kwargs):
                if path == '/user':
                    return {'login': 'MuditTandon20'}
                if path == '/graphql':
                    return {'data': {'user': {'contributionsCollection': {
                        'totalCommitContributions': 1, 'restrictedContributionsCount': 0}}}}
                raise AssertionError('Unexpected API call: ' + path)
        run(API(), datetime(2026, 11, 15, 23, 30, tzinfo=IST), write=True)

    def test_early_write_does_not_access_github(self):
        run(None, datetime(2026, 11, 15, 10, 0, tzinfo=IST), write=True)

    def test_existing_report_skips_write(self):
        class API:
            def request(self, path, *args, **kwargs):
                if path == '/user':
                    return {'login': 'MuditTandon20'}
                if path == '/graphql':
                    return {'data': {'user': {'contributionsCollection': {
                        'totalCommitContributions': 0, 'restrictedContributionsCount': 0}}}}
                if '/contents/reports/' in path:
                    return {'sha': 'existing'}
                raise AssertionError('Unexpected API call: ' + path)
        run(API(), datetime(2026, 11, 15, 23, 30, tzinfo=IST), write=True)

    def test_inactive_day_creates_one_attributed_report(self):
        now = datetime(2026, 11, 15, 23, 30, tzinfo=IST)
        writes = []
        class API:
            def request(self, path, data=None, method=None):
                if method == 'PUT':
                    writes.append(data)
                    return {'commit': {'html_url': 'https://github.com/example/commit/test'}}
                if path == '/user':
                    return {'login': 'MuditTandon20', 'id': 160775407, 'name': 'Mudit'}
                if path == '/graphql':
                    return {'data': {'user': {'contributionsCollection': {
                        'totalCommitContributions': 0, 'restrictedContributionsCount': 0}}}}
                if '/contents/reports/' in path:
                    raise urllib.error.HTTPError(path, 404, 'Not Found', None, None)
                if path.startswith('/users/'):
                    return []
                raise AssertionError(path)
        with patch('daily_builds.datetime') as clock:
            clock.combine = datetime.combine
            clock.now.return_value = now
            run(API(), now, write=True)
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]['author']['email'], '160775407+MuditTandon20@users.noreply.github.com')
        self.assertTrue(writes[0]['author']['date'].endswith('+05:30'))


if __name__ == '__main__':
    unittest.main()
