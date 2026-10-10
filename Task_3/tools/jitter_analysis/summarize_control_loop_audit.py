"""Read the saved control-loop experiments, verify traversal, and summarize them.

No simulation, checkpoint inference, controller edit, or server access occurs.
Run from Task_3 with its .venv Python; see --help for the result directory.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco
import numpy as np

from analyze import band_rms, load_run, save_json


def contact_diagnostics(out):
    """Read saved contacts and kinematics; do not integrate physics or run a policy."""
    base = out / "validation/current_gains"
    rows = []
    for item in read(base / "summary.json")["runs"]:
        path = base / item["run"]
        m, _, d = load_run(path)
        model = mujoco.MjModel.from_xml_path(m["scene"])
        data = mujoco.MjData(model)
        feet = ("FL", "FR", "RL", "RR")
        foot_ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, leg+"_foot") for leg in feet]
        mask = (d["time"] >= 5-1e-8) & (d["time"] < 11-1e-8)
        tangential_force = np.zeros((len(d["time"]), 4, 2))
        contact_speed, penetration, force_magnitude = [], [], []
        previous_index = -1
        for line in (path / "contacts.jsonl").open():
            event = json.loads(line)
            if not (5-1e-8 <= event["time"] < 11-1e-8) or event["foot"] is None:
                continue
            leg = feet.index(event["foot"])
            force = np.asarray(event["force_contact"][:3])
            index = int(round((event["time"] - d["time"][0]) / m["dt"]))
            assert abs(d["time"][index]-event["time"]) < 1e-8
            frame = np.asarray(event["frame"]).reshape(3, 3)
            tangential_force[index, leg] += (frame.T @ np.r_[0., force[1:]])[:2]
            if force[0] <= 5:
                continue
            if index != previous_index:
                data.qpos[:] = d["sim_qpos"][index]
                data.qvel[:] = d["sim_qvel"][index]
                mujoco.mj_kinematics(model, data)
                mujoco.mj_comPos(model, data)
                previous_index = index
            jac = np.zeros((3, model.nv))
            mujoco.mj_jac(model, data, jac, None, np.asarray(event["pos"]), int(model.geom_bodyid[foot_ids[leg]]))
            velocity = jac @ data.qvel  # The recorded floor is stationary.
            normal = frame[0]
            contact_speed.append(float(np.linalg.norm(velocity-normal*np.dot(normal, velocity))))
            penetration.append(max(0., -event["distance"]))
            force_magnitude.append(float(np.linalg.norm(force)))
        rows.append(dict(run=item["run"], checkpoint=item["checkpoint"], direction=item["direction"],
            impratio=m["impratio"], mean_actual_speed=item["mean_actual_speed"],
            normal_force_8_30_hz_rms_N=float(band_rms(d["foot_normal_force"][mask], 200).mean()),
            tangential_force_xy_8_30_hz_rms_N=float(np.linalg.norm(band_rms(tangential_force[mask].reshape(-1, 8), 200).reshape(4, 2), axis=1).mean()),
            joint_torque_8_30_hz_rms_Nm=float(band_rms(d["torque_applied"][mask], 200).mean()),
            loaded_contact_point_speed_rms_m_s=float(np.sqrt(np.mean(np.square(contact_speed)))),
            loaded_contact_point_speed_p99_m_s=float(np.quantile(contact_speed, .99)),
            penetration_p99_mm=float(1000*np.quantile(penetration, .99)),
            contact_force_p99_N=float(np.quantile(force_magnitude, .99)),
            loaded_contact_samples=len(contact_speed)))
    result = dict(provenance="Offline read of saved flat traces, t=5–11 s, kp=18/kd=0.7; no new trajectory.",
        sampling="Forces from [t,t+5ms] solve; velocities from recorded state at t. Load threshold >5 N.",
        slip_caveat="Rigid-foot velocity at the recorded contact point, computed with the recorded-state Jacobian against the stationary floor. A simulation slip proxy, not measured rubber deformation or hardware slip. Different closed-loop gaits can change the contact sample distribution.",
        interpretation="Rapid force/torque changes and slip proxies describe the changed feedback response. They do not establish physical accuracy or solver convergence on hardware.", runs=rows)
    save_json(out / "contact_response.json", result)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    groups = [(rows[i], rows[i+1]) for i in range(0, len(rows), 2)]
    for a, b in groups:
        assert (a["checkpoint"], a["direction"], a["impratio"]) == (b["checkpoint"], b["direction"], 100)
        assert b["impratio"] == 10
    labels = [("90k" if a["checkpoint"] == "original90000" else "91k")+" "+a["direction"].upper() for a, _ in groups]
    for ax, key, title in zip(axes.flat,
        ("normal_force_8_30_hz_rms_N", "tangential_force_xy_8_30_hz_rms_N", "loaded_contact_point_speed_rms_m_s", "penetration_p99_mm"),
        ("Normal contact force, 8–30 Hz RMS (N)", "Tangential XY force, 8–30 Hz RMS (N)", "Loaded contact-point slip proxy RMS (m/s)", "p99 penetration at loaded contacts (mm)")):
        x = np.arange(len(groups))
        ax.bar(x-.18, [a[key] for a, _ in groups], .36, label="impratio 100")
        ax.bar(x+.18, [b[key] for _, b in groups], .36, label="impratio 10")
        ax.set_xticks(x, labels); ax.set_title(title, fontsize=10); ax.grid(axis="y", alpha=.2); ax.legend()
    fig.suptitle("Saved simulated contacts: smoother response does not establish hardware accuracy")
    fig.savefig(out / "contact_response.png", dpi=150); plt.close(fig)
    return rows


def read(path):
    return json.loads(path.read_text())


def paired(rows, before, after):
    for checkpoint in ("original90000", "candidate91000"):
        for direction in ("x", "y"):
            group = [r for r in rows if r["checkpoint"] == checkpoint and r["direction"] == direction]
            if not group:
                continue
            yield next(r for r in group if r["case"] == before), next(r for r in group if r["case"] == after)


def verify_stairs(path):
    m, s, d = load_run(path)
    assert m["terrain"] == "stairs" and m["disabled_collision_geoms"] == []
    assert np.all(d["audit_impratio"] == m["impratio"])
    ever = np.maximum.accumulate(d["foot_platform_force"] > 1, axis=0)
    condition = (ever.all(1) & (d["foot_pos"][:, :, 0] > 3.622).all(1)
                 & (np.abs(d["foot_pos"][:, :, 1] + 9.5) < 1).all(1)
                 & (d["tilt_deg"] < 30) & (d["base_clearance"] > .18))
    duration = maximum = 0.
    for yes in condition:
        duration = duration + m["dt"] if yes else 0.
        maximum = max(maximum, duration)
    verified = maximum >= .5
    assert verified == (s["outcome"] == "traversed"), (path, maximum, s)
    first = np.flatnonzero((d["foot_step_force"] > 1).any(1))
    k = int(first[0]) if len(first) else None
    leg = int(d["foot_step_force"][k].argmax()) if k is not None else None
    return dict(run=str(path), outcome=s["outcome"], verified_traversal=verified,
                kp=m["kp"], kd=m["kd"], impratio=m["impratio"],
                final_time_s=float(d["time"][-1]), max_valid_traversal_hold_s=maximum,
                final_foot_xyz_m=d["foot_pos"][-1].tolist(),
                each_foot_loaded_platform=ever[-1].tolist(),
                final_tilt_deg=float(d["tilt_deg"][-1]),
                final_base_clearance_m=float(d["base_clearance"][-1]),
                final_nonfoot_force_N=float(d["nonfoot_contact_force"][-1]),
                first_contact_time_s=None if k is None else float(d["time"][k]),
                first_contact_foot_center_z_m=None if k is None else float(d["foot_pos"][k, leg, 2]))


def summarize(out):
    protocol = read(out / "protocol.json")
    protected = protocol["protected_file_hashes"]
    current_hashes = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in protected}
    assert protected == current_hashes, "Runtime/checkpoint changed since the diagnostic suite."
    current = read(out / "validation/current_gains/summary.json")["runs"]
    flat = []
    for a, b in paired(current, "legacy", "legacy_impratio10"):
        pa = out / "validation/current_gains" / a["run"]
        pb = out / "validation/current_gains" / b["run"]
        ma, _, da = load_run(pa)
        mb, _, db = load_run(pb)
        for key in ("checkpoint_sha256", "kp", "kd", "sensors", "dt", "decimation",
                    "target_min", "target_max", "foot_friction", "foot_solref", "spawn"):
            assert ma[key] == mb[key], (key, pa, pb)
        assert np.array_equal(da["command"], db["command"])
        assert np.array_equal(da["sim_qpos"][0], db["sim_qpos"][0])
        assert np.all(da["audit_impratio"] == 100) and np.all(db["audit_impratio"] == 10)
        flat.append(dict(checkpoint=a["checkpoint"], direction=a["direction"],
                         q_before_deg=a["q_band_deg"], q_after_deg=b["q_band_deg"],
                         reduction_percent=100*(1-b["q_band_deg"]/a["q_band_deg"]),
                         speed_before=a["mean_actual_speed"], speed_after=b["mean_actual_speed"],
                         tracking_rmse_before=a["speed_rmse"], tracking_rmse_after=b["speed_rmse"]))
    repeat_reductions = []
    for root in (out, out/"validation/start_plus", out/"validation/start_minus"):
        for a, b in paired(read(root/"summary.json")["runs"], "fresh", "fresh_impratio10"):
            repeat_reductions.append(100*(1-b["q_band_deg"]/a["q_band_deg"]))
            assert b["mean_actual_speed"] >= a["mean_actual_speed"]
    stairs = []
    for suite in ("stairs_current_gains", "stairs_reference"):
        base = out / "validation" / suite
        for r in read(base/"summary.json")["runs"]:
            stairs.append(verify_stairs(base/r["run"]))
    model = mujoco.MjModel.from_xml_path(next(p for p in protected if p.endswith("scene.xml")))
    geometry = {}
    for name in ("step_1_1", "step_1_12"):
        i = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)
        assert i >= 0
        geometry[name+"_top_m"] = float(model.geom_pos[i, 2] + model.geom_size[i, 2])
    findings = dict(provenance="Reads NEW scripted diagnostic simulations, not manual keyboard recordings.",
                    generated_from="protocol.json and saved trace.npz files; no new simulation",
                    protected_hashes_unchanged=True, flat_window_s=[5, 11], current_gains=[18, .7],
                    current_gain_flat_pairs=flat, repeated_fresh_reduction_percent=repeat_reductions,
                    stair_geometry=geometry, stair_verifications=stairs,
                    scope="Same nominal stair start, two checkpoints, two gains; not independent seeds or hardware validation.")
    save_json(out/"audit_findings.json", findings)
    contact_diagnostics(out)

    fig, ax = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    pos = np.arange(4); labels = [("Original 90k" if r["checkpoint"] == "original90000" else "Candidate 91k")+" "+r["direction"].upper() for r in flat]
    for key, panel, title in (("q", ax[0, 0], "Flat joint motion in 8–30 Hz (degrees RMS; lower is less rapid motion)"),
                              ("speed", ax[0, 1], "Flat actual speed (m/s; request = 0.30)")):
        suffix = "_deg" if key == "q" else ""
        panel.bar(pos-.18, [r[key+"_before"+suffix] for r in flat], .36, label="impratio 100")
        panel.bar(pos+.18, [r[key+"_after"+suffix] for r in flat], .36, label="impratio 10")
        panel.set_xticks(pos, labels); panel.set_title(title, fontsize=10); panel.legend(); panel.grid(axis="y", alpha=.2)
    ax[0, 1].axhline(.3, color="black", ls="--")
    for case, color in (("legacy", "#b44b35"), ("legacy_impratio10", "#167c47")):
        path = out/"validation/stairs_current_gains"/("candidate91000_x_"+case)
        _, s, d = load_run(path)
        label = ("100" if case == "legacy" else "10")+": "+s["outcome"]
        ax[1, 0].plot(d["time"], d["foot_pos"][:, :, 0].min(1), color=color, label=label)
        ax[1, 1].plot(d["time"], d["tilt_deg"], color=color, label=label)
    ax[1, 0].axhline(3.622, color="black", ls="--", label="All feet beyond final stair")
    ax[1, 0].set_title("Candidate stairs: smallest foot X position (m)"); ax[1, 0].legend()
    ax[1, 1].set_title("Candidate stairs: body tilt (degrees)"); ax[1, 1].legend()
    for panel in ax[1]: panel.set_xlabel("Simulation seconds"); panel.grid(alpha=.2)
    fig.suptitle("One contact-solver setting changed; policy, gains and command schedule preserved")
    fig.savefig(out/"impratio_comparison.png", dpi=150); plt.close(fig)

    flat_rows = "".join(f'<tr><td>{r["checkpoint"]} {r["direction"].upper()}</td><td>{r["q_before_deg"]:.3f} → {r["q_after_deg"]:.3f}</td><td>{r["reduction_percent"]:.1f}%</td><td>{r["speed_before"]:.3f} → {r["speed_after"]:.3f}</td></tr>' for r in flat)
    stair_rows = "".join(f'<tr><td>{html.escape(Path(r["run"]).name)}</td><td>{r["kp"]}</td><td>{r["impratio"]}</td><td>{r["outcome"]}</td><td>{r["final_time_s"]:.3f}</td><td>{r["max_valid_traversal_hold_s"]:.3f}</td></tr>' for r in stairs)
    content = f'''<!doctype html><meta charset="utf-8"><title>MoE jitter: verified control-loop findings</title>
<style>body{{font:17px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;line-height:1.55}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:8px}}img{{width:100%}}code,pre{{background:#eee}}.key{{background:#e7f5ea;padding:16px}}</style>
<h1>What reduced jitter in the controlled simulations?</h1><p>Verified 2026-10-07. These are new scripted simulations; your keyboard recordings remain separate.</p>
<p class="key"><b>Strongest tested contributor: viewer contact solver impratio=100.</b> Current training configuration uses 10. Changing only this setting reduced flat joint-band vibration by 44–73% at your current kp=18, kd=0.7, while maintaining or improving speed. All four tested impratio=10 stair cases traversed; none of the four matching impratio=100 cases did.</p>
<h2>Hardware objective: this is a diagnostic finding, not a deployment fix</h2><p><b>User clarification, 2026-10-07:</b> preserve actual hardware parameters. There is no impratio setting on the motor controller; it belongs to MuJoCo's contact solver. It changes simulated physics, so it can affect training and transfer even though it is simulation-only. The 100/10 comparison is evidence of contact sensitivity, not evidence that 10 is the measured real-world value. Keep deployed gains, limits, torque limits and transmission fixed; validate the simulator against hardware data before adopting a contact model for hardware training.</p><p>For a separate simulation diagnostic, the single XML edit would be <code>impratio="100"</code> → <code>impratio="10"</code> in <code>scene.xml:4</code>. This remains optional diagnostic advice; the live XML and controller have NOT been changed by this audit. No retraining is needed to compare this viewer setting. Original-training conditions are still unverified.</p>
<p>impratio controls how strongly the contact solver enforces friction relative to normal contact. It is a separate setting from the friction coefficient and motor gains. <a href="https://mujoco.readthedocs.io/en/stable/XMLreference.html#option-impratio">Official MuJoCo definition</a>. Lowering it helped these simulations; this does not measure the real robot's contact properties.</p>
<img src="impratio_comparison.png" alt="Matched vibration, speed, stair progress and tilt comparisons">
<h2>Matched flat runs at current gains</h2><p>Same 0.30 m/s requested speed; six-second windows, t=5–11 s. Joint RMS is averaged across the 12 joints after measuring their 8–30 Hz component; it is not the full leg swing. Read the actual-speed column to check that smoothness did not come from stopping.</p>
<table><tr><th>Policy / direction</th><th>Joint RMS °: 100 → 10</th><th>Reduction</th><th>Actual speed m/s: 100 → 10</th></tr>{flat_rows}</table>
<p>At kp=20, with fresh observations, 12 paired comparisons across three starts also reduced vibration ({min(repeat_reductions):.1f}–{max(repeat_reductions):.1f}%) without reducing mean requested-axis speed. These are paired sensitivity checks, not a broad generalization study.</p>
<h2>Stair completions independently checked from raw traces</h2><table><tr><th>Run</th><th>kp</th><th>impratio</th><th>Outcome</th><th>End time s</th><th>Longest valid traversal hold s</th></tr>{stair_rows}</table>
<p>Traversal requires all four feet beyond x=3.622 m and inside the lane, each foot having loaded the top platform, tilt below 30° and base clearance above 0.18 m, sustained for at least 0.5 s. Raw traces satisfy these criteria for all four successful runs. The staircase has 12 × 10 cm risers, ending at 1.2 m. This is two policies × two gains at one nominal start, not four independent random seeds. No hardware trial was performed.</p>
<h2>What the other tests tell us</h2><ul><li><b>kp/kd:</b> gain changes helped some cases and hurt others. Keep current gains for the first test.</li><li><b>Gate:</b> freezing weights did not consistently reduce vibration; a quiet candidate Y run mostly stopped moving. Gate movement alone is not established as the cause.</li><li><b>Timing/history:</b> delaying the actor's previous-action input destabilized gait. Do not change that observation contract casually. Refreshed observations also had mixed effects.</li><li><b>Frequency:</b> smaller physics steps helped several cases, but 50/200 Hz operation remained unchanged in the successful impratio tests. The different rates alone are not sufficient evidence of a fault.</li><li><b>First foot contact:</b> even the successful current-gain candidate contacted the first stair with a low foot center, then recovered and climbed. Low initial contact does not prove it never learned to lift. See its recorded first-contact plot below.</li><li><b>Policy:</b> it responds to the changed contact dynamics through feedback. Correct inference does not guarantee good actions under every environment setting.</li></ul>
<h2>Inspect the evidence</h2><ul><li><a href="audit_findings.json">Exact measurements, raw traversal verification and unchanged file hashes</a></li><li><a href="validation/current_gains/index.html">Current-gain flat comparisons</a></li><li><a href="validation/stairs_current_gains/candidate91000_x_legacy/index.html">Candidate stairs at 100: plots</a> / <a href="validation/stairs_current_gains/candidate91000_x_legacy_impratio10/index.html">Candidate stairs at 10: plots</a></li><li><a href="validation/stairs_current_gains/candidate91000_x_legacy_impratio10/08_first_contact.png">Successful candidate: first-contact event</a></li><li><a href="validation/stairs_reference/index.html">kp=20 stair suite</a> / <a href="validation/stairs_current_gains/index.html">kp=18 stair suite</a></li><li><a href="validation/start_plus/index.html">Positive start offsets</a> / <a href="validation/start_minus/index.html">Negative start offsets</a></li><li><a href="index.html">All 40 main sensitivity cases</a> / <a href="protocol.json">Protocol and checkpoint hashes</a></li></ul>
<h2>Deeper contact readout: what changed besides joint motion?</h2><p>Offline analysis of the same four flat pairs found less rapid normal/tangential force variation, less rapid joint torque variation, and smaller loaded contact-point slip estimates at 10. This does not demonstrate accurate rubber deformation or hardware friction. Contact sample distributions change when gait changes; these are simulation response measurements.</p><img src="contact_response.png" alt="Simulated contact-force, slip-proxy and penetration comparisons"><p><a href="contact_response.json">Exact contact metrics and definitions</a>. <a href="impratio_fixed_state.json">Fixed-state solver calculation</a> confirms the physical friction coefficients stay unchanged and the tangential regularizer increases tenfold when impratio falls from 100 to 10, with the normal regularizer unchanged. This is not a tenfold force change.</p>
<p><b>Limits of the conclusion:</b> reduced vibration is not zero vibration. Current training uses impratio=10, but the original 90k training configuration is not available to verify. These tests explain a major contributor in this simulator, not the cause of recorded hardware shaking. Wider calf/hip simulation limits remain unchanged and are not validated for hardware deployment.</p>'''
    (out/"FINDINGS.html").write_text(content)
    main = out/"index.html"
    page = main.read_text()
    if 'href="FINDINGS.html"' not in page:
        page = page.replace("<h1>", '<p><b><a href="FINDINGS.html">Start here: verified findings and recommended first change</a></b></p><h1>', 1)
        main.write_text(page)
    print(json.dumps(dict(flat=flat, stairs=[{k:r[k] for k in ("run", "verified_traversal", "max_valid_traversal_hold_s", "first_contact_foot_center_z_m")} for r in stairs], repeated_reduction_range=[min(repeat_reductions),max(repeat_reductions)]), indent=2))
    print("Findings:", out/"FINDINGS.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("out", type=Path)
    summarize(parser.parse_args().out.resolve())
