# Task 3 — SvanM2 MoE locomotion diagnostics

Objective: identify jitter/stair failure mechanisms and evaluate policy changes under explicit observation, actuator, and contact contracts. A measured real-robot improvement remains pending.

## Policy and actuator contract

MoE student: 5×45=225-D proprioceptive/command history → 12 raw actions; FL/FR/RL/RR hip/thigh/calf order. Policy 50 Hz; coupled PD/physics 200 Hz. Targets are standing offsets + scaled actions, followed by bounds; raw previous-action feedback is distinct from clamped targets. No explicit stair-height map enters the student.

`J_LEG = [[8,0,0],[0,8,0],[0,8,16]]`; `tau_joint = J_LEG.T @ tau_motor`. Thigh/calf stiffness is coupled. Target bounds do not change the transmission matrix. Hardware bounds reported by the early audit and wider viewer bounds are different contracts.

## Attempts and outcomes

| Attempt | Result | Interpretation |
| --- | --- | --- |
| Deployment/hardware-log audit | History, targets, command shaping, timing/reset/contact mismatches; 122,607-sample ~200 Hz log and 30,175 policy I/O records | Target/angle oscillation correlation 0.962; physical cause unresolved |
| Combined reward/bounds continuation, 90500 | Reduced target removal and better early forward tracking; mixed jitter; 0/12 distinct stair traversals | Multiple simultaneous changes prevent isolated reward attribution |
| Matched flat/stair collision intervention | Candidate/viewer same post-contact joint RMS 0.331° flat vs 0.833° stairs | Contact changes closed-loop response, without identifying a unique cause |
| Recorded keyboard sessions and gate/actor probes | Checkpoint replay, target/torque reconstruction, equal-command windows, spike decomposition | Flat sideways targets can spike; gate association is not gate causal proof |
| Time-aware target-rate penalty | Elapsed-time/reset/manager integration checks; thresholds derived from recordings | Implemented cost, not established locomotion improvement |
| 0.13 m swing preference / newest91000 | −0.01 rate weight, viewer-wide bounds, saved LR cap 1e−5 | Distinct from older91000; matched vy=0.15 RMSE worsens 0.1107→0.1335 m/s |
| Gain sweep | Responses differ by checkpoint; PD reconstruction checked | No universal damping-only fix established |
| Contact-setting A/B | Lower band RMS with `impratio=10`; four matched stair pairs complete at 10 and fail at 100 | Strong simulator sensitivity; not hardware validation |
| Tier-1 solver/substep probe | 28 grid/confirmation cases with iterations, slip, penetration, tracking and band RMS | Simulator numerical diagnostics, not independent trained seeds |

## Reward experiment

`q_cmd = clamp(action*scale + offset)`; `cost_rate = sum(relu(abs(q_cmd[t]-q_cmd[t-1])/(step_dt*rate_limit)-1)^2)`.

Exploratory hip/thigh/calf thresholds: **7.093/11.275/20.365 rad/s**, 1.25×P99 from six approach windows / 1,200 policy intervals. The review covers 41 attempts, with 19 qualifying four-second windows. These are target-rate references, not actuator speed limits. First-action reset masking applies. Existing second-difference and saturation costs are retained; reward rates and per-step rewards differ by `step_dt`.

## Controlled contact result

Common 5–11 s interval, requested axis speed 0.30 m/s, `kp=18`, `kd=0.7`, same checkpoint/start/targets/friction/timing within each pair; only `impratio` changes:

| Policy / axis | Joint 8–30 Hz RMS: 100 → 10 | Mean speed: 100 → 10 |
| --- | ---: | ---: |
| Original90000 / X | 0.380→0.103° | 0.215→0.246 m/s |
| Original90000 / Y | 0.281→0.157° | 0.202→0.202 m/s |
| Newest91000 / X | 0.284→0.120° | 0.235→0.246 m/s |
| Newest91000 / Y | 0.382→0.169° | 0.205→0.242 m/s |

Twelve additional fresh-sensing/start pairs reduce band RMS by 32.9–75.2%. Twelve 10 cm risers, one nominal start:

| Policy; kp/kd | At 100 | At 10 |
| --- | --- | --- |
| Original90000; 18/0.7 | Lane exit | Traversed 24.605 s |
| Newest91000; 18/0.7 | Lane exit | Traversed 25.475 s |
| Original90000; 20/0.7 | Incomplete timeout | Traversed 23.700 s |
| Newest91000; 20/0.7 | Lane exit | Traversed 25.370 s |

Traversal: every foot beyond x=3.622 m and inside lane, every foot having loaded platform >1 N, tilt <30°, base clearance >0.18 m, held ≥0.5 s. Four policy/gain cases are not independent seeds. `impratio` controls simulated frictional/normal constraint enforcement; it is not friction coefficient or a physical motor setting.

## Current hypothesis and pending work

Jitter is consistent with a policy–actuator–contact feedback interaction. Current local training configuration uses `impratio=10`; viewer uses 100; original90000 training contact conditions remain unverified. Pending: deployed bounds/scales/history/gains/rates verification; saved continuation-source recovery; calibration against robot lag/slip/contact response; isolated reward ablations; independent starts/seeds with vibration, speed/heading, and traversal evaluated together.

Measured joints at 200 Hz support 8–30 Hz; policy targets at 50 Hz use 8–20 Hz. Band RMS includes gait/impact/corrective content. Target occupancy/removal, torque clipping, and physical stop contact are different measurements.

## Source and artifacts

[Controller source](xterra_mjlab/svanm2_moe_stair_sim/controller.py) · [Checkpoint loader](xterra_mjlab/svanm2_moe_stair_sim/checkpoint_policy.py) · [Reward integration](xterra_mjlab/scripts/train_other.py) · [Analysis tool index](tools/README.md) · [Saved contact findings](../docs/mid_evaluation/evidence/task3/contact_findings.json).

Original90000 SHA `440bbb28d554f75db38bfd163351c04ea4a32d9d06764c37b7e6071d41daa5cb`; newest91000 SHA `dec9775d4b368b69964dde679985455d8b723d5af7fb2d24e8798fa4fdd66da4`. Older91000 begins `f74e62bf` and has different rate/LR settings. Raw sessions remain under `tools/results/interactive/`; scripted studies under `tools/results/<study>/`. Flat PPO, HIMLoco, and ISL-port work are separate training tracks.
