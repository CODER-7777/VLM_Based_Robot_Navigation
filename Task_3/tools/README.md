# SvanM2 analysis tools

Runtime: `Task_3/xterra_mjlab/.venv` (Python, PyTorch, MuJoCo, NumPy, Matplotlib; mjlab for reward integration). Scripts live in `jitter_analysis/` and import the simulator/controller from the SvanM2 source checkout.

## Interfaces

| Module | Inputs / method | Outputs |
| --- | --- | --- |
| `record.py`, `interactive.py` | Policy/controller, physics state, keyboard commands, resets; passive recording | Session/attempt manifests, source hashes, contacts, chunked raw NPZ, status |
| `analyze.py`, `plot_interactive.py`, `plot_help.py` | Saved traces; band RMS, units/timing, torque reconstruction | Metrics JSON, plots, HTML |
| `review_interactive.py`, `compare_policy_runs.py` | Recorded attempts; command/duration/contact/checkpoint contract checks | Matched windows, tracking/oscillation comparisons, CSV/JSON/HTML |
| `inspect_policy_spikes.py`, `diagnose_updates.py` | Saved policy input/action history, strict checkpoint replay, MoE/actor decomposition | Target-spike/gate diagnostics and consistency checks |
| `first_contact.py`, `compare_starts.py` | Contact events, foot trajectories, paired starts | Clearance/support/traversal analysis |
| `audit_target_rates.py`, `target_rate_reward.py` | Actual clamped target deltas and policy timestamps | Exploratory target-rate distributions and reward proposal |
| `run_suite.py` | Scripted flat/stair/sensing/start protocol | Frozen comparison runs and source snapshots |
| `audit_control_loop.py` | Matched gain/contact/sensing interventions; 50 Hz policy / 200 Hz PD | Protocol, run traces, summary metrics |
| `summarize_control_loop_audit.py` | Existing contact-audit traces; independent traversal and contact Jacobian checks | `audit_findings.json`, contact-response/fixed-state diagnostics, figures |
| `tier1_solver_probe.py` | Contact/substep grid with explicit policy/PD rates | Iteration, slip, penetration, tracking and vibration diagnostics |
| `smoke_target_rate_env.py` | Synthetic action sequence in reward manager/environment | Integration check; not policy capability |

## Data contracts

Joint traces at 200 Hz: 8–30 Hz analysis band. Policy targets at 50 Hz: 8–20 Hz. `requested`, `target`, `q`, applied torque, command, contact, and source/checkpoint hashes are distinct fields. Flat/stair classification comes from contacts, not filenames. Traversal requires all-foot platform/support/lane/upright criteria. Commands and window durations must match for comparisons.

`results/interactive/<session>/attempt_*/` holds raw chunks plus `plots/`; `results/<study>/` holds scripted studies. `archive/` preserves earlier debug exports and guides. Checkpoints remain in the source checkout/evaluation-run folders.

## CPU regression suite

```bash
cd Task_3/tools/jitter_analysis
CUDA_VISIBLE_DEVICES='' ../../xterra_mjlab/.venv/bin/python -m unittest test_target_rate_reward test_analysis test_interactive -v
```

13 tests cover reward timing/clamping/reset semantics, training-profile overrides, known-frequency RMS/Nyquist behavior, observation freshness, passive trajectory equality, full-foot traversal, transmission mapping, and reset-delimited keyboard recording. No hardware or server connection is required; local checkpoint/robot assets are required.
