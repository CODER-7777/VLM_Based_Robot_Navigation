# How to read the MoE plots — simple English

Added 2026-10-03. These explanations are also shown **directly above the plots in the dashboard pages**. Refresh the browser to see them. Start with [your original 90k flat-ground page](../tools/results/20261002_matched_v1/original90000_flat_viewer_start0/index.html).

## What is command vx, and why is it constant?

`v` means velocity (speed with a direction). `x` is the robot body's forward direction. **`command vx` is the forward speed we ask the robot to achieve.** It is an input to the policy.

In these recorded tests, we ask:

| Simulation time | Request |
| --- | --- |
| 0–3 seconds | Zero forward speed |
| 3–4 seconds | Gradually increase from 0 to 0.30 m/s |
| From 4 seconds until the run stops | Keep requesting 0.30 m/s |

**0.30 m/s means 30 cm per second.** It is a requested speed, not proof that the robot actually achieves it.

We keep it constant so the original and candidate receive the same task. Otherwise, a change in keyboard commands could explain a difference between them. Holding the speed request constant does not hold the joint actions constant: the policy must keep moving the legs and responding to the robot's changing state.

## The three lines in the speed graph

| Line | Simple meaning | How to use it |
| --- | --- | --- |
| **Black: command vx** | “Please walk forward at this speed.” | This is the reference |
| **Blue: body-frame vx** | How fast the robot is actually moving along its own forward direction | Compare with black to check forward-speed tracking |
| **Orange: world vx** | How fast it is moving along the scene's fixed x direction; this is the staircase direction in these tests | Check whether it is advancing along the intended route |

If black is 0.30 and blue is 0.15, the robot is moving forward at half the requested speed at that instant. If blue is near zero, little body-forward motion is happening. A negative value means motion opposite that coordinate direction. A few peaks touching black do not establish good average tracking.

Body and world speeds can differ because the robot turns or tilts. For a simple example, a robot facing 90° away can move forward along its own body at 0.30 m/s while making almost no progress along world x. Read heading and sideways drift alongside the speed graph.

The ups and downs of actual speed can reflect normal stepping, impacts or instability. **This speed graph alone does not prove motor jitter.** The joint-angle traces and frequency analysis examine rapid joint motion more directly.

## Your screenshot: what should you conclude?

The page is `original90000_flat_viewer_start0`: original `model_90000.pt`, flat ground, existing observation timing, centered starting pose.

During **4–30 simulation seconds**, its mean body-forward speed is approximately **0.170 m/s**, compared with the **0.300 m/s** request. So it walks forward, but on average it is slower than requested. The mean world-x speed is approximately **0.158 m/s**.

The maximum body tilt over the whole run is approximately **3.39°**, so this run has no large tipping event. However, it finishes facing approximately **−24.25°** relative to the scene reference and the maximum sideways body deviation is approximately **1.54 m**. It remains upright while drifting away from the requested direction. `flat_completed` means it finished the time horizon without a failure stop; it does not mean perfect speed, direction or absence of jitter.

Those numbers come from [this run's metrics](../tools/results/20261002_matched_v1/original90000_flat_viewer_start0/metrics.json). They describe this run, not a general success rate.

## Read the five motion panels from top to bottom

### 1. Progress: base x

`base` is the main body. `base x` is its position along the scene's x direction, measured in metres.

- Starting at **−1.5 m** means the body begins 1.5 m before the first riser. It does not mean negative speed.
- A rising curve means forward progress along world x.
- A nearly flat curve means little progress along that direction.
- A falling curve means it moves back along that direction.

In stair tests, the first riser is at x=0 and the top platform starts at x=3.6 m. Passing x=0 with the body is not proof that all four feet climbed. Full traversal has separate foot, balance and lane checks.

### 2. Speed: command versus measured motion

Use the black/blue/orange explanation above. Check most of the moving interval, not just a favorable peak. Read the turning and sideways plots when body-forward speed looks acceptable but route progress is poor.

### 3. Height: world z and z above surface

`z` is vertical height. **0.34 m means 34 cm.**

- `world z`: body height above the scene reference.
- `z above surface at base x/y`: body height minus terrain height directly underneath the body's horizontal position.

On flat ground at height zero, the lines overlap, so one may hide the other. On stairs, world height can rise while clearance above the step stays similar.

Read the axis numbers: a graph covering 0.335–0.365 m spans only **3 cm**, even if the curve looks dramatic. During your flat walking interval the variation is smaller than that full startup-inclusive range. A small height change is not automatically a fall.

The “surface underneath” estimate changes abruptly when the body crosses an edge. A jump in that clearance line can come from the surface-height change rather than sudden body movement. Confirm with the continuous world-z curve.

### 4. Angles: tilt and heading

- **Tilt:** how far the body leans away from upright. Near 0° means upright. Large sustained tilt can indicate loss of balance.
- **Heading:** the direction the robot faces around the vertical axis. It can change while the robot stays upright.

Zero yaw-rate command asks it not to keep turning. If heading drifts, direction control deserves investigation. A negative heading is a signed coordinate angle, not a negative reward.

### 5. Lateral offset

This is sideways body displacement from the lane center, in metres. Zero means centered; either sign shows one side of the center. Since requested sideways speed is zero, growing sideways displacement is unwanted drift.

On flat ground, lane departure is not itself a stop condition. The robot can finish `flat_completed` while drifting sideways. Stair lane checks use foot positions and additional conditions, not just this body-offset curve.

## The red dotted line

In stair cases with recorded contact, a **vertical red dotted line** marks the first foot/stair contact carrying more than 1 N normal force. It is a time marker, not a reward or limit.

Flat-ground runs have no stair contact and no such marker. Some older saved PNG titles contain the general caption “red dotted = first foot/stair contact”; that line does not exist in a flat run. Newly generated motion figures use a conditional caption.

## Joint-angle plots: requested, clamped and measured

There are twelve joints, arranged as four legs × hip/thigh/calf. FL/FR mean front-left/front-right; RL/RR mean rear-left/rear-right. Horizontal axis is time; vertical axis is degrees.

| Line | Meaning |
| --- | --- |
| Green: requested | Angle requested by the policy before the final target limit |
| Orange: clamped target | Angle sent to the PD controller after applying that limit |
| Blue: measured q | The simulated joint's actual angle |

Green different from orange means the software removed part of the request. Orange different from blue means the joint is not at its target at that moment. Response time, load and contact can contribute; the gap alone does not prove motor damage.

Look around the first contact: does the target request lift, does the actual joint follow, and is the request limited? Negative calf angles are the model's coordinate convention.

## Torque plots: requested effort versus applied effort

Torque is joint turning effort, in **Nm**. The controller calculates torque from angle and velocity errors; effort limits can then reduce it.

- `unlimited PD torque`: calculated effort before torque limiting.
- `applied torque`: effort actually applied after limiting.
- Gray horizontal lines: allowed positive/negative limits.

A separation at a boundary means clipping. Overlap means no clipping there, though one curve can hide the other. Positive/negative values indicate opposite turning directions. Inspect short bursts around the critical event; averages can hide them.

## Contact and clearance plots

Each color is one foot. The first panel shows summed foot normal forces in N. Near zero means little or no loaded foot contact. This total includes wall-like riser contact, so it does not always mean useful upward support.

The second panel isolates nearly vertical riser contacts. Repeated peaks mean the foot repeatedly pushes against a step face. They deserve checking alongside whether the foot is lifted and whether body tilt increases.

The third panel estimates the foot bottom's height above the surface underneath its center. Positive clearance means above that surface; near zero means close to it. This quantity can jump across stair edges. Small negative values can reflect contact penetration or the height definition rather than an automatic failure.

Normal walking has landing-force peaks too. Ask which feet support the body while another tries to climb.

## Foot paths

These show foot-center x versus z, in metres. Dot color shows simulation time. The black outline is the staircase when present.

Look for forward motion at low height near a riser, then lifting, retreating or repeated attempts. The sphere radius is 2.2 cm: clearing a 10 cm flat top needs roughly 12.2 cm center height, with any desired safety margin added.

This side-view projection hides sideways motion. A drawn intersection is not collision proof; confirm with the named contact records.

## Policy costs and expert weights

These plotted costs are diagnostic values, not the total training reward:

| Quantity | What a higher value means |
| --- | --- |
| Action first-difference cost | Actions changed more between consecutive policy updates |
| Target second-difference cost | Successive target increments changed more abruptly |
| Saturation cost | More of the target request was removed by position limits |
| Gyro stale/fresh difference | Existing and refreshed angular-velocity readings disagree more |

The curves are **unweighted costs**. A cost of 5 with weight −0.01 would give −0.05 before any reward-manager timestep scaling. Evaluation does not train the policy. These costs do not directly measure motor temperature or physical jitter.

The eight expert curves show continuous contributions to the MoE output. A changing weight does not mean a hard switch between single experts.

## Frequency plots

The horizontal axis is **frequency**, not time. 10 Hz means ten cycles per second. The vertical axis shows signal power and uses a logarithmic scale: equal vertical spacing means multiplication, not adding the same amount.

- Left: measured joint motion, sampled at 200 Hz; highlighted band 8–30 Hz.
- Right: target angles at 50 Hz policy updates; highlighted band 8–20 Hz.

More power in the highlighted band means more rapid variation there. RMS gives its typical size in degrees; it is not the maximum joint angle or the full leg swing. Compare the same band and phase across cases. The two panels use different bands; their amplitudes are not an equal-band comparison. Impacts also add rapid components.

## First-contact zoom and flat/stair comparison

The first-contact zoom links foot position, contact force, body angles, joint targets and torque around one event. Its orange foot-position curve is a static forward-kinematics check with the recorded body pose frozen. It is not a prediction of dynamic movement.

The flat/stair comparison uses the same saved policy and commands. Stair collisions are enabled in one and disabled in the other. Horizontal zero is the first stair-contact time in the stair run, not the beginning of the simulation. Curves diverging after contact show the terrain's effect on the whole feedback loop, without uniquely identifying the internal cause.

## Paired starting-pose comparison

Each colored line connects original and candidate results for the same pose. Start 0 is centered; start 1 is −3 cm sideways/−0.02 rad yaw; start 2 is +3 cm/+0.02 rad yaw. Dashed black is the mean of those three pairs.

The columns show rapid joint motion, speed error and target-removal fraction. Lower is usually desirable for these quantities, alongside useful walking. A colored line rising toward the candidate indicates a regression for that quantity and start. All use the same 4–8 s early-motion interval. Three deterministic poses are not statistical confidence intervals.

## What to record in your observations table

| Question | Evidence to write down |
| --- | --- |
| Did it move at the requested speed? | Requested speed, mean measured speed and speed error over the same interval |
| Did it keep direction? | Heading change and sideways drift |
| Did it stay upright? | Tilt and body height, with the axis scale |
| What happened at the first step? | Contacting foot, contact time, foot height and force |
| Did it request and achieve enough lift? | Target/measured joint angles and event foot-height check |
| Were commands limited? | Target removal and torque clipping at the relevant time |
| Did jitter improve? | Same-window, same-band measured joint RMS across matched runs |
| Did it complete the task? | Full traversal, fall, lane exit or incomplete timeout |

Write the observation first, then its possible explanation. Several signals can change together without proving that one caused the others.
