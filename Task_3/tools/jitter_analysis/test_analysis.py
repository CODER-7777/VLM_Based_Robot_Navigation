"""Checks that instrumentation is passive and metrics/success criteria are meaningful."""
import unittest
import json
from pathlib import Path
import tempfile
import mujoco
import numpy as np
import torch

import record
from analyze import band_rms


class AnalysisChecks(unittest.TestCase):
    def test_contact_override_is_explicit_and_recorded(self):
        import argparse
        from run_interactive_sim import configure_contact, parse_args
        model = mujoco.MjModel.from_xml_path(str(record.SIM / 'scene.xml'))
        before = record.solver_contract(model)
        friction, solref = model.geom_friction.copy(), model.geom_solref.copy()
        configure_contact(model, parse_args([]).contact_impratio)
        self.assertEqual(record.solver_contract(model), before)
        configure_contact(model, parse_args(['--contact-impratio', '10']).contact_impratio)
        self.assertEqual(record.solver_contract(model), dict(before, impratio=10.))
        np.testing.assert_array_equal(model.geom_friction, friction)
        np.testing.assert_array_equal(model.geom_solref, solref)
        for value in (0., -1., float('nan'), float('inf')):
            with self.assertRaises(argparse.ArgumentTypeError):
                configure_contact(model, value)

    def test_fresh_observation_is_consistent_and_records_actual_input(self):
        from build_scene import TRACK_CONFIGS, TRACK_SPACING
        from interactive import InteractiveSession, RecordedTeleop
        torch.set_num_threads(1)
        model = mujoco.MjModel.from_xml_path(str(record.SIM / 'scene.xml'))
        data = mujoco.MjData(model)
        ctrl = record.original.MoeStairController(model, data, record.DEFAULT_MODEL, 'cpu',
                                                observation_timing='fresh')
        ctrl.reset(record.get_spawn_pos(1))
        # A changed integrated velocity makes stale derived gyro data observable.
        data.qvel[3:6] = [.3, -.2, .1]
        command = (.15, 0., 0.)
        scratch = mujoco.MjData(model)
        mujoco.mj_copyData(scratch, model, data)
        mujoco.mj_forward(model, scratch)
        expected = record.fresh_frame(ctrl, scratch, command)
        legacy = ctrl.get_legacy_frame(command)
        before = {name: getattr(data, name).copy()
                  for name in ('qpos', 'qvel', 'sensordata', 'xmat', 'qacc_warmstart', 'ctrl')}
        np.testing.assert_array_equal(ctrl.get_current_frame(command), expected)
        self.assertGreater(float(np.max(np.abs(expected - legacy))), 1e-5)
        for name, value in before.items():
            np.testing.assert_array_equal(getattr(data, name), value)
        teleop = RecordedTeleop(ctrl, TRACK_CONFIGS, track_spacing=TRACK_SPACING)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'recording'
            session = InteractiveSession(model, data, ctrl, teleop, out)
            try:
                session.prepare_policy(command, True)
                ctrl.policy_step(command)
                session.before_physics(command, 1)
                ctrl.physics_step()
                session.after_physics()
            finally:
                session.close()
            manifest = json.loads((out / 'manifest.json').read_text())
            self.assertEqual(manifest['observation_timing'], 'fresh')
            with np.load(out / 'attempt_001/raw/chunk_00000.npz') as trace:
                np.testing.assert_array_equal(trace['obs_policy'][0], expected)
                np.testing.assert_array_equal(trace['obs_fresh'][0], expected)
                np.testing.assert_array_equal(trace['obs_viewer'][0], legacy)

    def test_frequency_band_and_units(self):
        fs = 200
        t = np.arange(0, 6, 1 / fs)
        signal = 2 * np.sin(2 * np.pi * 10 * t) + 20 * np.sin(2 * np.pi * t)
        self.assertAlmostEqual(float(band_rms(signal, fs)), np.sqrt(2), places=3)
        self.assertIsNone(band_rms(signal[:200], fs))
        with self.assertRaises(ValueError): band_rms(signal, 50, 8, 30)

    def test_success_needs_four_feet_and_support(self):
        row = dict(foot_pos=np.array([[4., -9.5, 1.23]] * 4), tilt_deg=0., base_clearance=.32)
        self.assertTrue(record.top_reached(row, np.ones(4, dtype=bool)))
        self.assertFalse(record.top_reached(row, np.array([1, 1, 1, 0], dtype=bool)))
        row["foot_pos"][3, 0] = 3.5
        self.assertFalse(record.top_reached(row, np.ones(4, dtype=bool)))

    def test_transmission_independent_of_target_limits(self):
        q = np.array([.1, .6, -1.2])
        np.testing.assert_allclose(record.original.J_LEG @ q, [8*.1, 8*.6, 16*(-1.2 + .5*.6)])
        gains = np.diag(20 / np.array([8, 8, 16])**2)
        np.testing.assert_allclose(record.original.J_LEG.T @ gains @ record.original.J_LEG,
                                   [[20, 0, 0], [0, 25, 10], [0, 10, 20]])

    def test_passive_recording_preserves_original_trajectory(self):
        torch.set_num_threads(1)
        model = mujoco.MjModel.from_xml_path(str(record.SIM / "scene.xml"))
        a, b = mujoco.MjData(model), mujoco.MjData(model)
        baseline = record.original.MoeStairController(model, a, record.DEFAULT_MODEL, "cpu")
        observed = record.ObservedController(model, b, record.DEFAULT_MODEL, "cpu", "viewer")
        spawn = record.get_spawn_pos(1)
        baseline.reset(spawn); observed.reset(spawn)
        logger = record.Recorder(model, b, observed, "stairs")
        max_sensor_gap = 0.
        for k in range(240):
            command = (.15, 0., 0.)
            logger.prepare()
            fresh = record.fresh_frame(observed, logger.scratch, command)
            viewer = observed.get_current_frame(command)
            if k == 0: np.testing.assert_array_equal(fresh, viewer)
            max_sensor_gap = max(max_sensor_gap, np.max(np.abs(fresh[3:9] - viewer[3:9])))
            if k % 4 == 0:
                baseline.policy_step(command); observed.policy_step(command)
            logger.state_row(np.array(command), k % 4 == 0)
            baseline.physics_step(); observed.physics_step()
            logger.contacts_after_step(k * .005)
            np.testing.assert_array_equal(a.qpos, b.qpos)
            np.testing.assert_array_equal(a.qvel, b.qvel)
            np.testing.assert_array_equal(baseline.target_q, observed.target_q)
        self.assertGreater(max_sensor_gap, 1e-5)
        print(f"Passive recorder: exact trajectory equality for 240 CPU physics steps; max scaled sensor discrepancy {max_sensor_gap:.6g}")


if __name__ == "__main__": unittest.main(verbosity=2)
