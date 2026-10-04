"""Offline rate-threshold diagnostic; no policy inference or simulator execution."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze import save_json
from plot_interactive import load_attempt


def policy_rates(d):
    ids = np.flatnonzero(d["policy_tick"])
    t = d["time"][ids]
    dt = np.diff(t)
    if np.any(dt <= 0):
        raise ValueError("Policy timestamps must increase within one attempt")
    q = d["target"][ids].astype(np.float64)
    return t[1:], np.abs(np.diff(q, axis=0)) / dt[:, None]


def audit(review, out, margin=1.25):
    if margin < 1 or not np.isfinite(margin):
        raise ValueError("Reference margin must be finite and at least one")
    out.mkdir(parents=True, exist_ok=False)
    windows = json.loads((review / "constant_command_windows.json").read_text())
    attempts = json.loads((review / "attempts.json").read_text())
    root = review.parent / "interactive"
    loaded = {}
    selected = []
    for w in windows:
        # Keep top-spawn descents/later flat travel out of ascent calibration.
        if w["start_kind"] != "ascent_start":
            continue
        run = w["run"]
        if run not in loaded:
            m, _, d = load_attempt(root / run)
            suffixes=("hip_joint", "thigh_joint", "calf_joint")
            if any(not name.endswith(suffixes[j % 3]) for j, name in enumerate(m["joint_names"])):
                raise ValueError("Inspect joint ordering before pooling hip/thigh/calf rates")
            times, rates = policy_rates(d)
            loaded[run] = m, times, rates
        m, times, rates = loaded[run]
        elapsed = times - m["start_sim_time"]
        mask = (elapsed >= w["start_s"] - 1e-8) & (elapsed < w["start_s"] + w["duration_s"] - 1e-8)
        selected.append((w, rates[mask]))
    reference = [r for w, r in selected if w["limit_profile"] == "tight" and w["phase"] == "before_stair_contact"]
    if not reference:
        raise ValueError("No tighter-bound, moving, constant-command approach windows")
    ref = np.concatenate(reference)
    family_p99 = [float(np.quantile(ref[:, j::3], .99)) for j in range(3)]
    limits = np.tile(np.array(family_p99) * margin, 4)
    if np.any(limits <= 0):
        raise ValueError("A zero reference rate cannot define a ratio penalty")
    rows = []
    for w, rates in selected:
        excess = np.maximum(rates / limits - 1, 0)
        rows.append(dict(w, target_rate_p99_rad_s=float(np.quantile(rates, .99)),
            joints_over_reference_fraction=float((rates > limits).mean()),
            policy_steps_with_any_excess_fraction=float((rates > limits).any(axis=1).mean()),
            proposed_rate_excess_cost=float(np.square(excess).sum(axis=1).mean())))
    groups = {}
    for profile in ("wide", "tight"):
        for phase in ("before_stair_contact", "after_stair_contact"):
            group = [r for w, r in selected if w["limit_profile"] == profile and w["phase"] == phase]
            if not group:
                continue
            rates = np.concatenate(group)
            groups[f"{profile}/{phase}"] = dict(windows=len(group), policy_intervals=len(rates),
                family_p50_rad_s=[float(np.quantile(rates[:, j::3], .5)) for j in range(3)],
                family_p95_rad_s=[float(np.quantile(rates[:, j::3], .95)) for j in range(3)],
                family_p99_rad_s=[float(np.quantile(rates[:, j::3], .99)) for j in range(3)],
                joints_over_reference_fraction=float((rates > limits).mean()),
                proposed_cost_mean=float(np.square(np.maximum(rates / limits - 1, 0)).sum(axis=1).mean()))
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    for j, ax in enumerate(axs):
        for phase, label in (("before_stair_contact", "moving approach"), ("after_stair_contact", "after first stair contact")):
            group = [r[:, j::3].flatten() for w, r in selected if w["limit_profile"] == "tight" and w["phase"] == phase]
            if group:
                values = np.sort(np.concatenate(group))
                ax.plot(values, np.arange(1, len(values) + 1) / len(values), label=label)
        ax.axvline(limits[j], color="crimson", ls="--", label=f"{margin:g} × approach P99 reference")
        ax.set_title(("Hip", "Thigh", "Calf")[j]); ax.set_xlabel("Absolute target increment / elapsed time (rad/s)")
        ax.set_ylabel("Fraction of recorded intervals at or below this rate")
        ax.grid(alpha=.2)
    axs[0].legend(fontsize=7)
    fig.suptitle("Tighter-bound ascent windows: empirical references, not physical motor limits")
    fig.tight_layout(); fig.savefig(out / "target_rate_distributions.png", dpi=130); plt.close(fig)
    summary = dict(recorded_attempts=len(attempts), qualifying_ascent_windows=len(selected),
        reference_windows=len(reference), reference_policy_intervals=len(ref),
        family_order=["hip", "thigh", "calf"], reference_family_p99_rad_s=family_p99,
        exploratory_margin=margin, exploratory_speed_limits_rad_s=limits.tolist(), groups=groups,
        method="Actual consecutive 50 Hz clamped-target samples; constant-command upright windows from prior review; no simulation",
        caveat="The approach itself may jitter; speed/gait states differ; P99 and margin are exploratory, not actuator calibration or a learned fix")
    save_json(out / "summary.json", summary); save_json(out / "window_metrics.json", rows)
    save_json(out / "provenance.json", dict(review=str(review.resolve()),
        review_input_hashes=json.loads((review / "input_sha256.json").read_text()),
        analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    (out / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Time-aware target penalty</title>'
        '<style>body{font:16px system-ui;max-width:1100px;margin:25px auto;line-height:1.5}img{width:100%}</style>'
        '<h1>Target change per elapsed time</h1><p>Reads your recorded runs only. Solid curves are empirical distributions; the dashed line is an exploratory reward threshold, not a safe motor limit.</p>'
        '<p>Penalize max(abs(target change)/(elapsed time × reference rate) − 1, 0) squared. A constant 20 ms update interval by itself cannot distinguish gentle movement from a large reversal.</p>'
        '<img src="target_rate_distributions.png"><p><a href="summary.json">Thresholds and group numbers</a> · <a href="window_metrics.json">Each window</a></p><pre>'
        + html.escape(json.dumps(summary, indent=2)) + '</pre>')
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--review", type=Path, default=Path("tools/results/interactive_review_20261003"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--margin", type=float, default=1.25)
    a = p.parse_args(); audit(a.review, a.out, a.margin)
