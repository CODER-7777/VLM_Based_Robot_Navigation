"""Durable navigation round trips without starting Habitat or changing live data."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent/'template'))
import collector


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='study-progress-')
        self.old_root = collector.ROOT
        collector.ROOT = self.root = Path(self.temp.name)
        (self.root/'campus_owner.json').write_text('{"username":"alice"}')
        self.session = self.root/'sessions/alice/sample1'
        (self.session/'frames').mkdir(parents=True)
        (self.session/'inputs.json').write_text('{"annotator_id":"alice","episode_key":"fixture"}')
        (self.session/'events.jsonl').write_text('{"type":"reasoning_annotation","text":"Keep my reasoning"}\n')
        self.pose = {'position':[1.,2.,3.], 'rotation_xyzw':[0.,0.,0.,1.]}
        self.row = {'frame_index':2, 'frame_path':'frames/000002.png', 'pose':self.pose,
                    'elapsed_seconds':12.5, 'action':'FORWARD'}

    def tearDown(self):
        collector.ROOT = self.old_root
        self.temp.cleanup()

    def app(self):
        app = collector.Collector.__new__(collector.Collector)
        app.session=None; app.finished=False; app.collection_cases={'fixture':{}}
        app.hs=SimpleNamespace(AgentState=SimpleNamespace)
        app.np=SimpleNamespace(asarray=lambda value,**kw:value, float32=float)
        app.q=SimpleNamespace(quaternion=lambda *values:values)
        app.agent=SimpleNamespace(set_state=lambda state,**kw:setattr(app,'restored_pose',state))
        app.activate_case=lambda key:setattr(app,'case',{'episode_key':key})
        app.render=lambda:setattr(app,'rgb',SimpleNamespace(copy=lambda:b'pixels'))
        def save_frame(directory, rgb, row):
            (directory/row['frame_path']).write_bytes(rgb)
            with (directory/'trajectory.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
        app.save_frame=save_frame; app.event=lambda value:None
        return app

    def checkpoint(self):
        app=self.app(); app.session=self.session;app.case={'episode_key':'fixture'}
        app.pose=lambda:self.pose;app.elapsed=lambda:12.5
        app.actions=7;app.path_length=4.25;app.goal_stage=1;app.goal_reached=False;app.frames=[self.row]
        app.save_checkpoint()

    def test_restart_restores_pose_actions_distance_and_missing_async_frame(self):
        self.checkpoint()
        original_inputs=(self.session/'inputs.json').read_bytes()
        original_events=(self.session/'events.jsonl').read_bytes()
        (self.session/'trajectory.jsonl').write_text('{"partial":')
        resumed=self.app()
        self.assertTrue(resumed.restore_checkpoint())
        self.assertEqual(resumed.session,self.session)
        self.assertEqual(resumed.restored_pose.position,self.pose['position'])
        self.assertEqual((resumed.actions,resumed.path_length,resumed.goal_stage,resumed.frame_index),(7,4.25,1,3))
        self.assertFalse(resumed.finished)
        self.assertEqual((self.session/'inputs.json').read_bytes(),original_inputs)
        self.assertEqual((self.session/'events.jsonl').read_bytes(),original_events)
        self.assertEqual(json.loads((self.session/'trajectory.jsonl').read_text()),self.row)

    def test_other_account_and_finished_samples_are_never_resumed(self):
        self.checkpoint()
        (self.root/'campus_owner.json').write_text('{"username":"bob"}')
        self.assertFalse(self.app().restore_checkpoint())
        (self.root/'campus_owner.json').write_text('{"username":"alice"}')
        (self.session/'manifest.json').write_text('{"finished":true}')
        self.assertFalse(self.app().restore_checkpoint())

    def test_pre_checkpoint_unfinished_sample_can_be_resumed(self):
        (self.session/self.row['frame_path']).write_bytes(b'fixture')
        (self.session/'trajectory.jsonl').write_text(json.dumps(self.row)+'\n{"partial":')
        app=self.app()
        self.assertTrue(app.restore_checkpoint())
        self.assertEqual(app.actions,1)
        self.assertEqual(app.restored_pose.position,self.pose['position'])


if __name__=='__main__':unittest.main()
