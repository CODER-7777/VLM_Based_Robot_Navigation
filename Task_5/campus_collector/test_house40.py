"""The forty-case adapter is checked with synthetic routes/photos only."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('house40_fixture_cases', Path(__file__).parent / 'template/presentation_cases.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class House40Tests(unittest.TestCase):
    def test_halves_routes_memories_request_photo_and_private_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_folder = root / 'verify/2azQ1b91cZZ'
            image_folder.mkdir(parents=True)
            (image_folder / 'memory_m1.jpg').write_bytes(b'synthetic-image')
            moments = [{'id': 'm1', 'who': 'Fixture', 'quote': 'This is the remembered room.', 'view': 'room', 'day': 'Monday', 'time': '10:00'},
                       {'id': 'm2', 'who': 'Fixture', 'quote': 'Synthetic speech-only memory.', 'view': None}]
            (root / 'week_log_2azQ1b91cZZ.json').write_text(json.dumps({'moments': moments}))
            rows = []
            for i in range(1, 41):
                rows.append({'case_id': 'synthetic_' + str(i), 'episode_ids': ['1'], 'level1_instruction_id': 'guide',
                             'end_xyz': [2, 0, 0], 'sub': [1, 2] if i == 1 else None,
                             'levels': {'3': {'text': 'Find the synthetic destination.', 'speaker': 'Fixture', 'image_view': 'room' if i == 1 else None}},
                             'week_log_ids': ['m1', 'm2'], 'start': {'story': 'Synthetic start.'}})
            path = root / 'cases_2azQ1b91cZZ.json'
            rows[6]['levels']['3']['image'] = 'Synthetic photo not supplied'
            path.write_text(json.dumps(rows))
            episode = {'episode_id': 1, 'instruction': {'instruction_id': 'guide'}, 'start_rotation': [0, 0, 0, 1],
                       'reference_path': [[0, 0, 0], [1, 0, 0], [2, 0, 0]]}
            rxr = root / 'guide.json.gz'
            with gzip.open(rxr, 'wt') as stream:
                json.dump({'episodes': [episode]}, stream)
            cases = module.load_house40_cases(root, rxr)
            self.assertEqual(len(cases), 40)
            self.assertEqual(sum(c['source_collection'] == 'house40_a' for c in cases.values()), 20)
            self.assertEqual(sum(c['source_collection'] == 'house40_b' for c in cases.values()), 20)
            first = cases['house40_synthetic_1']
            self.assertEqual(first['route']['reference_path'], [[1, 0, 0], [2, 0, 0]])
            self.assertEqual(first['route']['start_position'], [1, 0, 0])
            self.assertTrue(first['route']['authored_subroute_heading'])
            self.assertTrue(first['request_image_url'].startswith('data:image/'))
            self.assertEqual(first['memories'][1]['image_urls'], [])
            self.assertEqual(first['default_relevant_memory_ids'], [])
            self.assertTrue(first['ready_for_assignment'])
            self.assertFalse(cases['house40_synthetic_7']['ready_for_assignment'])
            self.assertIn('Missing request photo', cases['house40_synthetic_7']['source_notes'])
            public = module.public_case(first)
            for key in ['route', 'source', 'source_folder', 'source_collection', 'source_notes', 'source_goal_memory_id']:
                self.assertNotIn(key, public)
            metadata = module.load_house40_cases(root, rxr, include_images=False)
            self.assertTrue(all(not m['image_urls'] for c in metadata.values() for m in c['memories']))
            rows[0]['end_xyz'] = [100, 0, 0]
            path.write_text(json.dumps(rows))
            with self.assertRaisesRegex(ValueError, 'endpoint mismatch'):
                module.load_house40_cases(root, rxr)


if __name__ == '__main__':
    unittest.main()
