# Recording and analysis tools

Use the [main README](../README.md) for simulation and plotting commands, and the [debugging strategy](../notes/25_RL_POLICY_DEBUG_STRATEGY_20261017.md) for the investigation order.

| Task | Script in `jitter_analysis/` | Runs new simulation? |
| --- | --- | --- |
| Record an interactive session | `interactive.py`, called by the viewer with `--record` | Records the running viewer |
| Plot saved attempts | `plot_interactive.py` | No |
| Verify recorded policy outputs and inspect gating/timing | `diagnose_updates.py` | No; offline policy replay |
| Inspect target spikes and actor-input sensitivity | `inspect_policy_spikes.py` | No; offline policy probes |
| Compare recorded attempts and commands | `review_interactive.py`, `compare_policy_runs.py` | No |
| Run scripted controlled experiments | `record.py`, `run_suite.py`, `audit_control_loop.py`, `verify_current_contract.py` | Yes |

For the latest inspected session, from **Task_3**:

```bash
CUDA_VISIBLE_DEVICES='' xterra_mjlab/.venv/bin/python \
  tools/jitter_analysis/diagnose_updates.py \
  tools/results/interactive/20261017_205511_247716 \
  --device cpu --out tools/results/policy_debug_20261017
```

Open [the diagnostics dashboard](results/policy_debug_20261017/index.html). Replace session/output paths for a new recording. Rerunning the plotting tools replaces their derived outputs, while retaining raw recordings.

Recorded joints are sampled at 200 Hz; the standard joint analysis band is 8–30 Hz. Policy targets and gate weights are sampled at 50 Hz; use a band below their 25 Hz Nyquist limit. Compare consistent commands, windows, checkpoint identities and outcomes.

`audit_gate_frequency.py` currently contains October 11 attempt/phase selections; adapt them before analyzing another session. [Historical complete tool reference](../notes/archive/TOOLS_REFERENCE_20261011.md).
