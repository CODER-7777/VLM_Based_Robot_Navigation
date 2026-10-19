"""Verify the route cutoff and server-side selection without starting Habitat."""
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


presentation = module('presentation_cases', ROOT / 'template/presentation_cases.py')
import sys
sys.modules['presentation_cases'] = presentation
collector = module('study_collector', ROOT / 'template/collector.py')


class SelectionTests(unittest.TestCase):
    def test_strict_cutoff_and_archive_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'selection.json'
            cases = {key: {'route': {'reference_path': [[0, 0, 0], [length, 0, 0]]}}
                     for key, length in [('long', 41), ('boundary', 40), ('short', 39.9)]}
            path.write_text(json.dumps({'episode_keys': ['long'], 'minimum_reference_length_m_exclusive': 40}))
            selected = presentation.collection_cases(cases, path)
            self.assertEqual(list(selected), ['long'])
            self.assertEqual(set(cases), {'long', 'boundary', 'short'})
            for key in ['boundary', 'short', 'missing']:
                path.write_text(json.dumps({'episode_keys': [key], 'minimum_reference_length_m_exclusive': 40}))
                with self.assertRaises(ValueError):
                    presentation.collection_cases(cases, path)

    def test_cannot_bypass_menu_to_start_archived_episode(self):
        app = collector.Collector.__new__(collector.Collector)
        app.collection_cases = {'allowed': {}}
        app.case = {'episode_key': 'archived'}
        with self.assertRaisesRegex(ValueError, 'current study episode'):
            app.start({})
        with self.assertRaisesRegex(ValueError, 'study episode'):
            app.select_case({'episode_key': 'archived'})

    def test_only_named_account_gets_full_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'selection.json'
            path.write_text(json.dumps({'episode_keys': ['long'], 'minimum_reference_length_m_exclusive': 40,
                                        'full_catalog_users': ['vivekananda']}))
            cases = {key: {'route': {'reference_path': [[0, 0, 0], [length, 0, 0]]}}
                     for key, length in [('long', 41), ('laundry', 10)]}
            self.assertEqual(set(presentation.collection_cases(cases, path, 'vivekananda')), set(cases))
            for username in ['raj', 'priyansh', None, '', 'Vivekananda', 'vivekananda_01']:
                self.assertEqual(list(presentation.collection_cases(cases, path, username)), ['long'])

    def test_account_assignment_is_exact_and_keeps_short_authored_cases(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'selection.json'
            path.write_text(json.dumps({'episode_keys': ['long'], 'minimum_reference_length_m_exclusive': 40,
                                        'account_episode_keys': {'vivekananda': ['new_case']}}))
            cases = {'long': {'route': {'reference_path': [[0, 0, 0], [41, 0, 0]]}},
                     'new_case': {'route': {'reference_path': [[0, 0, 0], [16, 0, 0]]}}}
            self.assertEqual(list(presentation.collection_cases(cases, path, 'vivekananda')), ['new_case'])
            for user in ['raj', 'priyansh', None, 'Vivekananda']:
                self.assertEqual(list(presentation.collection_cases(cases, path, user)), ['long'])

    def test_adapter_preserves_start_order_and_keeps_answers_out_of_public_case(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            # Synthetic schema fixtures keep this test independent of private
            # deployment metadata, licensed scene images and dataset downloads.
            source_cases = []
            records = []
            for index, case_id in enumerate(['L3_MULTI', 'L3_ALIAS', 'L3_SIMPLE']):
                references = [{'id': f'm{index}_{j}', 'image': f'images/{index}_{j}.jpg'}
                              for j in range(3)]
                records.extend({'id': ref['id'], 'annotation': 'Synthetic household memory.'}
                               for ref in references)
                source_cases.append({
                    'case_id': case_id, 'scene': 'synthetic_scene',
                    'original_start': [index, 0, 0], 'original_start_rotation': [0, 0, 0, 1],
                    'reference_path': [[index, 0, 0], [index, 0, 2], [index, 0, 4]],
                    'legs': [{'stop': [index, 0, 2], 'goal': 'first destination'},
                             {'stop': [index, 0, 4], 'goal': 'final destination'}],
                    'trajectory': f'synthetic_{index}', 'evaluation_scope': 'Synthetic fixture only.',
                    'phenomenon': case_id, 'memory_records': references,
                    'request': {'text': 'Visit the remembered place.', 'speaker': 'fixture',
                                'issued_at': '2026-01-01T12:00:00Z', 'start_story': 'Synthetic start.'},
                })
            (root / 'cases_level3.json').write_text(json.dumps(source_cases))
            (root / 'house_memory_dataset.json').write_text(json.dumps({'records': records}))
            for case in source_cases:
                for reference in case['memory_records']:
                    image = root / reference['image']; image.parent.mkdir(parents=True, exist_ok=True)
                    image.write_bytes(b'synthetic-image-fixture')
            cases = presentation.load_house_cases(root)
            self.assertEqual(len(cases), 3)
            for source in source_cases:
                case = cases['house_first_' + source['case_id']]
                self.assertEqual(case['route']['start_position'], source['original_start'])
                self.assertEqual(case['route']['start_rotation_xyzw'], source['original_start_rotation'])
                self.assertEqual(case['route']['reference_path'], source['reference_path'])
                self.assertEqual([goal['position'] for goal in case['route']['goals']], [leg['stop'] for leg in source['legs']])
                self.assertEqual(case['default_request'], source['request']['text'])
                self.assertEqual(len(case['memories']), 3)
                public = presentation.public_case(case)
                self.assertNotIn('route', public)
                self.assertNotIn('answer_explanation', public)
                self.assertEqual(public['default_relevant_memory_ids'], [])
                self.assertTrue(all('role' not in memory for memory in public['memories']))

    def test_ordered_visits_cannot_skip_the_kitchen(self):
        app = collector.Collector.__new__(collector.Collector)
        app.case = {'route': {'goals': [{'position': [0, 0, 0]}, {'position': [10, 0, 0]}]}}
        app.goal_stage = 0
        position = [10, 0, 0]
        app.agent = SimpleNamespace(get_state=lambda: SimpleNamespace(position=position))
        app.hs = SimpleNamespace(ShortestPath=SimpleNamespace)
        app.np = SimpleNamespace(asarray=lambda value, dtype: value, float32=float)
        def find_path(path):
            path.geodesic_distance = math.dist(path.requested_start, path.requested_end)
            return True
        app.sim = SimpleNamespace(pathfinder=SimpleNamespace(find_path=find_path))
        events = []; app.event = events.append
        app.advance_ordered_goals()
        self.assertEqual(app.goal_stage, 0)
        position[:] = [0, 0, 0]
        app.advance_ordered_goals()
        self.assertEqual(app.goal_stage, 1)
        self.assertEqual(events[0]['type'], 'intermediate_navigation_stop')
        position[:] = [10, 0, 0]
        self.assertEqual(app.guidance()['next_action'], 'stop')


if __name__ == '__main__':
    unittest.main()
