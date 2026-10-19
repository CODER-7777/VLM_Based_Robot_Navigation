"""Validate authored cases on the simulation server using temporary synthetic samples.

Source photographs and rendered images remain on the server. No human media
devices, existing accounts, existing sessions or production worker processes are used.
"""
import argparse
import base64
import importlib.util
import io
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='task5-authored-qa-') as directory:
        root = Path(directory)
        for name in ['collector.py', 'presentation_cases.py', 'sample_case.json', 'collection_selection.json']:
            shutil.copy2(args.template / name, root / name)
        (root / 'campus_owner.json').write_text(json.dumps({'username': 'vivekananda'}))
        sys.path.insert(0, str(root))
        import presentation_cases
        spec = importlib.util.spec_from_file_location('authored_qa_collector', root / 'collector.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        app = module.Collector()
        try:
            assert list(app.collection_cases) == ['house_first_L3_MULTI', 'house_first_L3_ALIAS', 'house_first_L3_SIMPLE']
            for user in ['raj', 'priyansh']:
                selected = presentation_cases.collection_cases(app.cases, root / 'collection_selection.json', user)
                assert list(selected) == ['2azQ1b91cZZ_4240', '2azQ1b91cZZ_7372']
            checked = []
            for key, case in app.collection_cases.items():
                app.activate_case(key)
                assert app.rgb.shape == (512, 512, 3)
                assert app.np.allclose(app.agent.get_state().position, case['route']['start_position'])
                for memory in case['memories']:
                    with app.Image.open(io.BytesIO(base64.b64decode(memory['image_urls'][0].split(',', 1)[1]))) as image:
                        image.verify()
                app.start({'annotator': 'synthetic_validation', 'recording_source': 'synthetic_setup_validation',
                           'episode_key': key, 'relevant_memory_ids': []})
                app.action({'action': 'right'})
                if len(case['route']['goals']) > 1:
                    state = app.agent.get_state(); state.position = case['route']['goals'][-1]['position']
                    app.agent.set_state(state, reset_sensors=True); app.advance_ordered_goals()
                    assert app.goal_stage == 0, 'Final destination incorrectly skipped the pickup stop'
                for goal in case['route']['goals']:
                    state = app.agent.get_state(); state.position = goal['position']
                    app.agent.set_state(state, reset_sensors=True); app.advance_ordered_goals()
                app.render()
                assert app.guidance()['next_action'] == 'stop'
                app.annotate({'text': 'Synthetic setup verification; not human reasoning.', 'memory_ids': []})
                app.finish()
                app.media_executor.submit(lambda: None).result(timeout=120)
                manifest = json.loads((app.session / 'manifest.json').read_text())
                assert (app.session / 'navigation.mp4').is_file()
                assert manifest['intermediate_stops_reached'] == len(case['route']['goals']) - 1
                assert manifest['ordered_navigation_complete']
                app.load_session({'session_id': str(app.session.relative_to(root))})
                assert app.goal_stage == len(case['route']['goals']) - 1
                checked.append({'episode': key, 'memories_verified': len(case['memories']),
                                'reference_length_m': round(sum(math.dist(a, b) for a, b in zip(
                                    case['route']['reference_path'], case['route']['reference_path'][1:])), 2),
                                'ordered_goals': len(case['route']['goals']), 'synthetic_save_reload_passed': True})
            result = {'passed': True, 'cases': checked, 'participant_assignment_unchanged': True,
                      'images_validated_on_server_only': True, 'human_recordings_created': False,
                      'synthetic_samples_temporary': True, 'source_cases_modified': False}
            args.report.write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result, indent=2))
        finally:
            app.frame_executor.shutdown(wait=True)
            app.media_executor.shutdown(wait=True)
            app.sim.close()


if __name__ == '__main__':
    main()
