# Mid-evaluation speaking script

This script follows the **12 pages of [your presentation PDF](UGP_VLM_BASED_ROBOT_NAVIGATION.pdf)** in their actual order. The paragraphs under each slide are the words to speak. Figure cues in italics are optional actions. Questions and backup answers follow the closing; they are separate from the main script.

The main script is about 3,800 words: roughly 25–30 minutes at a steady speaking pace, before questions. It is the detailed version; a shorter presentation requires reducing the spoken explanation.

## Slide 1 — Introduction

Good morning, sir. I am Mansoju Vivekananda, and my project is Physics Informed VLM-Based Robot Navigation. I am working under Professor Tushar Sandhan, with Toshith as my co-mentor.

The overall goal is to make a quadruped robot navigate an indoor environment using visual information and language instructions, while also accounting for how the robot actually moves and interacts with the floor.

For this mid-evaluation, I have divided my progress into four tasks. First, choosing a suitable simulator. Second, studying and improving the GQFT motion-estimation pipeline. Third, investigating jitter in an RL-based locomotion policy. Fourth, repairing an indoor scene used with the RxR dataset and exploring how to render useful observations from it.

These components are still being developed and evaluated separately. Connecting them into a complete language-guided navigation system is remaining work. I will explain what I tried, what the analysis showed, which fixes are present, and where I need your feedback.

## Slide 2 — Task 1: Finding the right simulator

For the first task, I needed an indoor simulator that could show a detailed environment and also run a quadruped controller. My laptop has an RTX 3050 with four gigabytes of video memory, so the hardware budget was a major constraint.

I compared Genesis, MuJoCo, Habitat, Isaac Sim, and game-engine options. The table shows the practical trade-offs I considered. This is a feasibility comparison; I have not run a complete measured benchmark across all these engines.

The working decision was to use Genesis for the indoor visual prototype and Go2 integration, and MuJoCo for the detailed locomotion and contact experiments in Task 3. These are currently separate experiments, and their contact behavior still needs to be checked before transferring conclusions between them.

*Point to the office image and then the flowchart.*

The office prototype exposed a specific problem. Processing the detailed office as collision geometry reportedly caused an out-of-memory error. For the prototype, I disabled collisions on the detailed visual mesh and used a plane to support the robot. I also connected the pretrained policy through the observation interface and joint mapping.

This allowed the visual prototype to proceed. However, the furniture in that configuration does not provide obstacle collisions. So I cannot use this demonstration as evidence that the robot can safely navigate around furniture.

My next step is to add simplified collision shapes for the furniture and measure memory use, initialization time, runtime, and collision behavior. I would like your guidance on how detailed these collision shapes need to be for our first navigation experiments.

## Slide 3 — Task 2: GQFT approach and Transformer

The second task is about estimating camera motion from images and projecting the resulting path into image coordinates. The objective is to reproduce the supplied GQFT pipeline and then study changes that might reduce trajectory error.

*Follow the upper diagram from consecutive images to ground projection.*

First, consecutive camera images go into SEA-RAFT. It estimates optical flow, which tells us how image locations move between frames. SEA-RAFT is frozen in this pipeline, meaning its weights are not updated during our GQFT training. Its paper was published at ECCV in 2024.

A CNN then converts the flow into a grid of learned features. Each location in this grid contains information extracted from a region of the flow image. Pooling summarizes this grid into a compact vector that the Transformer can process.

The original model uses both mean pooling and max pooling. Mean pooling averages each feature across all spatial locations, giving every location equal weight. Max pooling takes the largest value for each feature across those locations. For a simple example, if one feature has values two, four, six, and eight at four locations, mean pooling gives five and max pooling gives eight.

Mean pooling provides an overall summary, while max pooling preserves the strongest activation for each feature. These operations are applied to learned CNN features, rather than directly averaging the raw optical-flow arrows. The two summaries are joined and passed through a learned projection to produce one 256-dimensional vector per flow step.

Why did we try attention? Different regions can provide different motion information. For example, a nearby surface and a distant surface can show different flow during the same camera movement. Some regions may also contain weak or uncertain evidence. Our hypothesis was that giving every location equal weight might dilute useful regional features.

The original CNN already receives image-coordinate information. The change we tested was to make the spatial aggregation learn which regions deserve more weight.

In the Attention variant, a small network produces a score for each location in the CNN feature grid. Softmax converts those scores into weights that add up to one. We multiply the features by these weights and sum them. So, instead of a fixed equal-weight average, the model learns a weighted summary during training.

We replace only the mean-pooling branch and retain max pooling. This lets us combine the learned regional summary with the strongest feature activations, while keeping the Transformer input size the same. The baseline is mean plus max; the candidate is attention-weighted pooling plus max.

This is spatial attention within one flow frame. The causal Transformer performs temporal attention across frames, which I will explain next. The experiment tests whether learned regional weighting helps motion estimation; its mixed results are shown on the next slide.

These features then enter the causal Transformer shown below. Here, causal means that a timestep can use the current and previous timesteps, but cannot look at future frames. It is a description of the attention rule, rather than a separate branded model name.

The encoder has four layers, eight attention heads, and 256-dimensional features. Its job is to select useful information from the motion history. Spatial attention decides which image regions matter; temporal attention decides which earlier observations matter.

The prediction heads estimate displacement increments, which are added to form a path. The optional yaw head supervises heading change. The pixel query is used later in projection and validity checking; it is not an input token to this Transformer.

I explored attention and yaw supervision because regional-flow analysis showed useful heading information. An exploratory yaw probe reduced its error from about 0.157 to 0.122 radians. That supports studying regional aggregation, but it does not by itself prove an improvement in the complete trajectory model.

Historical flip-augmentation attempts are also documented, but they are discontinued and excluded from the next controlled comparison.

## Slide 4 — Task 2: Comparison results

To compare the models, I used both ADE and FDE. ADE is the average error along the predicted path. FDE is the error at the final point. Here, both are measured in pixels, and lower values are better.

The validation comparison uses the same 104 windows, one query per window, and a history length of 24. The saved test records use a separate protocol. I compare model rows within each split, rather than treating the validation and test columns as the same experiment.

In validation, Attention reduces ADE from 11.263 to 10.283 pixels, which is about an 8.7 percent improvement. However, on the saved test records, Attention alone performs worse than the baseline.

Attention plus Yaw has the best saved test results in this table. Its ADE is 8.783 pixels and its FDE is 13.323 pixels. Compared with the baseline, these are improvements of about 8.8 and 15.9 percent. But its validation ADE is worse, so this result does not establish that it is the best model in every setting.

*Point to the two graphs.*

The left graph shows error at different points in the trajectory. The yaw variant can have larger intermediate errors while still ending closer to the reference. This is why I report average path error and endpoint error together.

The right graph compares motion families. Attention does not improve every family. For constant-arc motion, ADE increases from about 6.96 to 8.29 pixels. Attention also fails the existing history-selection requirement, meaning that lower average error alone is not enough for the intended selection task.

The takeaway from this analysis is that I need a fixed evaluation protocol and motion-specific diagnosis before choosing an architecture. The saved test improvement also needs a controlled experiment to separate the effect of yaw supervision from other training differences.

## Slide 5 — Task 2: Episode failures and analysis-driven fixes

These episode images help explain errors that a single average score can hide.

*Point to the upper-left image.*

In episode 837, leg 7, the path is nearly straight. The orange prediction follows roughly the right direction but ends short of the traversed-path reference. This suggests that path length and motion scale need inspection.

*Point to the lower image.*

In episode 1285, leg 23, the reference path is curved. The predictions differ in curvature and endpoint position, so we need to inspect heading change as well as displacement.

*Point to the upper-right image.*

Episode 837, leg 11, is a stronger turning failure. The orange path departs visibly from the traversed route and enters the extended canvas below the image.

These are historical overlays. The audit found problems in the old tools, so I use them to illustrate behavior needing investigation, rather than as proof of a model improvement. In particular, a line labeled baseline is not necessarily a verified released-baseline checkpoint.

The audit identified three concrete pipeline problems. First, cached flow was already normalized, but some tools divided it by the grid dimensions again. That suppressed the motion values. The correction preserves the normalized flow and masks invalid vectors.

Second, the simulator's camera-pitch sign and the model's geometry convention disagreed, and the anchor convention was inconsistent. The correction makes the sign conversion explicit, checks the camera configuration, and uses the trained anchor.

Third, an augmented checkpoint had been labeled baseline. The loader now checks the architecture and loads weights strictly, so incompatible weights produce an error instead of being silently accepted.

There was also a supervision issue. I tested the projection using exact ground-truth motion. Even with perfect motion, three of the 104 windows disagreed with the pixel labels. The labels and projector used different camera-height references. When those heights were matched, the maximum discrepancy dropped from 65.525 pixels to about 0.000126 pixels.

That is a geometry diagnostic, rather than a new trained-model result. The optional fixed-rig supervision mode is implemented but off by default. Paired training is still pending.

My next experiment is to keep the Attention architecture fixed and change only the supervision convention. I also need to regenerate these episodes through the corrected adapter, with the checkpoint and camera settings recorded. This will help separate model error from projection and evaluation error.

## Slide 6 — Task 3: RL and the MoE student actor

The third task focuses on locomotion jitter in the SvanM2 robot simulation. Before explaining the experiments, I will explain the policy we are using.

Reinforcement learning means learning through interaction. The policy observes the robot, chooses actions, and receives feedback based on the resulting movement. During training, the learner updates the policy to improve its behavior. Our objective is to follow velocity commands while maintaining balance, foot support, and smooth joint motion.

MoE stands for Mixture of Experts. In this architecture, several learned feature branches process the same recent observation history. A gating network gives each branch a weight, and their outputs are blended before one shared actor produces the actions.

*Follow the upper architecture diagram.*

The student receives five observations, each containing 45 values, giving a 225-value history. These observations include body motion, the command, joint positions and velocities, and previous actions.

The expert branch produces eight feature vectors, each with 32 values. The gating branch produces eight weights that add up to one. These are soft weights, so the network blends expert features rather than choosing just one expert.

The blended 32-value vector is combined with the latest 45-value observation. The shared actor then outputs 12 actions, corresponding to the robot's 12 joints. We have not established that individual experts correspond to named behaviors such as walking, turning, or climbing.

Student refers to the deployable policy in the teacher-student learning framework. The CTS reference was published in IEEE Robotics and Automation Letters in 2024; the eight-expert structure here comes from the implementation we inspected.

The actions are scaled and limited to produce joint-position targets. A coupled PD controller converts target error into torque. The policy runs at 50 hertz, or once every 20 milliseconds, while the PD and physics loop runs at 200 hertz, or once every five milliseconds.

The lower diagram shows how training uses rewards to update the policy. During deployment or these fixed-policy evaluations, the learned weights stay fixed.

## Slide 7 — Task 3: Attempts and the contact intervention

The problem was that the robot showed joint oscillation, and reducing a training penalty did not consistently produce better movement. I needed to check the whole loop: policy actions, target limits, actuator response, and foot contact.

I tried action-rate penalties, target-smoothness and saturation costs, and probes involving gains, sensing, and delay. One continuation, called bundle90500, reduced the training second-difference cost by about 6.57 percent and the saturation cost by about 59.65 percent.

However, it completed zero out of 12 staircase trials. So the reward statistics improved, but they did not establish successful stair locomotion.

The next analysis found differences between training and viewer contact settings. This motivated a controlled test of MuJoCo's impratio setting. For each comparison, I held the policy, gains, and target limits fixed and changed the ratio from 100 to 10.

In plain language, impratio affects how firmly the contact solver handles frictional motion relative to normal contact. With elliptic friction cones, it is the ratio of frictional to normal constraint impedance. It changes the numerical contact response without changing the physical friction coefficient.

*Point to the joint-vibration and speed graphs.*

Across the four primary flat-ground comparisons, joint-band RMS decreased by about 63.5 to 70.5 percent. RMS here summarizes the size of oscillation in a selected frequency range.

With the current corrected target bounds, the six matched policy-and-start stair cases improved from zero completed cases to three. That is encouraging simulation evidence, but still a small set of cases.

There was also a trade-off. For the original policy, sideways speed decreased from 0.175 to 0.148 metres per second. So lower vibration did not improve every aspect of movement.

The next step is to measure vibration together with speed error, heading, target clipping, foot support, and stair completion. Improvement on the physical robot remains unverified.

## Slide 8 — Task 3: Audit fixes and dashboard analysis

The audit also found a mismatch in the software target limits. The historical simulator allowed the calf target up to positive 0.5 radians, whereas the corrected upper target is negative 0.88776 radians. That is a difference of almost 80 degrees.

The hip targets were also tightened from plus or minus 1.0472 radians to plus or minus 0.735 radians. Both of these important corrections are present in the current controller.

These are software limits on requested joint positions. They bring the controller closer to the recorded deployment contract; they do not mean that I changed the robot's mechanical stops or firmware limits.

I also checked whether the wrong policy or observation history could explain the behavior. Replaying 30,175 recorded policy outputs reproduced them closely. This did not support wrong weights or history ordering as the explanation. The current analysis therefore preserves the raw-action history and the coupled PD convention.

The audit contains additional checks involving command shaping, sensor freshness, reset behavior, timing, and invalid outputs. Some were corrected in the separate audit simulator. Full parity in the current viewer is still pending, so I am distinguishing those from the two limit corrections confirmed in the current controller.

*Point to the upper joint traces.*

For ongoing analysis, each interactive attempt records commands, requested targets, limited targets, measured joint angles, torques, and foot contacts. The dashboard lets me compare what the policy requested, what the controller allowed, and what the robot actually did.

In these plots, blue shows the requested target, orange the limited target, and green the measured angle. The contact marker lets me align the traces to the first stair interaction. I then inspect approach, impact and recovery, ascent, and settling separately.

In the reviewed interactive attempt, joint-band RMS rose from about 0.14 degrees during approach to 0.58 degrees around impact and recovery. Calf targets were also frequently clipped. This focuses the next investigation on contact recovery and target reachability. Clipping alone does not prove that a physical joint stop was hit.

The later saved-data audit verifies full-foot ascent in this attempt at 16.265 seconds. It includes operator steering and variable commands, so it is one verified operator-assisted simulation ascent. To test the cause of an improvement, I need repeated runs from the same start, with the same command, checkpoint, gains, and limits, changing one setting at a time.

## Slide 9 — Task 4: Repairing an RxR scene

The fourth task is about improving the indoor scene used for navigation experiments. RxR stands for Room-Across-Room. It is a vision-and-language navigation dataset using Matterport3D environments, which can be loaded in Habitat. The RxR paper was published at EMNLP in 2020, and Habitat at ICCV in 2019.

My work here focuses on a selected kitchen scene, rather than changing the entire dataset or its language annotations. The repaired scene is a separate derivative used for these experiments.

The scanned scene contains distorted objects, broken surfaces, and texture artifacts. These make it difficult to inspect object shape and placement clearly. My approach was to compare the scene with reference photographs, fit replacement geometry, preserve materials where available, and inspect the result from calibrated cameras and room views.

The analysis led to specific fixes. Incorrect shape or support position led to fitting changes. Material errors on child meshes led to handling the object hierarchy explicitly. A missing handset and dock led to restoring the active geometry and correcting object selection.

*Point to the two panoramas.*

The upper panorama is made from the original dataset photographs. The lower panorama is a render of the repaired polygon scene. They share a calibrated viewing position, which helps inspect placement and appearance. They are different representations, so this is a photographic-reference comparison rather than an untouched-mesh before-and-after test.

The revision shown in this slide records 23 calibrated comparisons and 30 room or model selections. The toaster retains its 11 parts and original PBR materials. PBR means physically based rendering: the materials describe properties such as colour, roughness, and metal appearance for use under lighting.

There are still scan gaps and approximate substitute shapes. The next step is to evaluate silhouette, scale, support position, missing surfaces, and material appearance from fixed views. Better-looking objects alone do not establish better navigation performance.

## Slide 10 — Task 4: Gaussian RGB-D rendering

Alongside the polygon-scene repairs, I explored a separate Gaussian rendering pipeline. The objective is to generate camera observations while keeping collision and navigation geometry lightweight.

*Follow the diagram from navigation action to synchronized export.*

The navigation side provides the camera pose. A calibrated bridge converts the pose and camera settings for the Gaussian renderer. The renderer produces colour, expected depth, and opacity information, and these are exported with matching camera and frame information.

The idea is to use simple geometry for movement constraints and a richer representation for visual observations. This bridge currently concerns a static navigation agent; full articulated-robot coupling is still pending.

3D Gaussian Splatting represents appearance using many small, overlapping Gaussian elements. Its foundational paper appeared in ACM Transactions on Graphics at SIGGRAPH in 2023.

Earlier renders had floating and irregular corner artifacts. That analysis motivated dense sampling on fixed surfaces and appearance refinement. Missing room coverage then motivated an expansion across the kitchen.

The expanded representation contains about 4.378 million Gaussians. One saved frame had about 99.01 percent valid depth, and the rasterization kernel took about 12.06 milliseconds.

Those numbers need careful interpretation. Valid depth means most pixels received a usable depth value; it does not prove that the depth is geometrically correct. The kernel time covers one rendering stage, rather than the complete observation pipeline.

Earlier held-out views had weak PSNR values of about 7.28 and 10.48 decibels. PSNR measures image agreement, and higher is better. These results showed that looking good from reference cameras did not guarantee accurate unseen views. The final expanded model's held-out accuracy remains unmeasured.

My next step is to fix a set of unseen cameras and evaluate image agreement, depth accuracy, and complete-pipeline latency separately from coverage.

## Slide 11 — Task 4: Sample before-and-after pictures

These pictures show the object repairs inside the actual room, using a shared camera for the earlier saved mesh and the repaired scene.

*Point to the large image on the left.*

In the toaster area, the earlier mesh has distorted object shapes and broken surface appearance. In the repaired view, the toaster and nearby containers have more clearly defined geometry. The original toaster materials were retained instead of replacing the object with a single generic surface.

*Point to the upper-right pair.*

Around the sink, the repaired objects, including the paper-towel holder and tap, are easier to inspect. However, the surrounding wall and cabinet still have missing or irregular regions. This shows that object replacement does not automatically repair the entire scan.

*Point to the lower-right pair.*

The corner comparison similarly makes the individual props easier to distinguish from the distorted scanned geometry. These views help identify remaining placement and shape differences before further changes.

The home-tour comparison keeps the same camera when switching versions and supports side-by-side inspection while walking. Its before view is an earlier saved mesh, rather than a verified untouched original dataset mesh. Its browser textures were reduced to allow both scenes to load, so geometry and placement are more reliable comparison points than sharpness alone.

These are polygon and PBR renders. They are separate from the Gaussian experiment on the previous slide. The pictures demonstrate inspectable scene changes, but I still need geometric checks and navigation experiments to measure their practical benefit.

## Slide 12 — Closing and feedback

To conclude, Task 1 established a working visual simulator prototype, with furniture collisions still to be added and evaluated.

Task 2 produced model comparisons and identified flow, camera, checkpoint, and supervision inconsistencies. The next step is a controlled supervision experiment and regenerated episode evaluation.

Task 3 corrected important joint-target limits and found a contact-setting intervention that reduced simulated vibration. Remaining work is to verify the full controller contract and check whether the improvement preserves tracking and transfers to hardware.

Task 4 produced scene repairs, calibrated comparisons, and a separate Gaussian observation pipeline. Held-out visual and depth quality, collision validity, and navigation benefit still need evaluation.

The repository contains the code, analysis, retained failures, and task-wise documentation supporting these results.

I would especially like your guidance on the next supervision experiment for GQFT, whether locomotion calibration should come before more reward changes, and which scene-quality checks matter most for the first navigation integration.

Thank you, sir. I am happy to discuss the results and the next experiments.

## Genuine questions to ask sir

Choose two or three based on time. These ask for decisions that would change the next experiment.

### 1. Task 2 — Decide the next controlled experiment

**Say:** “Sir, the exact-motion test still shows a projection mismatch in three validation windows. Should I first keep the Attention model fixed and compare the original supervision with fixed-rig supervision, before trying more architecture changes? I would retain the original benchmark and report the alternative protocol separately.”

**Why this is useful:** The answer sets the next training priority. Adapter fixes are implemented, but the paired supervision experiment has not been run. The unresolved question is whether consistent labels help the learned model, not just the oracle.

### 2. Task 3 — Decide between calibration and retraining

**Say:** “Sir, changing the contact ratio reduced simulated vibration, but sideways tracking became worse in one comparison and the hardware benefit is still unverified. Should I prioritize actuator-delay and contact calibration before another reward-based retraining attempt? Which controlled measurement would you consider most useful to distinguish these causes?”

**Why this is useful:** This asks how to identify the remaining cause. It acknowledges that improved smoothness alone is insufficient, and avoids treating a simulator parameter as a proven hardware repair.

### 3. Task 4 — Define what counts as a useful repaired scene

**Say:** “Sir, the repaired scene is easier to inspect, but high depth coverage does not establish correct geometry. For the first navigation experiment, should I prioritize collision and depth consistency, or object appearance? What minimum checks would you expect before I use this scene to compare navigation methods?”

**Why this is useful:** The answer defines an acceptance criterion for integration, rather than simply asking whether the pictures look good.

### 4. Task 1 — Optional question about collision detail

**Say:** “Sir, to stay within the four-gigabyte memory budget, I plan to use simplified furniture collision shapes. Would that be sufficient for our first indoor navigation study, or are there particular contacts and obstacles where I should retain more detailed geometry?”

**Why this is useful:** The answer determines how much scene modelling is needed and which collision tests to prioritize.

### 5. Overall project — Optional question about scope

**Say:** “Sir, these four components are still evaluated separately. For the next milestone, would you prefer that I first demonstrate one complete navigation episode with a fixed controller, or finish the controlled GQFT and locomotion experiments before integrating them?”

**Why this is useful:** This makes the research-versus-integration trade-off explicit and helps set a realistic next deliverable.

## Supervisor feedback after the mid-evaluation

Sir advised connecting the VLM, trajectory component and RL into one navigation system, and researching masked attention in GQFT to reduce unreliable evidence. These are next directions, not completed improvements. The exact intended mask is still to be clarified. [Integration plan](../docs/INTEGRATION_PLAN.md) · [Controlled masking plan](../Task_2/MASKED_ATTENTION_PLAN.md).

**Explanation to speak in a follow-up:** “Based on your feedback, my next direction is to connect the components. The VLM will identify the destination from the instruction and images. GQFT will estimate the observed camera motion. A local navigation layer will combine the goal, motion estimate and geometry to produce velocity commands, which the existing RL policy will execute. In parallel, I will investigate masking unreliable regions in GQFT's attention and compare it against the current model. The precise mask and its benefit still need to be established.”

## Backup answers for likely follow-up questions

### What are mean pooling and max pooling?

“They summarize the CNN feature grid. Mean pooling averages each feature across locations with equal weight. Max pooling keeps the largest value for each feature. For feature values two, four, six, and eight, the mean is five and the maximum is eight. The model combines both summaries into a motion token.”

### Why did you implement attention-based pooling?

“We wanted to test whether giving more weight to informative regions improves motion estimation. A small network learns spatial scores, softmax turns them into weights, and those weights produce a weighted feature summary. We replace the equal-weight mean branch and keep max pooling. Regional-flow analysis supports investigating this idea, and matched validation ADE improves, but the saved test and turning results are mixed.”

### Why is the Transformer called causal?

“Because each step can attend only to the current and earlier observations. Future frames are masked. It processes motion features from optical flow, rather than language tokens.”

### Are the eight MoE experts eight different gait controllers?

“No. In this implementation they produce learned feature vectors, which are blended before one shared actor predicts joint actions. We have not established a named gait role for each expert.”

### Have the calf and hip corrections actually been applied?

“Yes, the current controller contains the calf upper-target limit of minus 0.88776 radians and hip limits of plus or minus 0.735 radians. Those are software target clamps. Full parity with all audit corrections, and a measured hardware improvement, remain pending.”

### Have you solved the locomotion jitter?

“I have reduced the measured vibration in controlled simulation comparisons. There is still a tracking trade-off, failures remain, and the physical-robot improvement is not verified.”

### What does impratio change?

“It changes the contact solver's frictional-to-normal impedance ratio, most directly for elliptic friction cones. It changes numerical contact behavior without changing the physical friction coefficient.”

### Is 99.01 percent depth coverage a reconstruction-accuracy result?

“No. It means that almost all pixels in one saved frame received valid depth. I still need comparison against reference geometry or measured depth to establish accuracy.”

### Is the full VLM navigation system complete?

“No. The current progress is on its simulation, motion estimation, locomotion, and scene-observation components. Language-guided planning and integration into a complete navigation evaluation are remaining work.”

### Does the PDF show the latest appliance revision?

“The slide's numerical mesh evidence is the saved v6 record. A later v7 refinement also exists: it repairs exported tea-set and metal materials, refines appliance shapes, and corrects the tea-tray support position. I would show its saved comparisons separately rather than relabeling the older screenshots as v7.”

## Evidence behind the script

- Actual slide order and pictures: [12-page PDF](UGP_VLM_BASED_ROBOT_NAVIGATION.pdf).
- Task 1 scope and collision limitation: [simulator README](../Task_1_Simulator_Evaluation/README.md).
- Task 2 implementation and remaining experiment: [Task 2 README](../Task_2/README.md), [graph and episode interpretation](../docs/mid_evaluation/presentation/TASK2_VISUAL_ANALYSIS.md).
- Task 3 correction scope: [audit correction inventory](../docs/mid_evaluation/presentation/TASK3_CONTRACT_CORRECTIONS.md); [interactive dashboard analysis](../docs/mid_evaluation/presentation/TASK3_DASHBOARD_WORKFLOW.md).
- Contact-setting definition: [official MuJoCo impratio documentation](https://mujoco.readthedocs.io/en/stable/XMLreference.html#option-impratio).
- Task 4 reference-versus-render distinction: [visual selection notes](../docs/mid_evaluation/presentation/TASK4_VISUAL_SELECTION.md); [saved-mesh home-tour comparison](../Task_4/kitchen_home_tour_before_after/README.md).
- Later appliance refinements: [v7 repair record](../Task_4/kitchen_appliance_refinement_20261011/README.md).
- Paper titles, venues, years, and primary sources: [reference table](../docs/mid_evaluation/REFERENCES.md).

This script documents saved results and inspected artifacts. Preparing it did not rerun training, modify the controller, deploy a scene, or perform a hardware experiment.
