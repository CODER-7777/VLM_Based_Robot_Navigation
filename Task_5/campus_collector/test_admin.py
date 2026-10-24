"""Admin authorization, assignment concurrency and live-worker protection tests."""
import json
from pathlib import Path
import secrets
import unittest
from types import SimpleNamespace

import test_gateway
from admin_tools import StudyCatalog


class AdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = test_gateway.GatewayTests
        cls.base.setUpClass()
        cls.server = cls.base.server
        cls.root = Path(cls.base.temp.name)
        template = Path(cls.base.cfg['template_root'])
        (template / 'presentation_cases.py').write_bytes((Path(__file__).parent / 'template/presentation_cases.py').read_bytes())
        memories = {'m': {'who': 'Fixture speaker', 'said': 'Synthetic place memory.', 'images': ['fixture']}}
        cases = []
        for key, length in [('fixture_long', 41), ('fixture_short', 12)]:
            cases.append({'episode_key': key, 'title': key, 'index': len(cases) + 1, 'group': 'fixture',
                          'category_level3': 'fixture', 'route': {'scene': 'synthetic', 'start_position': [0, 0, 0],
                          'start_rotation_xyzw': [0, 0, 0, 1], 'reference_path': [[0, 0, 0], [length, 0, 0]],
                          'goals': [{'position': [length, 0, 0]}]},
                          'levels': {'3': {'now': 'Synthetic time', 'inputs': {'multiple_memories': {'primary':
                          {'memory_ids': ['m'], 'evaluator_rules': {'goal_memory_id': 'm'}, 'assigned_task': 'Synthetic ' + key}}}}}})
        data = {'cases': cases, 'memories': memories, 'images': {'fixture': {'data_url': 'synthetic-fixture'}}}
        source = cls.root / 'source.html'
        source.write_text('<script id="presentation-data" type="application/json">' + json.dumps(data) + '</script>')
        (template / 'collection_selection.json').write_text(json.dumps({'episode_keys': ['fixture_long'], 'minimum_reference_length_m_exclusive': 40}))
        scenes = cls.root / 'scenes/synthetic'
        scenes.mkdir(parents=True)
        (scenes / 'synthetic.glb').write_bytes(b'not-a-real-scene-test-fixture')
        cls.base.cfg.update(presentation_source=str(source), scene_root=str(scenes.parent))
        cls.server.admin.catalog = StudyCatalog(cls.base.cfg)
        cls.server.admin.store.set_role('alice', 'admin')

    @classmethod
    def tearDownClass(cls):
        cls.base.tearDownClass()

    def call(self, action, data, user='alice', **kwargs):
        return self.base.request('/api/admin/' + action, 'POST', json.dumps(data).encode(), user=user, **kwargs)

    def target(self):
        username = 'fixture_' + secrets.token_hex(4)
        password = secrets.token_urlsafe(20)
        self.server.accounts.add(username, password)
        self.base.tokens[username] = 'task5_session=' + self.server.accounts.login(username, 3600)
        return username, password

    def test_private_routes_and_assets_require_admin(self):
        for path in ['/admin', '/admin/', '/admin/app.js', '/admin/style.css', '/api/admin/state', '/api/admin/catalog.csv', '/api/admin/catalog.md']:
            anonymous = self.base.request(path)
            self.assertEqual(anonymous[0], 303 if path in ['/admin', '/admin/'] else 401)
            if path in ['/admin', '/admin/']:
                self.assertEqual(anonymous[1]['Location'], '/login')
            response = self.base.request(path, user='bob')
            self.assertEqual(response[0], 403)
            self.assertNotIn(b'fixture_long', response[2])
        self.assertEqual(self.base.request('/admin', user='alice')[0], 200)
        status, _, body = self.base.request('/api/admin/state', user='alice')
        self.assertEqual(status, 200)
        state = json.loads(body)
        self.assertEqual(len(state['instructions']), 2)
        self.assertEqual(next(u for u in state['users'] if u['username'] == 'alice')['episode_keys'], ['fixture_long', 'fixture_short'])
        self.assertNotIn('password', body.decode())
        self.assertNotIn('digest', body.decode())
        self.assertEqual(self.base.request('/api/state')[0], 401)
        self.assertEqual(self.call('create-user', {'username': 'blocked'}, user='bob')[0], 403)

    def test_create_account_secret_once_and_no_role_escalation(self):
        username = 'new_' + secrets.token_hex(4)
        status, _, body = self.call('create-user', {'username': username, 'episode_keys': ['fixture_short']})
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertTrue(self.server.accounts.authenticate(username, result['password']))
        self.assertEqual(self.server.admin.store.role(username), 'contributor')
        self.assertEqual(self.server.admin.effective(username), ['fixture_short'])
        self.assertNotIn(result['password'].encode(), self.base.request('/api/admin/state', user='alice')[2])
        self.assertEqual(self.call('create-user', {'username': username, 'password': 'replacement-not-permitted'})[0], 409)
        self.assertTrue(self.server.accounts.authenticate(username, result['password']))
        self.assertEqual(self.call('create-user', {'username': 'elevated', 'role': 'admin'})[0], 400)
        self.assertEqual(self.call('create-user', {'username': 'malformed', 'password': 123456789012})[0], 400)
        self.assertEqual(self.call('create-user', {'username': 'cross_origin'}, origin='https://untrusted.example')[0], 403)

    def test_invalid_keys_and_stale_revision_do_not_change_assignments(self):
        username, _ = self.target()
        self.assertEqual(self.call('assign', {'username': username, 'episode_keys': ['unknown'], 'revision': 0})[0], 400)
        self.assertEqual(self.call('assign', {'username': username, 'episode_keys': [['nested']], 'revision': 0})[0], 400)
        self.assertEqual(self.call('assign', {'username': username, 'episode_keys': ['fixture_short'], 'revision': 0})[0], 200)
        self.assertEqual(self.call('assign', {'username': username, 'episode_keys': ['fixture_long'], 'revision': 0})[0], 409)
        self.assertEqual(self.server.admin.store.assignment(username)['keys'], ['fixture_short'])
        self.assertEqual(self.call('assign', {'username': username, 'episode_keys': [], 'revision': 1})[0], 200)
        self.assertEqual(self.base.request('/api/state', user=username)[0], 403)

    def test_recording_and_upload_lease_protect_assignment(self):
        username, _ = self.target()
        self.base.ready(username)
        self.base.request('/api/start', 'POST', b'{}', user=username)
        self.assertEqual(self.call('assign', {'username': username, 'episode_keys': ['fixture_short'], 'revision': 0})[0], 409)
        self.assertIsNone(self.server.admin.store.assignment(username))
        self.assertEqual(self.call('reset-password', {'username': username})[0], 409)
        self.assertEqual(self.call('set-enabled', {'username': username, 'enabled': False})[0], 409)
        self.base.request('/api/reset', 'POST', b'{}', user=username)
        worker = self.server.pool.workers[username]
        worker.inflight = 1
        try:
            self.assertEqual(self.call('assign', {'username': username, 'episode_keys': ['fixture_short'], 'revision': 0})[0], 409)
        finally:
            worker.inflight = 0
        self.assertEqual(self.call('assign', {'username': username, 'episode_keys': ['fixture_short'], 'revision': 0})[0], 200)
        self.assertNotIn(username, self.server.pool.workers)

    def test_reset_disable_enable_preserve_recordings(self):
        username, password = self.target()
        recording = Path(self.base.cfg['data_root']) / 'contributors' / username / 'sessions' / username / 'saved/manifest.json'
        recording.parent.mkdir(parents=True)
        recording.write_text('{"synthetic_recording":true}')
        self.call('assign', {'username': username, 'episode_keys': ['fixture_short'], 'revision': 0})
        status, _, body = self.call('reset-password', {'username': username})
        self.assertEqual(status, 200)
        new = json.loads(body)['password']
        self.assertFalse(self.server.accounts.authenticate(username, password))
        self.assertTrue(self.server.accounts.authenticate(username, new))
        self.assertEqual(self.base.request('/auth/me', user=username)[0], 401)
        self.assertEqual(self.call('set-enabled', {'username': username, 'enabled': False})[0], 200)
        self.assertFalse(self.server.accounts.authenticate(username, new))
        self.assertEqual(self.call('set-enabled', {'username': username, 'enabled': True})[0], 200)
        self.assertTrue(self.server.accounts.authenticate(username, new))
        self.assertEqual(recording.read_text(), '{"synthetic_recording":true}')
        self.assertEqual(self.server.admin.store.assignment(username)['keys'], ['fixture_short'])

    def test_admin_roles_and_export_are_protected(self):
        self.assertEqual(self.call('assign', {'username': 'alice', 'episode_keys': [], 'revision': 0})[0], 400)
        self.assertEqual(self.call('set-enabled', {'username': 'alice', 'enabled': False})[0], 400)
        with self.assertRaises(ValueError):
            self.server.admin.store.set_role('alice', 'contributor')
        csv_response = self.base.request('/api/admin/catalog.csv', user='alice')
        self.assertEqual(csv_response[0], 200)
        self.assertIn(b'source_folder', csv_response[2])
        self.assertIn(b'fixture_short', csv_response[2])
        md = self.base.request('/api/admin/catalog.md', user='alice')
        self.assertEqual(md[0], 200)
        self.assertIn(b'Administrator-only', md[2])

    def test_worker_selection_contains_only_own_assignment(self):
        raw = {'episode_keys': ['fixture_long'], 'minimum_reference_length_m_exclusive': 40,
               'account_episode_keys': {'alice': ['fixture_short'], 'bob': ['fixture_long']}}
        owner = self.server.admin.worker_selection('alice', raw)
        self.assertEqual(owner['account_episode_keys'], {'alice': ['fixture_long', 'fixture_short']})
        contributor = self.server.admin.worker_selection('bob', raw)
        self.assertEqual(contributor['account_episode_keys'], {'bob': ['fixture_long']})
        self.assertEqual(raw['account_episode_keys']['alice'], ['fixture_short'])

    def test_missing_source_asset_blocks_contributor_assignment_only(self):
        username, _ = self.target()
        catalog = self.server.admin.catalog
        catalog.refresh()
        row = next(r for r in catalog.rows if r['key'] == 'fixture_short')
        original = row['assignable']
        row['assignable'] = False
        try:
            self.assertIn('fixture_short', self.server.admin.effective('alice'))
            self.assertEqual(self.call('assign', {'username': username, 'episode_keys': ['fixture_short'], 'revision': 0})[0], 400)
            self.assertIsNone(self.server.admin.store.assignment(username))
        finally:
            row['assignable'] = original


if __name__ == '__main__':
    unittest.main()
