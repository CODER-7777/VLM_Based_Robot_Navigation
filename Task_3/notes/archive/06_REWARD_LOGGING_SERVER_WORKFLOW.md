> Historical note. For current commands and decisions, start at [Task 3](../../README.md).

# Reward logging, server transfer, and MoE 90k verification

Prepared: 2026-09-26. This is a manual implementation guide. Commands labelled LAPTOP run on your laptop; commands labelled SERVER run after SSH.

## 1. Actual status when this guide was written

| Item | Status verified locally |
|---|---|
| `action_rate_l2` coefficient | Your `-0.15` edit is present in `env_cfgs.py`, currently line 237. |
| Individual reward logging | **Not added yet** in either training script. Instructions below are proposed manual edits. |
| Per-run `--action-rate-weight` option | **Not added yet**. Instructions below let you compare two weights without repeatedly editing the configuration. |
| Training from the changed reward | Not launched by this assistant. |
| Lab environment and upstream source | Must be checked on the server; local checks do not establish server readiness. |
| Corrected dashboard evaluator | Not found in the searched local repository. The existing interactive demo still has the legacy calf upper limit `+0.5 rad`. |

Core files, relative to `Task_3/xterra_mjlab`:

- [scripts/m2_algorithm_env.py](../../xterra_mjlab/scripts/m2_algorithm_env.py): environment adapter; collect reward terms before reset.
- [scripts/train_other.py](../../xterra_mjlab/scripts/train_other.py): training loop, TensorBoard logging, resume and per-run override.
- [env_cfgs.py](../../xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py): your existing reward-weight edit.

The supplied original checkpoint was inspected on CPU:

| Field | Verified value |
|---|---|
| Update | `90000` |
| Algorithm | `moe` |
| Environments | `8192` |
| Rollout steps/update | `24` |
| Seed | `103001` |
| Optimizers | Two saved optimizer states |
| Saved CUDA RNG states | One; use one visible GPU for these commands |
| Stabilization | Enabled; max learning rate `0.0003`, std bounds `0.05` to `1.0` |
| Saved current learning rate | Approximately `0.000050625` |
| Upstream learner path recorded in checkpoint | `/data/robotics/toshith/m2_algorithm_sources20260913/go2_rl_gym` |
| SHA-256 | `440bbb28d554f75db38bfd163351c04ea4a32d9d06764c37b7e6071d41daa5cb` |

The saved source path is a lead to check, not confirmation that it currently exists on the lab server.

## 2. Does the reward change enter the training score? Does it prove causation?

The correct key is **`action_rate_l2`**, not `action_update_l2`. This reward term already exists in the base environment. Your line changes its weight; it does not add a new reward function.

In the inspected mjlab implementation, the action-change cost is:

```text
cost[t] = sum over joints of (action[t] - action[t-1])²
weighted_rate[t] = weight × cost[t]
```

The adapter clips network actions to `[-6, 6]` before passing them to the environment. Confirm the installed action-manager/reward implementation before assigning the cost to a particular buffer; it is not automatically a physical joint-target difference.

The reward manager iterates through configured reward terms and adds their weighted values to the environment reward. With timestep scaling enabled:

```text
environment_reward[t] = step_dt × sum(weight[i] × raw_term[i])
```

Therefore **you do not need a second hand-written `score += ...` line**. The configuration weight is consumed by the existing reward manager. Adding the same penalty manually again could double-count it.

For the same nonzero action difference, changing `-0.10` to `-0.15` makes this negative contribution 50% larger in magnitude. That changes the incentive during future training. It does not modify the existing 90k checkpoint during playback, and it does not automatically change an evaluation success metric.

There are three different claims to verify:

1. **The term is active:** print the configured weight, log its contribution, and check that per-term contributions reconstruct the environment reward.
2. **The policy responds:** after training, evaluate deterministically and check whether actual action changes decrease.
3. **The jitter improves because of the intervention:** compare equal-budget continuations from the same checkpoint, changing only this coefficient. Look for lower measured joint oscillation while preserving command tracking and stair completion; repeat promising results across additional matched starts/training seeds.

The reported target/joint correlation does not prove that abrupt actions initiate the oscillation. Robot motion also changes the policy's next observation. A successful controlled intervention would support the practical usefulness of this penalty under the tested conditions, not establish it as the only physical root cause.

If raw action changes fall but joint jitter does not, investigate actuator/contact response and target clamping. If both fall but the robot stalls, the task has not improved. If neither changes, inspect the actual reward contribution and training response before increasing the weight again.

## 3. What needs to be transferred?

For a fresh isolated server copy, transfer:

| Item | Why |
|---|---|
| Whole `xterra_mjlab/scripts/` directory | The entry point imports helpers such as `other_backends.py`, `training_recovery.py`, and `train_him.py`. |
| Whole `xterra_mjlab/xterra_mjlab/` package | Robot XML, meshes, actuator, task and reward configuration. |
| `pyproject.toml` and `README.md` | Package metadata and instructions. |
| `checkpoints/svanm2_moe/model_90000.pt` | Actual trainable checkpoint and optimizer state. |
| This guide | Persistent reference on the server. |

Do not copy the laptop `.venv` as the lab training environment. The archive below does not include it. Videos and dashboard assets are unnecessary for training. The independent upstream MoE learner identified by `--source` must also exist on the server; this archive does not contain that external source tree.

### LAPTOP: create and copy a focused archive

Set `SERVER` to the SSH destination that already works for you. The supervisor's handoff used `isl-server`; if your working destination is `guest-isl@isl-pc`, use that instead. The new directory below is a suggested isolated workspace, not an existing path assumed to contain the project.

```bash
LOCAL_TASK=/home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
SERVER=isl-server
REMOTE_WORK=/data/robotics/toshith/vivekananda_moe_jitter_20260926
BUNDLE=/tmp/vivekananda_moe_jitter_20260926.tar.gz

tar --exclude='__pycache__' --exclude='*.pyc' \
  -czf "$BUNDLE" -C "$LOCAL_TASK" \
  xterra_mjlab/scripts \
  xterra_mjlab/xterra_mjlab \
  xterra_mjlab/pyproject.toml \
  xterra_mjlab/README.md \
  xterra_mjlab/checkpoints/svanm2_moe/model_90000.pt \
  notes/06_REWARD_LOGGING_SERVER_WORKFLOW.md

ssh "$SERVER" "mkdir -p '$REMOTE_WORK'"
scp "$BUNDLE" "$SERVER:$REMOTE_WORK/"
ssh "$SERVER"
```

### SERVER: extract into the isolated workspace

```bash
cd /data/robotics/toshith/vivekananda_moe_jitter_20260926
ls
```

On the first transfer, extract:

```bash
tar -xzf vivekananda_moe_jitter_20260926.tar.gz
cd xterra_mjlab
```

If this directory already contains a working copy with edits, use a new workspace or compare the contents first; extracting again would replace matching files. Later, use the three-file update commands in section 6.

## 4. SERVER: verify the environment and inspect configuration before editing

Activate the **original MoE training environment** using its actual activation command. Its name/path has not yet been established. The GQFT handoff's Python 3.9 environment is for a different project; this repository requires Python >=3.11. Do not replace the original mjlab version with the latest release just to make imports succeed.

If you do not know the environment, these read-only commands help locate it:

```bash
command -v python python3 conda uv
python3 --version
rg --files --hidden --no-ignore -g 'pyvenv.cfg' -g '!**/.git/**' /data/robotics/toshith
```

After activation, from the isolated `xterra_mjlab` directory:

```bash
export PYTHONPATH="$PWD:$PWD/scripts${PYTHONPATH:+:$PYTHONPATH}"
python --version
nvidia-smi
```

The `PYTHONPATH` entry is important: an older installed `xterra_mjlab` must not silently override the package you transferred.

Run this inspection, saving its output:

```bash
python - <<'PY' > ../configuration_check.txt
import sys
import inspect
import importlib.metadata
from dataclasses import asdict
from pprint import pprint
import torch
from m2_algorithm_env import make_cfg
from mjlab.managers.reward_manager import RewardManager
from xterra_mjlab.tasks.velocity.config.svanm2 import env_cfgs

print('PYTHON:', sys.executable)
print('MJLAB:', importlib.metadata.version('mjlab'))
print('TORCH:', torch.__version__)
print('CUDA AVAILABLE:', torch.cuda.is_available())
print('TASK SOURCE:', inspect.getfile(env_cfgs))
print('ENV ADAPTER SOURCE:', inspect.getfile(make_cfg))
cfg = make_cfg(8192, 103001)
print('\nPHYSICS CONFIG:')
pprint(asdict(cfg.sim))
print('DECIMATION:', cfg.decimation)
print('\nACTION CONFIG:')
pprint(cfg.actions['joint_pos'])
print('ACTION CONFIG SOURCE:', inspect.getfile(type(cfg.actions['joint_pos'])))
print('\nCOMMAND CONFIG:')
pprint(cfg.commands['twist'])
print('\nCOMMAND CURRICULUM:')
pprint(cfg.curriculum.get('command_vel'))
print('\nREWARD WEIGHTS:')
for name, term in cfg.rewards.items():
    if term is not None:
        print(name, term.weight)
print('\nACTION-RATE FUNCTION:')
print(inspect.getsource(cfg.rewards['action_rate_l2'].func))
print('\nREWARD MANAGER COMPUTE:')
print(inspect.getsource(RewardManager.compute))
PY

cat ../configuration_check.txt
```

This constructs a configuration, not GPU simulation worlds. If imports fail, resolve the environment/source path before proceeding.

Check these items explicitly:

| Item | Check / expected baseline |
|---|---|
| Source paths | The task and adapter paths must point into your isolated server copy. |
| Policy period | Physics timestep × decimation; verify the intended 0.02 s (50 Hz). |
| Action scale | Hip/thigh/calf: 0.15, 0.15, 0.30. |
| Raw clipping | Adapter uses `actions.clamp(-6., 6.)`. |
| Target clamping | Read the installed action implementation and actuator/entity path; establish whether final position targets use all 12 deployed bounds. Configuration repr alone is not proof. |
| Joint-limit penalty | Actual joint-angle penalty is different from clamping requested targets. |
| Observation/history | 45 values × five frames; preserve previous clipped-action semantics and intended history order. |
| Commands | Base lateral range ±0.3 m/s; inspect resumed curriculum for forward speed. Evaluate diagnosis within trained command ranges. |
| Actuator | Coupled transmission, gains, torque limits and delay units; some hardware correspondence remains unmeasured. |
| Current coefficient | `action_rate_l2 = -0.15` in the copied configuration, unless intentionally changed. |
| Reward-buffer semantics | The logging below requires `_step_reward` to store raw term × weight, with the timestep scaling applied separately in `compute`. |

The current upstream implementation has those reward-buffer semantics, but the server's installed version is authoritative. Reference: [mjlab reward manager](https://github.com/mujocolab/mjlab/blob/main/src/mjlab/managers/reward_manager.py).

If target limits differ, resolve and document the intended control contract before interpreting reward comparisons. Apply any shared contract correction to both comparison arms; do not mix a bounds change into only the `-0.15` arm and call the result a reward-only effect.

## 5. Manual code edits on the LAPTOP after the API check

Use the nearby code anchors rather than relying on line numbers, which will move. Do not add duplicate blocks if you have already made an edit.

### Edit A: collect terms before resets in `scripts/m2_algorithm_env.py`

Inside `Adapter.step`, find the existing environment step and add the new assignment immediately after it:

```python
        obs, rewards, terminated, truncated, extras = self.env.step(actions.clamp(-6., 6.))
        reward_term_rates = (
            self.env.reward_manager._step_reward.detach().mean(dim=0)
        )
```

Further down in that function, extend the existing `info` creation:

```python
        info = dict(extras)
        info["reward_term_rates"] = reward_term_rates
```

The mean creates a separate per-term vector before any manual reset. Do not rerun reward functions just to log them; some reward functions may retain state.

### Edit B: select the weight per run in `scripts/train_other.py`

Add this alongside the other argument definitions, before `a = p.parse_args()`:

```python
    p.add_argument("--action-rate-weight", type=float, default=None)
```

Immediately after the existing configuration construction, add the override:

```python
    cfg = make_cfg(a.num_envs, a.seed)
    if a.algorithm == "moe" and a.action_rate_weight is not None:
        cfg.rewards["action_rate_l2"].weight = a.action_rate_weight
```

This is before environment construction and the saved `env.yaml`, so both should use the requested value. Your local configuration can remain `-0.15`; the control run explicitly overrides it to `-0.10`.

### Edit C: accumulate and write reward logs in `scripts/train_other.py`

Immediately after the existing `adapter = Adapter(...)` statement, add:

```python
    reward_names = list(adapter.env.reward_manager.active_terms)
    if adapter.env.reward_manager._step_reward.shape != (a.num_envs, len(reward_names)):
        raise RuntimeError("Unexpected reward buffer layout; inspect installed mjlab")
```

Inside `for update in range(...)`, immediately after the `episode_stats` initialization, add:

```python
        reward_rate_sum = torch.zeros(len(reward_names), device=device)
```

Inside the rollout loop, extend the existing adapter step:

```python
                rewards, done, info, successor = adapter.step(action)
                reward_rate_sum += info.pop("reward_term_rates")
```

After the update, beside the existing `writer.add_scalar("Terrain/mean", ...)` line, add the following at the same indentation level as that line:

```python
        mean_rates = (reward_rate_sum / a.steps).cpu().tolist()
        for name, weighted_rate in zip(reward_names, mean_rates):
            writer.add_scalar(f"RewardRate/{name}", weighted_rate, update)
            weight = adapter.env.reward_manager.get_term_cfg(name).weight
            if weight != 0:
                writer.add_scalar(
                    f"RewardRaw/{name}",
                    weighted_rate / weight,
                    update,
                )
```

Interpretation:

- `RewardRate/action_rate_l2`: average weighted penalty before timestep scaling.
- `RewardRaw/action_rate_l2`: average squared action-change cost; lower means smaller action changes in the inspected buffer.
- Both are averages over environments and rollout steps, not episode totals.
- These include the environment population used by concurrent teacher/student training. They are not student-only deployment metrics; evaluate the deployed student separately.
- They describe reward-manager terms before the adapter's numerical-recovery overrides and PPO timeout bootstrap additions. A nonzero numerical-reset count needs separate investigation.

### Optional one-time proof that terms enter the environment reward

After confirming the installed manager API, insert this immediately after `self.env.step(...)` in `Adapter.step`, before the adapter's numerical guard or any resets. It checks the first step of a process and uses the manager's actual timestep-scaling flag:

```python
        if not getattr(self, "_reward_sum_checked", False):
            rm = self.env.reward_manager
            scale = self.env.step_dt if rm._scale_by_dt else 1.0
            reconstructed = rm._step_reward.sum(dim=1) * scale
            torch.testing.assert_close(
                reconstructed, rewards, rtol=1e-4, atol=1e-6
            )
            self._reward_sum_checked = True
            print("Reward terms match environment reward", flush=True)
```

This checks numerical agreement with the environment reward before additional training bookkeeping. It proves reward inclusion, not that the reward change fixes physical jitter. If it fails, inspect the manager version and reward path; do not simply suppress the failure.

## 6. LAPTOP: transfer only the edited files after the initial copy

These commands assume the isolated server copy from section 3 exists. Run in a laptop terminal; re-enter variables if this is a new terminal.

```bash
LOCAL_PROJECT=/home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3/xterra_mjlab
SERVER=isl-server
REMOTE_PROJECT=/data/robotics/toshith/vivekananda_moe_jitter_20260926/xterra_mjlab

scp "$LOCAL_PROJECT/scripts/m2_algorithm_env.py" \
    "$LOCAL_PROJECT/scripts/train_other.py" \
    "$SERVER:$REMOTE_PROJECT/scripts/"

scp "$LOCAL_PROJECT/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py" \
    "$SERVER:$REMOTE_PROJECT/xterra_mjlab/tasks/velocity/config/svanm2/"
```

These replace the matching files in your isolated workspace. Do not upload edits into an actively running experiment. If both copies have been edited independently, compare them first.

## 7. SERVER: verify transferred edits and checkpoint

From the isolated `xterra_mjlab`, with the correct environment active and `PYTHONPATH` set:

```bash
python - <<'PY'
import ast
from pathlib import Path
paths = [
    'scripts/m2_algorithm_env.py',
    'scripts/train_other.py',
    'xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py',
]
for name in paths:
    ast.parse(Path(name).read_text())
    print('Syntax OK:', name)
PY

rg -n 'reward_term_rates|reward_rate_sum|RewardRate|RewardRaw|action-rate-weight' \
  scripts/m2_algorithm_env.py scripts/train_other.py

python scripts/train_other.py --help
sha256sum checkpoints/svanm2_moe/model_90000.pt
```

Expected: the help includes `--action-rate-weight`; the checkpoint hash matches section 1. Syntax passing does not prove runtime compatibility.

Check the external learner source separately:

```bash
MOE_SOURCE=/data/robotics/toshith/m2_algorithm_sources20260913/go2_rl_gym
ls -ld "$MOE_SOURCE"
```

If missing, locate the original pinned learner or obtain it from the supervisor. Do not substitute another MoE implementation based only on a similar name.

## 8. SERVER: short GPU smoke test of resume and logging

Prerequisites: environment verified, edits transferred, manager API confirmed, original checkpoint/source present. Choose an available GPU from `nvidia-smi`; the example selects physical GPU 0 and exposes it as `cuda:0`.

```bash
export CUDA_VISIBLE_DEVICES=0
MOE_SOURCE=/data/robotics/toshith/m2_algorithm_sources20260913/go2_rl_gym
CKPT="$PWD/checkpoints/svanm2_moe/model_90000.pt"

python - <<'PY'
import torch
assert torch.cuda.is_available()
print('Visible GPUs:', torch.cuda.device_count())
print('Selected GPU:', torch.cuda.get_device_name(0))
PY

python scripts/train_other.py \
  --algorithm moe --source "$MOE_SOURCE" \
  --out ../runs/smoke_logging_rate015 \
  --num-envs 8192 --steps 24 --seed 103001 \
  --resume "$CKPT" --updates 90002 \
  --stabilize --max-learning-rate 0.0003 --std-min 0.05 --std-max 1.0 \
  --action-rate-weight -0.15 --smoke
```

This resumes at 90,000 and performs two updates. `--smoke` reduces episodes to 0.2 s, so it checks execution/logging only. Its checkpoints are not locomotion evidence; do not use them as the starting point for either real comparison run. Both comparison runs must start independently from the original 90k checkpoint.

The output directory must be new; the trainer deliberately refuses an existing directory. If retrying, use a new output name. GPU capacity for this exact job is not yet measured. If it runs out of memory, save the error; the current restore logic requires the original `num_envs=8192`, so silently reducing it is not a drop-in continuation.

Inspect saved configuration and logs:

```bash
rg -n -A 10 'action_rate_l2' ../runs/smoke_logging_rate015/env.yaml
cat ../runs/smoke_logging_rate015/resume.json
cat ../runs/smoke_logging_rate015/progress.json

python - <<'PY'
import math
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
path = '../runs/smoke_logging_rate015'
ea = EventAccumulator(path)
ea.Reload()
tags = ea.Tags()['scalars']
required = ['RewardRate/action_rate_l2', 'RewardRaw/action_rate_l2']
for tag in required:
    assert tag in tags, (tag, tags)
    samples = ea.Scalars(tag)
    assert samples and all(math.isfinite(s.value) for s in samples)
    print(tag, [(s.step, s.value) for s in samples[-2:]])
PY
```

Expected: weight `-0.15`; resume update `90000`; completion at `90002`; finite log values. On the same samples, weighted action-rate values should equal `-0.15 × raw values` within logging precision. That is an inclusion/scaling check, not a jitter outcome.

## 9. SERVER: matched control and candidate training runs

Only proceed with an interpretable jitter experiment once the evaluation/control-contract checks are resolved. Keep both runs' shared environment, timing and stabilization options identical.

The following 500-additional-update budget is an initial pilot example, not a validated sufficient fine-tuning duration. `--updates` is the final update number, not how many updates to add. Run sequentially on the chosen GPU. Do not continue the candidate from the control result.

Control:

```bash
python scripts/train_other.py \
  --algorithm moe --source "$MOE_SOURCE" \
  --out ../runs/control_rate010_90500 \
  --num-envs 8192 --steps 24 --seed 103001 \
  --resume "$CKPT" --updates 90500 \
  --stabilize --max-learning-rate 0.0003 --std-min 0.05 --std-max 1.0 \
  --action-rate-weight -0.10
```

Candidate:

```bash
python scripts/train_other.py \
  --algorithm moe --source "$MOE_SOURCE" \
  --out ../runs/candidate_rate015_90500 \
  --num-envs 8192 --steps 24 --seed 103001 \
  --resume "$CKPT" --updates 90500 \
  --stabilize --max-learning-rate 0.0003 --std-min 0.05 --std-max 1.0 \
  --action-rate-weight -0.15
```

Use a persistent server terminal such as an existing tmux session if the SSH connection may close. No multi-GPU training is implemented by these commands: each run uses one visible A40.

At this stopping point, the trainer writes `latest.pt`; it creates numbered `model_<update>.pt` files only on multiples of 5,000. Therefore do not expect a `model_90500.pt` file automatically. Keep each run's separate `latest.pt` and verify its saved update before evaluation. The trainer saves source snapshots and resolved configuration with each run.

The resume code restores weights, optimizers and learning rate, but simulation episodes are reset and older checkpoints may not include terrain-state information. This is not a bit-for-bit recreation of the original rollout stream. Use identical setup for both arms and report that limit.

## 10. TensorBoard and final evaluation

SERVER, with the training environment active:

```bash
python -m tensorboard.main --logdir ../runs --host 127.0.0.1 --port 6006
```

LAPTOP, in another terminal using your working SSH destination:

```bash
ssh -N -L 6006:127.0.0.1:6006 isl-server
```

Open `http://localhost:6006` in your laptop browser. Compare `RewardRaw/action_rate_l2`, weighted rewards, and tracking/clearance/slip terms. A weighted reward becoming more negative after the coefficient change is not by itself worsening physical behaviour.

Locate the corrected evaluator on SERVER:

```bash
rg --files --hidden -g '!**/.git/**' /data/robotics/toshith \
  | rg 'svanm2_moe_hardware_audit/.*/run_suite.py$'
```

If absent, obtain the complete `svanm2_moe_hardware_audit` source/assets folder. The original audit commands used `/home/pil-lab/toshith/svanm2_moe_hardware_audit/audit/run_suite.py` on another machine. The dashboard and videos do not include the complete corrected evaluator here.

Before evaluation, inspect the evaluator's checkpoint/export-loading interface. Its old `offline_inference.ts` does not update when a `.pt` checkpoint is trained. Each evaluation must load the intended original or newly trained student policy, and record the checkpoint/export hash. Exact evaluation commands depend on the recovered implementation and cannot be verified from the missing source.

Use identical starting conditions and commands for the original 90k, control and candidate. Include flat forward, required 10 cm ascent, and successful rough/downhill cases as regression checks. The existing stair videos show 15 cm, not the required 10 cm.

| Checkpoint | Joint HF RMS | Raw action change | Speed error | Heading/lane error | 10 cm completions | Falls/stalls |
|---|---:|---:|---:|---:|---:|---:|
| Original 90k | | | | | | |
| Control continuation | | | | | | |
| Candidate continuation | | | | | | |

Use sufficiently sampled joint traces for the existing 8–30 Hz metric; a 25 fps video does not resolve that full band. Compare matched windows/commands, report survival duration, and retain failures. Reduced oscillation while standing still or leaving the stairs does not count as a successful fix.

## 11. Immediate order of work

1. Stage the focused project copy on the server.
2. Activate and identify the actual MoE environment; collect `configuration_check.txt`.
3. Confirm reward-manager API and training/evaluation control semantics.
4. Make the two-script logging/CLI edits manually; your configuration weight edit already exists.
5. Transfer the three edited files and verify syntax, imports, weight, and checkpoint hash.
6. Run the two-update smoke check and inspect reward tags.
7. Recover/verify the corrected evaluator and establish original-90k baseline cases.
8. Run the two matched continuations from original 90k.
9. Evaluate original/control/candidate under the same conditions before drawing a conclusion about jitter.

Useful outputs to share next: the actual MoE Python executable, `configuration_check.txt`, the evaluator search result, and any smoke-test traceback. These resolve the remaining unknowns without guessing environment names, target-clamp behaviour or evaluator flags.
