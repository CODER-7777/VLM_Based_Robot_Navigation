# MoE 90k Jitter Audit — Plain-Language Explanation

## Main question and answer

The report asks:

> Why does the MoE 90k robot shake or fail on stairs even when the correct policy
> is loaded?

The report's answer is that the original simulator differed from the deployed
robot, and the observed problems involve the policy, motor control, and contact
with the ground or stairs. It found useful evidence, but it did not identify one
exclusive cause or a successful general fix.

## 1. What was investigated

The investigators used:

- Previously recorded real-robot data.
- Offline simulations using the same MoE 90k policy.
- Controlled comparisons where individual settings were changed.

They did not **retrain the policy**, send new commands to the robot, deploy a fix, or
change firmware during this audit.

The phrase **policy-actuator-contact interaction** describes this feedback loop:

```text
Policy requests joint positions
              ↓
Motors try to reach those positions
              ↓
Feet contact the ground or stairs
              ↓
The robot's movement changes
              ↓
Sensors report the new state to the policy
              ↺
```

A problem anywhere in this loop affects later actions. Shaking therefore cannot
be assigned automatically to the neural network alone.

## 2. What passed verification, what differed, and what remains unknown

The audit compares the original stair demo with the deployed robot's control rules.
Its original heading, "What was wrong or unverified", combines several categories.
It does not mean that every row is a fault or an unverified assumption.
In particular, **the joint-target limit difference is an established mismatch in
this comparison**. Checking that difference does not automatically change the demo.

| Item | Status / scope of evidence | Plain-language explanation |
|---|---|---|
| Policy | Passed the reported replay checks | The same MoE 90k weights were used; checkpoint substitution is unsupported. |
| History order | Final input order verified by audit | Interfaces use different external ordering, but the deployed adapter reverses it internally. |
| Joint target limits | Confirmed mismatch between original demo and reported deployed bounds | The original demo allowed targets that the deployed controller would clamp. |
| Observation/action contract | Audit reports parity checks passing in its corrected implementation | Ordering, scaling, interpretation and previous-action feedback must match; this does not establish physical motor-model accuracy. |
| Command shaping | Different behavior identified | Latched keyboard commands differ from joystick deadzones, gradual changes and release behavior. |
| Timing | Separate rates documented; exact hardware motor timing remains partly unverified | Policy updates, PD control, physics integration and delivery delay are distinct. |
| Sensors | Refresh issue identified in original demo; audit reports correction | Observations must describe the intended simulation state. |
| Reset | Incomplete original reset identified; audit reports correction | Resetting only position and velocity can leave controls and solver state behind. |
| Invalid actions | Original handling issue identified | Replacing invalid output with zeros can hide an inference failure. |
| Stair validation | Original test insufficient | A short approach toward stairs does not demonstrate traversal. |
| Physical model | Partly unmeasured / unresolved | Motor, payload, friction, backlash and contact properties still need physical validation. |

### The policy row is not an error

The original REPORT.md heading says **wrong or unverified**, but its table also
includes things that were checked successfully. This row:

| Policy | Original MoE 90k | Same weights confirmed by replay; no checkpoint substitution |

means the audit ruled out the following explanation:

> The bad behaviour happened because somebody accidentally used a different
> checkpoint.

Replay showed that the corrected audit used the same learned weights. The policy
may still produce unsuitable commands for the task, but it was not secretly
replaced by another checkpoint.

### Large target-limit mismatch

The original demo allowed the calf target up to `+0.50 rad`; the deployed
controller used `-0.88776 rad`. The difference is about `1.38776 rad`, or 79.5°.

Therefore, the same raw network output can become a different commanded target in
the two systems. This mismatch alone was not proven to cause every failure.

### Verified does not mean corrected, physically validated, or proven causal

| Question | Answer and evidence limit |
|---|---|
| Were original-demo and deployed calf bounds different? | Yes. Original `controller.py` has +0.50000 rad; the audit reports -0.88776 rad for deployment, supported by the previously inspected saved target traces. |
| Did checking the values fix the original demo? | No. On 2026-09-25, the local original `TARGET_MAX` still contains +0.5000 rad for every calf. |
| Where does the report say the correction was made? | In its separate corrected audit simulator. That implementation was not found in the local copy during prior inspection. |
| Are those software bounds independently measured physical joint stops? | No such conclusion follows; software target limits and mechanical range are different quantities. |
| Did the original 90k training use the demo limits? | Not established; historical training configuration and action processing must still be traced. |
| Is this mismatch proven to cause the jitter? | No. It can change control behavior, but the audit did not isolate it as the root cause; failures occurred under both limit profiles. |

Source: [original controller](../xterra_mjlab/svanm2_moe_stair_sim/controller.py),
`TARGET_MAX` near line 32, and [audit comparison](../moe_jitter_audit_20260921/REPORT.md).
The deployed adapter's original contract is not currently available locally for
fresh direct inspection; that side of the comparison relies on the saved audit
and its artifacts. Do not confuse this provenance limit with saying the report
never established a target-bound difference.

Observation to retain: **The target-limit mismatch is a confirmed audit finding;
its contribution to jitter is still an open causal question.**

### The original stair test was insufficient

Starting 1.5 m before the stairs and running for one second at a requested
0.15 m/s covers only about 0.15 m under perfect tracking. It cannot demonstrate
stair contact or traversal. The audit instead checks first contact, all-feet
traversal, stalls, lane exits, and tipping.

## 3. Contact and timing

- A 50 Hz policy produces one new neural-network action every 20 ms.
- A 200 Hz external PD controller recalculates torque every 5 ms.
- The physics timestep determines how often MuJoCo integrates motion.

These rates are related but not identical. Reducing the physics timestep does
not automatically increase the policy or PD-control rate.

MuJoCo normally requires a positive contact time constant to be at least twice
the simulation timestep. With a 5 ms timestep, asking for a 2 ms contact time
constant effectively reaches a 10 ms lower bound. Geometry priority can also
decide which contact friction and solver values take effect.

Inference: simulator parameters must be verified from effective behaviour. A
smoother-looking video is not proof of a more accurate physical model.

## 4. Hardware evidence

Two recorded runs were examined:

| Recording | What it can establish |
|---|---|
| About 20 samples/s | Shows the large tipping incident, but cannot resolve the full 8–30 Hz band. |
| About 200 samples/s | Supports analysis of rapid joint and target motion. |

At 20 samples/s, the Nyquist frequency is about 10 Hz. Frequencies above that
cannot be reconstructed reliably.

The later recording lacked synchronized terrain labels, so a high-oscillation
window cannot be called a stair or flat-ground interval from joint signals alone.

### Important terms

| Term | Meaning |
|---|---|
| 8–30 Hz | The frequency range chosen to measure rapid oscillation. |
| RMS | A measure of signal magnitude over an interval, not its maximum excursion. |
| Measured-angle RMS | Rapid oscillation of actual measured joint positions. |
| Target RMS | Rapid oscillation of the requested joint positions. |
| p99 interval | About 99% of measured intervals were at or below this value. |
| Sensor/action age | How old the sensor reading or action was when used. |

Measured joint oscillation was approximately 0.19–0.45° RMS per joint in the
analysed motion samples. Target oscillation was larger, approximately 0.63–1.84°.
These values describe the selected frequency component, not the full walking
motion.

Target and measured oscillation had a strong Spearman association of 0.962.
Timing and age measures had much weaker associations. This supports examining
the target/closed-loop response, but correlation does not determine which part
caused the problem.

### What is the practical use of the oscillation measurement?

It provides a quantitative reference and a direction for investigation. It does not
identify the root cause by itself.

| Observation | Practical use | Limit of the conclusion |
|---|---|---|
| Measured joint motion contains 0.19–0.45 degrees RMS in the selected band | Quantify rapid motion separately from the much larger leg swing; compare joints and matched trials | These are per-joint band measurements, not maximum angle or total walking movement |
| Sent targets contain larger band variation, 0.63–1.84 degrees RMS | Inspect raw actions, target processing, saturation and their interaction with contact and feedback | Sent targets are processed commands, so this does not isolate the neural network or rewards as the cause |
| Measured band magnitude is smaller than target magnitude | Investigate tracking and the physical/controller response to rapid requests | Motors and dynamics may attenuate rapid changes, but these aggregate numbers do not prove the mechanism, healthy motors or an acceptable controller |

A teaching example: a leg may swing through tens of degrees while only a small
part of its variation lies in the 8–30 Hz band. The reported RMS describes that
selected component, not the full swing. It is not a universal threshold defining
safe, harmful or acceptable jitter; normal gait harmonics and impacts can contribute.

For our reward project, measure both target and actual-motion oscillation before
and after training under the SAME command, terrain, sampling/filter method and
comparable upright movement phase. If target oscillation falls while measured motion
and task performance improve, that is useful evidence for the candidate. If only
targets become smoother, inspect physical response. If the robot simply slows,
stalls or falls, a lower oscillation score does not count as a fix.

These saved hardware ranges are a historical reference. Because this recording
lacks synchronized terrain labels, they are not automatically the baseline for
our specific 10 cm stair test. Establish that baseline separately.

Suggested observation-table entry:

> Rapid variation is present in both sent joint targets and measured motion, with
> larger variation in the targets. This motivates checking target generation and
> the motor/contact feedback response together. Use both signals as outcome metrics
> in matched experiments, alongside tracking, falls and full stair traversal.

## 5. Saturation, velocity, and fault fields

Saturation means that a requested target reaches an allowed boundary and is
clamped there.

| Calf joint | Fraction of moving samples at a deployed limit |
|---|---:|
| Front left | 17.7% |
| Front right | 20.0% |
| Rear left | 19.4% |
| Rear right | 64.8% |

The rear-right asymmetry needs investigation. A software target at its limit
does not prove contact with a physical mechanical stop.

Reported `dq` closely matched velocity calculated from the measured `q`. The
record provides no evidence for an obvious velocity sign or unit error.

Nonzero motor `fault` values appeared in repeated telemetry rows. Their firmware
meaning was not decoded. They neither prove a damaged motor nor prove harmless
status; actuator involvement remains unresolved.

## 6. Thigh-calf coupling

The belt transmission matrix for one leg is:

```text
J = [[8, 0,  0],
     [0, 8,  0],
     [0, 8, 16]]
```

At `kp=20` and `kd=0.7`, the effective stiffness is:

```text
K_effective = [[20,  0,  0],
               [ 0, 25, 10],
               [ 0, 10, 20]]
```

The off-diagonal `10` values mean that thigh and calf response are coupled. A
calf error can contribute to thigh torque, and a thigh error can contribute to
calf torque. The coupled model matched estimated hardware torque better than a
diagonal independent-joint model, supporting retention of the coupling.

The audit still could not establish the exact hardware torque-saturation law.

## 7. Action clipping and MoE routing

The target pipeline is:

```text
raw policy action
        ↓
clip raw action to [-6, 6]
        ↓
scale and add nominal standing position
        ↓
clamp to deployed joint-target bounds
```

The previous-action observation keeps the clipped raw action from before the
final target-bound clamp. Altering that convention changes what the trained
policy sees.

The MoE encoder uses eight continuously weighted experts. It does not make a
hard selection of one expert at a time. The report therefore does not support
the claim that abrupt expert switching causes jitter.

All 30,175 recorded policy outputs were reproduced from the recorded histories
within tolerance. Wrong weights and reversed history are unsupported causes.
Correct inference does not imply that the learned behaviour is sufficient for
stair climbing.

## 8. Terrain and smoothing experiments

The audit completed 120 offline rollouts. The main terrain comparison used two
deterministic starts per case, so the results are examples rather than reliable
success-rate estimates.

Main findings:

- Flat cases stayed upright, though sideways commands showed yaw drift.
- Rough 3 cm and several downhill cases traversed.
- Uphill cases were inconsistent.
- Neither baseline start completed a valid ascent at 10, 15, or 18 cm.
- Some failures were stalls or lane exits rather than falls.

### Smoothing experiments

| Change | Outcome |
|---|---|
| 20 ms target filtering | Flat oscillation fell by about 7%, tracking worsened, and both tested 15 cm ascent runs tipped. |
| 40 ms target filtering | Flat oscillation increased by about 47%. |
| Smaller physics timestep | Behaviour changed substantially, showing numerical sensitivity rather than proving a hardware fix. |

A filter introduces delay. It can make targets look smoother while weakening
rapid balance and foot-placement corrections. Lower jitter alone is therefore
not a sufficient success metric.

## 9. Proposed training experiments

The report recommends validating the controller and actuator model before
attributing everything to rewards. If fine-tuning is justified, resume from the
90k checkpoint.

Existing training already reports penalties for action rate, foot slip, foot
clearance, soft landing, and joint limits. Their formulas and actual weighted
contributions must be measured before adding duplicates.

### Candidate A — physical-target second difference

```text
q_cmd[t] - 2*q_cmd[t-1] + q_cmd[t-2]
```

This measures how sharply the target's direction or rate changes. A constant
increment such as `0°, 5°, 10°` gives zero; a reversal such as `0°, 5°, 0°`
does not. Penalizing it may reduce rapid reversals, but too much can suppress
necessary stair-lifting motion.

### Candidate B — saturation pressure

```text
q_raw_target - q_cmd
```

This measures how much of the requested target was removed by the deployed
joint-limit clamp. Penalizing it may teach the policy to request reachable
positions. It remains a proposed experiment, not a proven fix.

## Supported conclusions and next questions

| Supported observation | Next investigation |
|---|---|
| Recorded policy outputs reproduce correctly | Look beyond checkpoint loading. |
| Original demo and deployed controls differ | Establish one consistent evaluation contract. |
| Targets oscillate and frequently saturate | Inspect applied targets, target limits, and reward contributions. |
| Actuator/contact properties remain uncertain | Validate assumptions before blaming rewards. |
| Baseline stair ascent failed in reported trials | Measure traversal, tracking, stalls, lane exits, and falls. |
| Smoothing did not reliably fix the task | Test every change as a controlled experiment. |

Five passing contract tests mean that particular software-interface checks
passed. They do not mean the robot passed the stairs. Similarly, 120 completed
rollouts means the experiments ran to recorded outcomes, including failures.

