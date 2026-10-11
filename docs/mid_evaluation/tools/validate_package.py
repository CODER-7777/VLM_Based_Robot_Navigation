#!/usr/bin/env python3
"""Validate documentation/evidence consistency without research dependencies."""

from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import re
import unicodedata
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "docs/mid_evaluation"


def load(path):
    return json.loads(path.read_text())


def heading_anchors(text):
    anchors, seen = set(), {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.MULTILINE):
        # GitHub's common heading cases: retain letters/numbers/hyphens/underscores.
        slug = "".join(c for c in heading.lower() if c in " -_" or unicodedata.category(c)[0] in "LN")
        slug = slug.replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        anchors.add(slug if not count else f"{slug}-{count}")
    return anchors


def optional_workspace_source(path):
    relative = path.relative_to(ROOT).as_posix()
    roots = ["Task_2/gqft_algorithm_sharing_vivekananda/", "Task_3/xterra_mjlab/",
             "Task_3/moe_jitter_audit_20260921/", "Task_3/Videos/"]
    if any(relative.startswith(prefix) for prefix in roots):
        return True
    # The presentation includes independent task summaries; extended research
    # reports, tools, and dashboards may exist only in the full workspace.
    if relative.startswith("Task_4/") and relative not in ["Task_4/README.md", "Task_4/notes/PREVIOUS_OVERVIEW.md"]:
        return True
    return relative in ["Task_2/gqft_algorithm_sharing_vivekananda/AGENTS.md"]


def check_links(errors):
    documents = [ROOT / "README.md", ROOT / "Task_1_Simulator_Evaluation/README.md",
                 ROOT / "Task_2/README.md", ROOT / "Task_3/README.md", ROOT / "Task_4/README.md"]
    documents += sorted(PACKAGE.glob("*.md"))
    documents += sorted((PACKAGE / "presentation").glob("*.md"))
    documents += sorted((PACKAGE / "diagrams").glob("*.md"))
    documents += sorted((ROOT / "mid-eval").glob("*.md"))
    documents += [ROOT / "docs/INTEGRATION_PLAN.md", ROOT / "Task_2/MASKED_ATTENTION_PLAN.md"]
    missing_optional, count = [], 0
    for document in documents:
        source = document.read_text()
        # Remove fenced code so command examples are not interpreted as links.
        source = re.sub(r"```.*?```", "", source, flags=re.DOTALL)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", source):
            if re.match(r"(?:https?://|mailto:)", target):
                continue
            target = target.strip().strip("<>")
            path_part, _, anchor = target.partition("#")
            path = (document.parent / unquote(path_part)).resolve() if path_part else document
            count += 1
            if not path.exists():
                if optional_workspace_source(path):
                    missing_optional.append(f"{document.relative_to(ROOT)} -> {target}")
                else:
                    errors.append(f"Missing link: {document.relative_to(ROOT)} -> {target}")
                continue
            if anchor and path.suffix == ".md" and anchor not in heading_anchors(path.read_text()):
                errors.append(f"Missing heading: {document.relative_to(ROOT)} -> {target}")
    return count, missing_optional


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-sources", action="store_true", help="Also require and verify original local artifact hashes")
    args = parser.parse_args()
    errors = []
    copies = 0
    manifests = sorted((PACKAGE / "evidence").glob("*/manifest.json"))
    presentation_manifest = PACKAGE / "presentation/assets/manifest.json"
    if presentation_manifest.exists():
        manifests.append(presentation_manifest)
    for manifest_path in manifests:
        for record in load(manifest_path)["records"]:
            snapshot = ROOT / record["snapshot"]
            if not snapshot.is_file():
                errors.append(f"Missing snapshot: {snapshot}")
                continue
            payload = snapshot.read_bytes()
            if len(payload) != record["bytes"] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
                errors.append(f"Snapshot differs from manifest: {snapshot}")
            if args.check_sources:
                original = ROOT / record["source"]
                expected = record.get("source_sha256", record["sha256"])
                if not original.is_file() or hashlib.sha256(original.read_bytes()).hexdigest() != expected:
                    errors.append(f"Original differs/missing: {original}")
            if snapshot.suffix == ".json":
                load(snapshot)
            copies += 1

    summary = load(PACKAGE / "evidence/task2/summary.json")
    raw_names = {"baseline": "baseline_test_h24.json", "spatial_attention": "attention_test_h24.json", "spatial_yaw": "yaw_test_h24.json"}
    for model, name in raw_names.items():
        raw = load(PACKAGE / "evidence/task2" / name)["histories"][0]
        if summary["test"][model]["metrics"] != raw:
            errors.append(f"Derived test row differs: {model}")
    base = summary["test"]["baseline"]["metrics"]
    yaw = summary["test"]["spatial_yaw"]["metrics"]
    for metric in ["ade", "fde"]:
        reduction = 100 * (base[f"{metric}_px"] - yaw[f"{metric}_px"]) / base[f"{metric}_px"]
        if not math.isclose(reduction, summary["test"]["spatial_yaw"][f"{metric}_reduction_percent_vs_baseline"], abs_tol=1e-10):
            errors.append(f"Incorrect GQFT {metric} reduction")
    diagnostics = load(PACKAGE / "evidence/task2/validation_diagnostics.json")
    for model, row in summary["validation"].items():
        source = diagnostics["models"][model]
        if row["history24"] != next(x for x in source["histories"] if x["history"] == 24):
            errors.append(f"Derived validation row differs: {model}")
        if row["selected_history"] != source["shortest_sufficient_history"]:
            errors.append(f"Incorrect selected history: {model}")

    with (PACKAGE / "evidence/task3/stair_starts_90500.csv").open(newline="") as stream:
        starts = list(csv.DictReader(stream))
    if len(starts) != 12 or any(row["outcome"] == "traversed" for row in starts):
        errors.append("Earlier stair-case count/outcomes do not match the report")
    findings = load(PACKAGE / "evidence/task3/contact_findings.json")
    traversals = findings["stair_verifications"]
    for setting, expected in [(10, True), (100, False)]:
        rows = [row for row in traversals if row["impratio"] == setting]
        if len(rows) != 4 or any(row["verified_traversal"] != expected for row in rows):
            errors.append(f"Later contact-setting traversal claim differs at {setting}")
    for pair in findings["current_gain_flat_pairs"]:
        reduction = 100 * (pair["q_before_deg"] - pair["q_after_deg"]) / pair["q_before_deg"]
        if not math.isclose(reduction, pair["reduction_percent"], abs_tol=1e-8):
            errors.append("Contact-setting RMS percentage mismatch")

    latest = load(PACKAGE / "evidence/task4/all_kitchen_publication.json")
    if latest["gaussians"] != 4378360 or not math.isclose(latest["depth_valid_fraction"], 0.990068359375):
        errors.append("Final kitchen counts/coverage differ from the report")
    if latest["render_info"]["width"] != 800 or latest["render_info"]["height"] != 640:
        errors.append("Final kitchen image dimensions differ from the report")
    current_verification = PACKAGE / "presentation/assets/task3_current_verification.json"
    if current_verification.exists():
        current = load(current_verification)
        if current["runs"] != 34 or current["devices"] != ["cpu"] or current["training_launched"]:
            errors.append("Current locomotion study scope differs from slides")
        stairs = current["stair_verifications"]
        for tag, expected in [("baseline", 0), ("impratio10", 3)]:
            rows = [r for r in stairs if f"_{tag}_" in r["run"]]
            if len(rows) != 6 or sum(r["verified_traversal"] for r in rows) != expected:
                errors.append(f"Current tight-limit stair result differs: {tag}")
        reductions = [r["q_reduction_percent"] for r in current["flat_pairs"]]
        if len(reductions) != 4 or round(min(reductions), 1) != 63.5 or round(max(reductions), 1) != 70.5:
            errors.append("Current flat vibration range differs from slides")
        slide_text = (PACKAGE / "presentation/SLIDE_TEXT.md").read_text()
        if len(re.findall(r"^## Slide \d+", slide_text, re.MULTILINE)) != 10:
            errors.append("Slide text must contain exactly ten slides")
    source_count = 0
    source_manifest = PACKAGE / "SOURCE_MANIFEST.json"
    if source_manifest.exists():
        for record in load(source_manifest)["files"]:
            path = ROOT / record["path"]
            if not path.is_file():
                errors.append(f"Missing indexed tool source: {record['path']}")
                continue
            payload = path.read_bytes()
            if len(payload) != record["bytes"] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
                errors.append(f"Indexed tool source changed: {record['path']}")
            source_count += 1
    links, missing_optional = check_links(errors)
    if errors:
        raise SystemExit("Validation failed:\n" + "\n".join(errors))
    print(f"PASS: {copies} evidence snapshots, {source_count} indexed tool sources, {links} report links, and central numeric claims.")
    if missing_optional:
        print(f"Extended workspace sources absent: {len(missing_optional)} links; portable evidence passed.")
    else:
        print("All linked extended workspace sources are present.")


if __name__ == "__main__":
    main()
