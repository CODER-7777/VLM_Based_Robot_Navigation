#!/usr/bin/env python3
"""Copy selected recorded evidence; never launch inference, training, or servers.

Run from any directory. Requires the original local research artifacts.
Writes only the presentation evidence and figures beside this script.
"""

from pathlib import Path
import hashlib
import json
import shutil


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "docs/mid_evaluation"
GQFT = "Task_2/gqft_algorithm_sharing_vivekananda"
RESULTS = "Task_3/tools/results"

SOURCES = {
    "task2": {
        "baseline_test_h24.json": f"{GQFT}/results/isl_test_h24.json",
        "attention_test_h24.json": f"{GQFT}/results/spatial_attn_test_h24.json",
        "yaw_test_h24.json": f"{GQFT}/results/spatial_yaw_test.json",
        "validation_diagnostics.json": f"{GQFT}/analysis/validation_failure_20261009/diagnostics.json",
        "geometry_oracle.json": f"{GQFT}/analysis/label_geometry_20261009/oracle_geometry.json",
        "cpu_contract_checks.json": f"{GQFT}/analysis/verification/cpu_contract_checks_server.json",
    },
    "task3": {
        "hardware_audit_report.md": "Task_3/moe_jitter_audit_20260921/REPORT.md",
        "matched_90500.csv": f"{RESULTS}/20261002_matched_v1/comparison.csv",
        "stair_starts_90500.csv": f"{RESULTS}/20261002_stair_repeats_v1/comparison.csv",
        "target_rate_summary.json": f"{RESULTS}/time_aware_penalty_20261003/summary.json",
        "rate_clearance_integration.json": f"{RESULTS}/time_rate_integration_20261004/clearance_013_check.json",
        "gain_sensitivity.json": f"{RESULTS}/gain_sensitivity_20261005_v1/summary.json",
        "contact_findings.json": f"{RESULTS}/control_loop_audit_20261006_v2/audit_findings.json",
        "contact_response.json": f"{RESULTS}/control_loop_audit_20261006_v2/contact_response.json",
        "fixed_state_regularization.json": f"{RESULTS}/control_loop_audit_20261006_v2/impratio_fixed_state.json",
        "solver_probe.json": f"{RESULTS}/tier1_solver_probe_20261007/results.json",
    },
    "task4": {
        "initial_gaussian_evaluation.json": "Task_4/split_render_pipeline/evidence/final_evaluation.json",
        "dense_corner_evaluation.json": "Task_4/gaussian_corner_repair/evidence/global_evaluation.json",
        "dense_corner_geometry.json": "Task_4/gaussian_corner_repair/evidence/geometry_validation.json",
        "all_kitchen_publication.json": "Task_4/kitchen_all_objects_upgrade/evidence/published_validation.json",
        "all_kitchen_placement.json": "Task_4/kitchen_all_objects_upgrade/evidence/validation.json",
        "size_exceptions.json": "Task_4/kitchen_all_objects_upgrade/evidence/audit_size_exceptions.json",
        "physics_validation.json": "Task_4/kitchen_all_objects_upgrade/evidence/physics_validation.json",
        "browser_verification.json": "Task_4/kitchen_all_objects_upgrade/evidence/browser_verification.json",
        "toaster_archive_metadata.json": "Task_4/toaster_selected_model/evidence/archive_metadata.json",
        "wall_geometry_result.json": "Task_4/toaster_wall_mesh_repair/evidence/geometry_result.json",
    },
}

FIGURES = {
    "task2": {
        "task2_validation_comparison.png": f"{GQFT}/analysis/figures/validation_comparison.png",
        "task2_geometry_failure.png": f"{GQFT}/analysis/figures/geometry_failure.png",
    },
    "task3": {
        "task3_impratio_comparison.png": f"{RESULTS}/control_loop_audit_20261006_v2/impratio_comparison.png",
    },
    "task4": {
        "task4_toaster_comparison.jpg": "Task_4/toaster_selected_model/images/toaster_comparison.jpg",
        "task4_caddy_comparison.jpg": "Task_4/kitchen_all_objects_upgrade/images/gaussian_caddy.jpg",
        "task4_corner_before_after.jpg": "Task_4/gaussian_corner_repair/images/comparison4.jpg",
        "task4_latest_kitchen.jpg": "Task_4/kitchen_all_objects_upgrade/images/live_rgb.jpg",
    },
}


def read_json(relative):
    return json.loads((ROOT / relative).read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def copy_record(source, destination):
    source_path = ROOT / source
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination)
    payload = source_path.read_bytes()
    return {
        "source": source,
        "snapshot": str(destination.relative_to(ROOT)),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def main():
    # Refuse incomplete source availability before writing any snapshots.
    required = [p for group in (SOURCES, FIGURES) for files in group.values() for p in files.values()]
    missing = [p for p in required if not (ROOT / p).is_file()]
    if missing:
        raise SystemExit("Original artifacts missing; use the committed snapshots instead:\n" + "\n".join(missing))
    for task, files in SOURCES.items():
        records = []
        for name, source in files.items():
            if name.endswith(".json"):
                read_json(source)  # Verify parseability without importing research code.
            records.append(copy_record(source, PACKAGE / "evidence" / task / name))
        for name, source in FIGURES[task].items():
            records.append(copy_record(source, PACKAGE / "figures" / name))
        write_json(PACKAGE / "evidence" / task / "manifest.json", {
            "review_date": "2026-10-10",
            "scope": "Copies of existing artifacts, not new evaluations. Source and copy SHA-256 are identical.",
            "records": records,
        })

    diagnostics = read_json(SOURCES["task2"]["validation_diagnostics.json"])
    baseline = read_json(SOURCES["task2"]["baseline_test_h24.json"])["histories"][0]
    test_rows = {}
    for name, filename in [("baseline", "baseline_test_h24.json"), ("spatial_attention", "attention_test_h24.json"), ("spatial_yaw", "yaw_test_h24.json")]:
        result = read_json(SOURCES["task2"][filename])
        row = result["histories"][0]
        test_rows[name] = {"protocol": {k: result[k] for k in ["split", "reference_history", "fixed_reference_tasks"]}, "metrics": row,
                           "ade_reduction_percent_vs_baseline": 100 * (baseline["ade_px"] - row["ade_px"]) / baseline["ade_px"],
                           "fde_reduction_percent_vs_baseline": 100 * (baseline["fde_px"] - row["fde_px"]) / baseline["fde_px"]}
    validation_rows = {}
    for name, model in diagnostics["models"].items():
        validation_rows[name] = {"history24": next(row for row in model["histories"] if row["history"] == 24),
                                 "selected_history": model["shortest_sufficient_history"],
                                 "direct_3d_mean_error_m": model["trajectory_3d_mean_m"],
                                 "parameters": diagnostics["checkpoints"][name]["parameters"],
                                 "cpu_ms_per_history30_window": model["cpu_ms_per_history30_window"]}
    write_json(PACKAGE / "evidence/task2/summary.json", {
        "derived_from": "The sibling copied test JSONs and validation_diagnostics.json",
        "test_caveat": "Fixed history 24; yaw validation selected 12 historically / 16 in standardized sweep; eight repeated anchor queries per window.",
        "validation_protocol": diagnostics["protocol"], "checkpoints": diagnostics["checkpoints"],
        "test": test_rows, "validation": validation_rows,
    })
    metric_count = sum(len(files) for files in SOURCES.values())
    figure_count = sum(len(files) for files in FIGURES.values())
    print(f"Copied {metric_count} recorded artifacts and {figure_count} figures; wrote manifests and the derived GQFT summary.")


if __name__ == "__main__":
    main()
