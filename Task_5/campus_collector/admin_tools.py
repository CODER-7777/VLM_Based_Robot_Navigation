"""Private study administration; no participant-facing assignment roster."""
from __future__ import annotations
import csv
import datetime as dt
import importlib.util
import io
import json
import math
from pathlib import Path
import secrets
import sqlite3
import threading


class AdminError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class AdminStore:
    def __init__(self, accounts):
        self.accounts = accounts
        with accounts.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS study_roles(username TEXT PRIMARY KEY,role TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS study_assignments(
                    username TEXT PRIMARY KEY,episode_keys TEXT NOT NULL,revision INTEGER NOT NULL,
                    updated_by TEXT NOT NULL,updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS study_admin_audit(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,
                    target TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL);
            ''')

    def role(self, username):
        if not username:
            return None
        with self.accounts.connect() as db:
            row = db.execute('SELECT COALESCE(r.role,\'contributor\') FROM users u '
                             'LEFT JOIN study_roles r ON r.username=u.username '
                             'WHERE u.username=? AND u.enabled=1', (username,)).fetchone()
        return row[0] if row else None

    @staticmethod
    def audit(db, actor, action, target, details):
        db.execute('INSERT INTO study_admin_audit(actor,action,target,details,created_at) VALUES(?,?,?,?,?)',
                   (actor, action, target, json.dumps(details), now()))

    def set_role(self, username, role):
        if role not in {'admin', 'contributor'}:
            raise ValueError('Unknown study role.')
        with self.accounts.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM users WHERE username=? AND enabled=1', (username,)).fetchone():
                raise ValueError('Create/enable the account before assigning its role.')
            if role == 'contributor' and self.role(username) == 'admin':
                total = db.execute('SELECT COUNT(*) FROM study_roles r JOIN users u USING(username) '
                                   'WHERE role=\'admin\' AND enabled=1').fetchone()[0]
                if total <= 1:
                    raise ValueError('Keep at least one enabled administrator.')
            db.execute('INSERT INTO study_roles VALUES(?,?) ON CONFLICT(username) DO UPDATE SET role=excluded.role',
                       (username, role))
            self.audit(db, 'server_cli', 'set_role', username, {'role': role})

    def assignment(self, username):
        with self.accounts.connect() as db:
            row = db.execute('SELECT episode_keys,revision,updated_by,updated_at FROM study_assignments '
                             'WHERE username=?', (username,)).fetchone()
        return {'keys': json.loads(row[0]), 'revision': row[1], 'updated_by': row[2], 'updated_at': row[3]} if row else None

    def create_user(self, username, password, keys, actor):
        self.accounts.validate(username, password)
        salt = secrets.token_bytes(16)
        digest = self.accounts.digest(password, salt)
        with self.accounts.connect() as db:
            try:
                db.execute('INSERT INTO users(username,salt,digest) VALUES(?,?,?)', (username, salt, digest))
            except sqlite3.IntegrityError:
                raise AdminError(409, 'That account already exists; no password or recordings were changed.') from None
            db.execute('INSERT INTO study_assignments VALUES(?,?,1,?,?)',
                       (username, json.dumps(keys), actor, now()))
            self.audit(db, actor, 'create_user', username, {'episode_keys': keys})

    def save_assignment(self, username, keys, revision, actor):
        with self.accounts.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone():
                raise AdminError(404, 'Account not found.')
            old = db.execute('SELECT episode_keys,revision FROM study_assignments WHERE username=?', (username,)).fetchone()
            current = old[1] if old else 0
            if revision != current:
                raise AdminError(409, 'Another administrator changed this assignment. Refresh before saving.')
            db.execute('INSERT INTO study_assignments VALUES(?,?,?,?,?) ON CONFLICT(username) DO UPDATE SET '
                       'episode_keys=excluded.episode_keys,revision=excluded.revision,updated_by=excluded.updated_by,updated_at=excluded.updated_at',
                       (username, json.dumps(keys), current + 1, actor, now()))
            self.audit(db, actor, 'assign_tasks', username, {'before': json.loads(old[0]) if old else None, 'after': keys})
        return current + 1

    def list_users(self):
        with self.accounts.connect() as db:
            rows = db.execute('SELECT u.username,u.enabled,COALESCE(r.role,\'contributor\') FROM users u '
                              'LEFT JOIN study_roles r ON r.username=u.username ORDER BY u.username').fetchall()
        return [{'username': row[0], 'enabled': bool(row[1]), 'role': row[2]} for row in rows]

    def recent_audit(self):
        with self.accounts.connect() as db:
            rows = db.execute('SELECT id,actor,action,target,details,created_at FROM study_admin_audit ORDER BY id DESC LIMIT 60').fetchall()
        return [dict(zip(['id', 'actor', 'action', 'target', 'details', 'created_at'],
                         [r[0], r[1], r[2], r[3], json.loads(r[4]), r[5]])) for r in rows]


class StudyCatalog:
    LABELS = {'presentation10': 'Existing presentation · 10 tasks', 'house3': 'Household L3 · 3 tasks',
              'house40_a': 'House-first · set A · cases 01–20', 'house40_b': 'House-first · set B · cases 21–40'}

    def __init__(self, cfg):
        self.cfg = cfg
        self.template = Path(cfg['template_root'])
        self.source = Path(cfg.get('presentation_source', '/home/guest-isl/rishabh/bench/experiments/awarevln_levels_1_2_3_presentation/presentation.html'))
        self.scenes = Path(cfg.get('scene_root', '/data/robotics/toshith/vln_baselines/data/scene_datasets/mp3d'))
        self.lock = threading.RLock()
        self.signature = None
        self.cases = {}
        self.rows = []
        self.selection = {}

    def refresh(self):
        with self.lock:
            selection_path = self.template / 'collection_selection.json'
            selection = json.loads(selection_path.read_text()) if selection_path.is_file() else {}
            dependencies = [self.source, self.template / 'sample_case.json', selection_path,
                            self.template / 'presentation_cases.py']
            if selection.get('authored_source_root'):
                dependencies += [Path(selection['authored_source_root']) / name for name in ['cases_level3.json', 'house_memory_dataset.json']]
            if selection.get('house40_source_root'):
                dependencies += [Path(selection['house40_source_root']) / name for name in ['cases_2azQ1b91cZZ.json', 'week_log_2azQ1b91cZZ.json']]
                dependencies.append(Path(selection['house40_rxr_file']))
            signature = tuple((str(p), p.stat().st_mtime_ns if p.exists() else None) for p in dependencies)
            if signature == self.signature:
                return
            spec = importlib.util.spec_from_file_location('private_catalog_cases', self.template / 'presentation_cases.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            default = json.loads((self.template / 'sample_case.json').read_text())
            cases = module.load_study_cases(self.source, default, selection, include_images=False)
            rows = []
            for key, case in cases.items():
                path = case['route']['reference_path']
                length = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
                if not math.isfinite(length):
                    raise ValueError('A catalog route has an invalid length.')
                scene = case['scene']
                available = (self.scenes / scene / (scene + '.glb')).is_file()
                collection = case.get('source_collection', 'other')
                rows.append({'key': key, 'title': case.get('title', key), 'instruction': case['default_request'],
                             'collection': collection, 'collection_label': self.LABELS.get(collection, collection),
                             'source_file': case.get('source', ''), 'source_folder': case.get('source_folder', ''),
                             'scene': scene, 'length_m': round(length, 3), 'at_least_40m': length >= 40,
                             'memory_count': len(case['memories']), 'available': available,
                             'assignable': available and case.get('ready_for_assignment', True),
                             'notes': case.get('source_notes', 'Navigation-only; object manipulation is not simulated.')})
            self.cases, self.rows, self.selection, self.signature = cases, rows, selection, signature

    def valid_keys(self, keys):
        self.refresh()
        if not isinstance(keys, list) or any(not isinstance(k, str) for k in keys) or len(keys) != len(set(keys)):
            raise AdminError(400, 'Select a unique list of instruction IDs.')
        available = {r['key'] for r in self.rows if r['assignable']}
        if any(k not in available for k in keys):
            raise AdminError(400, 'An instruction is unknown, unavailable, or missing a required source asset. Check its details.')
        return keys

    def legacy_keys(self, username):
        self.refresh()
        selection = self.selection
        if username in selection.get('account_episode_keys', {}):
            return list(selection['account_episode_keys'][username])
        if username in selection.get('full_catalog_users', []):
            return list(self.cases)
        return list(selection.get('episode_keys', self.cases))

    def groups(self):
        self.refresh()
        result = {}
        for row in self.rows:
            group = result.setdefault(row['collection'], {'id': row['collection'], 'label': row['collection_label'],
                                      'source_file': row['source_file'], 'source_folder': row['source_folder'],
                                      'count': 0, 'available': 0})
            group['count'] += 1
            group['available'] += row['available']
        return list(result.values())


class Administration:
    def __init__(self, cfg, accounts, pool):
        self.cfg, self.accounts, self.pool = cfg, accounts, pool
        self.store = AdminStore(accounts)
        self.catalog = StudyCatalog(cfg)
        self.lock = threading.RLock()

    def effective(self, username):
        if self.store.role(username) == 'admin':
            self.catalog.refresh()
            return [r['key'] for r in self.catalog.rows if r['available']]
        assignment = self.store.assignment(username)
        return assignment['keys'] if assignment is not None else self.catalog.legacy_keys(username)

    def worker_selection(self, username, selection):
        explicit = self.store.assignment(username)
        if self.store.role(username) != 'admin' and explicit is None:
            keys = selection.get('account_episode_keys', {}).get(username)
            result = dict(selection)
            result['account_episode_keys'] = {username: keys} if keys is not None else {}
            result['full_catalog_users'] = [username] if username in selection.get('full_catalog_users', []) else []
            return result
        result = dict(selection)
        result['account_episode_keys'] = {username: self.effective(username)}
        result['full_catalog_users'] = []
        return result

    def overview(self, actor):
        self.catalog.refresh()
        users = self.store.list_users()
        for user in users:
            username = user['username']
            assignment = self.store.assignment(username)
            user.update(episode_keys=self.effective(username), revision=assignment['revision'] if assignment else 0,
                        assignment_mode='all_catalog' if user['role'] == 'admin' else 'explicit' if assignment else 'existing',
                        updated_by=assignment['updated_by'] if assignment else None,
                        updated_at=assignment['updated_at'] if assignment else None)
            with self.pool.lock:
                worker = self.pool.workers.get(username)
                state = self.pool.state(worker) if worker else None
                user['worker'] = {'running': bool(worker), 'active': bool(state and state.get('active')),
                                  'processing': bool(state and state.get('processing'))}
            folder = Path(self.cfg['data_root']) / 'contributors' / username
            user['saved_samples'] = sum(1 for _ in folder.glob('sessions/*/*/manifest.json'))
        return {'me': actor, 'users': users, 'instructions': self.catalog.rows, 'collections': self.catalog.groups(),
                'audit': self.store.recent_audit(), 'capacity': self.cfg.get('max_workers', 2)}

    def stop_idle(self, username):
        # Caller holds pool.lock across this check, mutation and DB commit.
        worker = self.pool.workers.get(username)
        if not worker:
            return
        state = self.pool.state(worker)
        if worker.inflight or state is None or state.get('active') or state.get('processing'):
            raise AdminError(409, 'This person is recording, uploading or processing. Wait for them to finish.')
        worker.process.terminate()
        worker.process.wait(timeout=10)
        self.pool.workers.pop(username, None)

    def mutate(self, actor, action, data):
        if not isinstance(data, dict):
            raise AdminError(400, 'Expected an object.')
        if any(k in data for k in ['role', 'admin', 'is_admin']):
            raise AdminError(400, 'Administrator roles are provisioned only through the server CLI.')
        username = data.get('username', '')
        if not isinstance(username, str):
            raise AdminError(400, 'Choose a valid account ID.')
        if 'password' in data and not isinstance(data['password'], str):
            raise AdminError(400, 'Password must be text, or leave it blank to generate one.')
        with self.lock, self.pool.lock:
            if action == 'create-user':
                keys = self.catalog.valid_keys(data.get('episode_keys', []))
                password = data.get('password') or secrets.token_urlsafe(18)
                self.store.create_user(username, password, keys, actor)
                # Returned only once. Never put this in audit/state/browser storage.
                return {'username': username, 'password': password, 'created': True}
            users = {u['username']: u for u in self.store.list_users()}
            if username not in users:
                raise AdminError(404, 'Account not found.')
            if users[username]['role'] == 'admin':
                raise AdminError(400, 'Administrators already have the full catalog. Their access is managed through the server CLI.')
            if action == 'assign':
                keys = self.catalog.valid_keys(data.get('episode_keys', []))
                revision = data.get('revision')
                current = self.store.assignment(username)
                if type(revision) is not int or revision != (current['revision'] if current else 0):
                    raise AdminError(409, 'Assignment changed. Refresh before saving.')
                self.stop_idle(username)
                return {'revision': self.store.save_assignment(username, keys, revision, actor), 'count': len(keys)}
            if action == 'reset-password':
                password = data.get('password') or secrets.token_urlsafe(18)
                self.accounts.validate(username, password)
                self.stop_idle(username)
                self.accounts.reset_password(username, password)
                with self.accounts.connect() as db:
                    self.store.audit(db, actor, 'reset_password', username, {})
                return {'username': username, 'password': password, 'reset': True}
            if action == 'set-enabled':
                enabled = data.get('enabled')
                if type(enabled) is not bool:
                    raise AdminError(400, 'Choose enabled or disabled.')
                self.stop_idle(username)
                with self.accounts.connect() as db:
                    db.execute('UPDATE users SET enabled=? WHERE username=?', (int(enabled), username))
                    db.execute('DELETE FROM logins WHERE username=?', (username,))
                    self.store.audit(db, actor, 'enable_user' if enabled else 'disable_user', username, {})
                return {'enabled': enabled}
        raise AdminError(404, 'Unknown administrator operation.')

    def export(self, markdown=False):
        self.catalog.refresh()
        fields = ['collection_label', 'source_folder', 'source_file', 'key', 'instruction', 'scene', 'length_m', 'memory_count', 'notes']
        if markdown:
            def cell(value):
                return str(value).replace('|', '\\|').replace('\n', ' ')
            lines = ['# Private instruction inventory', '', 'Administrator-only. Do not include this table in participant packs.', '',
                     '| ' + ' | '.join(fields) + ' |', '| ' + ' | '.join(['---'] * len(fields)) + ' |']
            lines += ['| ' + ' | '.join(cell(row[f]) for f in fields) + ' |' for row in self.catalog.rows]
            return '\n'.join(lines) + '\n'
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(fields)
        for row in self.catalog.rows:
            values = []
            for field in fields:
                value = str(row[field])
                if value.lstrip().startswith(('=', '+', '-', '@')):
                    value = "'" + value
                values.append(value)
            writer.writerow(values)
        return output.getvalue()
