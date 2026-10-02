# Current step: analyze fresh failures before another training change

Updated 2026-10-02. The combined candidate has completed training at 90500. The video in `Task_3/Videos/2026-10-02 18-50-10.mp4` was reviewed in [note 13](13_CANDIDATE_VIDEO_REVIEW_20261002.md). New local measurement tools and matched evaluations are now completed.

**Follow [tools/README.md](../tools/README.md) now.** Notes 07–12 and the September audit remain background. The audit is not ground truth; the new conclusions link to raw simulation data.

1. Read [the new report](../tools/results/20261002_matched_v1/REPORT.md).
2. Open [the first-contact plot](../tools/results/20261002_matched_v1/candidate90500_stairs_viewer_start0/08_first_contact.png). In the central candidate run the front-left foot hits the first riser at 9.730 s with center height 5.63 cm, below the roughly 12.2 cm needed to clear a 10 cm top with the modeled foot radius. The contacting leg's target and torque are not clipped at that instant.
3. Open [the same-policy flat/stair comparison](../tools/results/20261002_matched_v1/candidate90500_stairs_viewer_start0/09_flat_comparison.png). Motion diverges after first contact. Same-window joint HF RMS is 0.331° on flat versus 0.833° with stairs; this implicates the contact feedback loop without identifying one internal cause.
4. Open [the paired-start comparison](../tools/results/20261002_stair_repeats_v1/paired_starts.png). Candidate saturation and speed tracking improve in the tested early-motion window; jitter changes are mixed. No policy completes any tested stair start.
5. Inspect clearance reward/sensor semantics, support transfer and heading tracking, after agreeing on observation timing. Choose the next reward experiment from those measurements. Actuator calibration/tuning remains separate.

Changing allowed hip/calf targets does **not** require changing `J_LEG`. It converts between joint and motor coordinates according to the assumed gears and belt. See [the derivation and source files](../tools/README.md#do-the-changed-angle-limits-require-a-changed-j_leg). The screenshot's MuJoCo Control values are torque-motor inputs in this model, not target angles.

The new work added local tools, raw traces, plots, dashboards and documentation. It did not change training rewards, J, gains, torque limits, the production controller, or server files. The earlier hip-limit edit was separately authorized and is retained in both policies' evaluation setup.

To view:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/tools/results/20261002_matched_v1/index.html>. If a server is already serving Task_3 on port 8000, just use the link.
