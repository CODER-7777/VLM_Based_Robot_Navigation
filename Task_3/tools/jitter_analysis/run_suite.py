"""Matched sequential local GPU evaluation; never trains or edits production code."""
import argparse
import csv
import html
import json
from pathlib import Path

from record import record_run, DEFAULT_MODEL, CANDIDATE, write_json
from analyze import analyze_run
from first_contact import analyze_contact


def dashboard(out, results):
    fields = ["run", "outcome", "update", "terrain", "sensors", "first_contact_s", "end_s", "max_base_x", "max_tilt_deg", "final_yaw_deg"]
    more = ["q_8_30_hz_rms_deg_mean", "target_8_20_hz_rms_deg_mean", "target_removed_fraction_mean", "torque_clipped_fraction_mean", "vx_body_rmse"]
    rows = []
    for r in results:
        row = {k: r[k] for k in fields}
        phase = r["phases"].get("fixed_motion_4_8") or {}
        row.update({"fixed4to8_" + k: phase.get(k) for k in more})
        rows.append(row)
    with (out / "comparison.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    write_json(out / "comparison.json", results)
    def fmt(x):
        return "—" if x is None else (f"{x:.3f}" if isinstance(x, float) else html.escape(str(x)))
    body = ['<h1>MoE local failure analysis</h1>',
            '<p>Original 90000 vs combined candidate 90500, identical scripted commands and current target bounds. GPU policy inference; CPU MuJoCo physics. This is fresh data, not a replay of the video or the old audit.</p>',
            '<p><a href="REPORT.md">Interpretation/report</a> · <a href="comparison.csv">CSV comparison</a> · <a href="comparison.json">All phase metrics</a> · <a href="../../README.md">Tools guide</a></p>',
            '<p>Viewer = existing observation timing. Fresh = refresh sensors on a copy before constructing each policy observation. This is an isolated sensitivity test; it does not establish hardware accuracy.</p>',
            '<p>HF columns use the fixed 4–8 simulation-second window. Q: mean per-joint 8–30 Hz RMS (degrees), sampled at 200 Hz. Target: 8–20 Hz RMS, sampled at 50 Hz. Different bands are not an equal-band amplitude comparison. Lower oscillation alone is not success.</p>',
            '<div style="overflow-x:auto"><table><thead><tr><th>Run / plots</th><th>Outcome</th><th>First stair contact (s)</th><th>Max base x (m)</th><th>Max tilt (deg)</th><th>Q HF (deg)</th><th>Target HF (deg)</th><th>Target removed fraction</th><th>Torque clipped fraction</th><th>vx RMSE (m/s)</th></tr></thead><tbody>']
    for r in rows:
        cells = [r[k] for k in ("outcome", "first_contact_s", "max_base_x", "max_tilt_deg")]
        cells += [r["fixed4to8_" + k] for k in more]
        body.append(f'<tr><td><a href="{r["run"]}/index.html">{r["run"]}</a></td>' + ''.join('<td>' + fmt(x) + '</td>' for x in cells) + '</tr>')
    body.append('</tbody></table></div><p>Outcomes include falls, lane exits and timeouts. Completed execution means the experiment was recorded, not that stairs were climbed. These initial runs are deterministic cases, not a success-rate estimate. Plot panels use full run or contact-aligned windows as labelled.</p>')
    (out / "index.html").write_text('<!doctype html><html><meta charset="utf-8"><title>MoE failure comparison</title><style>body{font:16px system-ui;margin:30px;line-height:1.5}table{border-collapse:collapse}th,td{border:1px solid #ccc;padding:8px;text-align:left}a{color:#1760a5}th{background:#eef3fa}</style>' + '\n'.join(body) + '</html>')


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--seconds", type=float, default=30.)
    p.add_argument("--vx", type=float, default=.30)
    p.add_argument("--starts", type=int, choices=(1, 3), default=1)
    p.add_argument("--sensors", nargs="+", choices=("viewer", "fresh"), default=["viewer", "fresh"])
    p.add_argument("--terrains", nargs="+", choices=("flat", "stairs"), default=["flat", "stairs"])
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    offsets = [(0., 0.)] if a.starts == 1 else [(0., 0.), (-.03, -.02), (.03, .02)]
    protocol = dict(device=a.device, seconds=a.seconds, vx=a.vx, stand=3., ramp=1., starts=offsets,
                    sensors=a.sensors, terrains=a.terrains, original=str(DEFAULT_MODEL), candidate=str(CANDIDATE))
    write_json(a.out / "protocol.json", protocol)
    results = []
    for label, ckpt in [("original90000", DEFAULT_MODEL), ("candidate90500", CANDIDATE)]:
        for terrain in a.terrains:
            for sensors in a.sensors:
                for i, (dy, yaw) in enumerate(offsets):
                    name = f"{label}_{terrain}_{sensors}_start{i}"
                    print(f"START {name}", flush=True)
                    run = record_run(ckpt, a.out / name, terrain=terrain, sensors=sensors,
                                     device=a.device, seconds=a.seconds, vx=a.vx, y_offset=dy, yaw_offset=yaw)
                    metrics = analyze_run(run)
                    if terrain == "stairs":
                        flat = a.out / name.replace("_stairs_", "_flat_")
                        analyze_contact(run, flat if flat.exists() else None)
                    results.append(metrics)
                    dashboard(a.out, results)
                    print(f"DONE {name}: {metrics['outcome']}", flush=True)
    print(f"Dashboard: {a.out / 'index.html'}", flush=True)


if __name__ == "__main__": main()
