#!/usr/bin/env python3
"""Validate all presentation environments in an isolated temporary workspace.

Run with the server's Habitat interpreter. Only GPU 0 renders scenes. No policy
or VILA model is loaded; no live collector or human recording is modified.
"""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import time

import collector


def main():
    source_root = collector.ROOT
    app = None
    report = {'episodes': [], 'recorded_scenes': []}
    with tempfile.TemporaryDirectory(prefix='environment-validation-', dir=str(source_root)) as temporary:
        collector.ROOT = Path(temporary)
        (collector.ROOT / 'sample_case.json').write_bytes((source_root / 'sample_case.json').read_bytes())
        try:
            app = collector.Collector()
            catalog = app.environments()
            assert len(catalog) == 4 and len(app.cases) == 10
            assert all(environment['available'] for environment in catalog)
            assert app.case['episode_key'] == 'QUCTc6BB5sX_8247'
            assert 'carrying dirty school clothes' in app.case['default_current_state']
            assert app.case['scenario_matches_original_benchmark'] is False
            saved = []
            for environment in catalog:
                for item in environment['episodes']:
                    state = app.select_case({'episode_key': item['episode_key']})
                    case = app.case
                    assert state['scene'] == environment['scene']
                    assert state['episode_key'] == case['episode_key']
                    assert app.np.allclose(app.pose()['position'], case['route']['start_position'], atol=.005)
                    assert app.sim.pathfinder.is_loaded
                    assert app.guidance()['distance_m'] is not None
                    assert base64.b64decode(state['frame_data_url'].split(',', 1)[1]).startswith(b'\xff\xd8')
                    assert 'route' not in state['case'] and 'source_goal_memory_id' not in state['case']
                    assert case['default_relevant_memory_ids'] == [case['source_goal_memory_id']]
                    assert len(case['memories']) == 3
                    assert all(len(memory['image_urls']) == len(memory['original_view_indices']) for memory in case['memories'])
                    report['episodes'].append({'episode_key':case['episode_key'], 'scene':case['scene'],
                        'authored_start_pose_matches':True, 'JPEG_rendered':True, 'navmesh_route_available':True,
                        'correct_memories_and_relevant_label':True})
                case = app.case
                state = app.start({'annotator':'isolated_environment_validation',
                    'episode_key':case['episode_key'], 'relevant_memory_ids':case['default_relevant_memory_ids'],
                    'recording_source':'automated_environment_validation_not_human'})
                for operation in [lambda:app.select_case({'episode_key':next(iter(app.cases))}),
                                  lambda:app.load_session({'session_id':state['session_id']})]:
                    try:
                        operation()
                        raise AssertionError('Environment/load operation interrupted an active sample')
                    except ValueError:
                        pass
                app.action({'action':'forward'});app.action({'action':'right'})
                state = app.action({'action':'stop'})
                for _ in range(200):
                    state = app.status()
                    if state['download_url']:
                        break
                    time.sleep(.1)
                assert state['download_url']
                directory = collector.ROOT / state['session_id']
                inputs = json.loads((directory/'inputs.json').read_text())
                manifest = json.loads((directory/'manifest.json').read_text())
                assert inputs['scene'] == environment['scene'] == manifest['scene']
                assert inputs['episode_key'] == case['episode_key'] == manifest['episode_key']
                assert [m['id'] for m in inputs['supplied_memories']] == [m['id'] for m in case['memories']]
                assert manifest['movement_actions'] == 2 and manifest['frame_count'] == 4
                import imageio_ffmpeg
                subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(directory/'navigation.mp4'),
                    '-f','null','-'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                saved.append((state['session_id'], environment['scene'], case['episode_key']))
                report['recorded_scenes'].append({'scene':environment['scene'],'movement_actions':2,
                    'frame_count':4,'MP4_decodes':True,'scene_episode_and_memory_provenance_correct':True})
            # Replay each saved session after a different scene has been loaded.
            for session_id, scene, episode_key in saved:
                state = app.load_session({'session_id':session_id})
                assert state['scene'] == scene and state['episode_key'] == episode_key
                assert state['case']['scene'] == state['inputs']['scene'] == scene
                assert state['finished'] and not state['active']
            before = app.case['episode_key']
            try:
                app.select_case({'episode_key':'../../invalid'})
                raise AssertionError('Unknown environment was accepted')
            except ValueError:
                pass
            assert app.case['episode_key'] == before
            report.update(all_checks_passed=True, environment_count=4, episode_count=10,
                active_sample_switch_rejected=True, saved_sessions_restore_correct_scene=True,
                dirty_clothes_scenario_preserved=True, unknown_episode_rejected=True,
                human_recordings_modified=False, physical_GPU_used=0, policy_or_VILA_inference=False)
        finally:
            if app is not None:
                app.frame_executor.shutdown(wait=True);app.media_executor.shutdown(wait=True);app.sim.close()
            collector.ROOT = source_root
    (source_root/'environment_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
