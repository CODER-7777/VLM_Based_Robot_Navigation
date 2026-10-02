"""Verify live instrumentation, reset separation and saved-data-only plotting."""
import json
from pathlib import Path
import tempfile
import unittest

import mujoco
import numpy as np
import torch

from interactive import InteractiveSession, RecordedTeleop
from plot_interactive import load_attempt, plot_session
from record import DEFAULT_MODEL, SIM, original
from build_scene import TRACK_CONFIGS, TRACK_SPACING, get_spawn_pos


class InteractiveChecks(unittest.TestCase):
    def test_keyboard_recording_is_passive_and_resets_split_attempts(self):
        torch.set_num_threads(1)
        model = mujoco.MjModel.from_xml_path(str(SIM / 'scene.xml'))
        a, b = mujoco.MjData(model), mujoco.MjData(model)
        baseline = original.MoeStairController(model, a, DEFAULT_MODEL, 'cpu')
        observed = original.MoeStairController(model, b, DEFAULT_MODEL, 'cpu')
        baseline.reset(get_spawn_pos(1))
        teleop = RecordedTeleop(observed, TRACK_CONFIGS, TRACK_SPACING)
        teleop.teleport_to_track(1)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'validation_only'
            session = InteractiveSession(model, b, observed, teleop, out)
            # Exercise chunk boundaries too, without waiting five seconds.
            session.chunk_samples = 31
            applied = (0., 0., 0.)
            for k in range(240):
                if k == 5:
                    teleop.handle_char('w')
                    self.assertEqual(teleop.command, (0., 0., 0.))
                if k == 120:
                    teleop.handle_char('r')
                    baseline.reset(get_spawn_pos(1))
                if k == 129:
                    teleop.handle_key(ord('W'))
                teleop.apply_pending(session)
                tick = k % 4 == 0
                command = teleop.command
                session.prepare_policy(command, tick)
                if tick:
                    applied = command
                    baseline.policy_step(command)
                    observed.policy_step(command)
                session.before_physics(command, teleop.current_track)
                baseline.physics_step(); observed.physics_step()
                session.after_physics()
                np.testing.assert_array_equal(a.qpos, b.qpos)
                np.testing.assert_array_equal(a.qvel, b.qvel)
                np.testing.assert_array_equal(baseline.target_q, observed.target_q)
            session.close()
            m, s, d = load_attempt(out / 'attempt_001')
            self.assertEqual(s['samples'], 120)
            self.assertEqual(m['recording_kind'], 'interactive_user_commands')
            self.assertEqual(d['command'][5, 0], 0.)
            self.assertAlmostEqual(d['input_command'][5, 0], .05)
            self.assertAlmostEqual(d['command'][8, 0], .05)
            self.assertEqual(load_attempt(out / 'attempt_002')[1]['samples'], 120)
            events = [json.loads(line) for line in (out / 'events.jsonl').read_text().splitlines()]
            self.assertEqual(len([e for e in events if e['type'] == 'key']), 3)
            self.assertTrue(any(e.get('reset') for e in events))
            results = plot_session(out)
            self.assertEqual(len(results), 2)
            self.assertIsNone(results[0]['mean_joint_8_30_hz_rms_deg'])
            self.assertTrue((out / 'attempt_001/plots/01_overview.png').exists())
            self.assertTrue((out / 'index.html').exists())
            # Plotting consumed logs only: live physics state is untouched.
            np.testing.assert_array_equal(a.qpos, b.qpos)


if __name__ == '__main__':
    unittest.main(verbosity=2)
