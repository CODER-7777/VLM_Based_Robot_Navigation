#!/usr/bin/env python3
"""Prepare explicit publication groups; never stage, commit or push."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "docs/mid_evaluation"
OUTPUT = PACKAGE / "PUBLICATION_PLAN.json"


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", *args], cwd=cwd).decode().strip()


TITLES = [
    "chore(repo): separate generated research artifacts from published source",
    "docs(simulator): document feasibility and pending furniture collisions",
    "docs(gqft): explain pooling and plan controlled masked attention",
    "feat(locomotion): record active solver options and pin corrected controller",
    "feat(analysis): preserve hardware audit and MoE pathway diagnostics",
    "feat(scene): version product fitting and material verification tools",
    "feat(scene): add synchronized tours and appliance repair tooling",
    "docs(evidence): index portable results and validate source provenance",
    "docs(presentation): preserve slides speaking script and visual examples",
    "docs(research): connect VLM trajectory and RL integration milestones",
]


def group(path):
    if path in {"README.md", "docs/INTEGRATION_PLAN.md",
                "docs/mid_evaluation/PUBLICATION_PLAN.md",
                "docs/mid_evaluation/PUBLICATION_PLAN.json",
                "docs/mid_evaluation/PUBLICATION_VALIDATION.json",
                "docs/mid_evaluation/tools/prepare_publication.py"}:
        return 10
    if path in {".gitignore", ".gitmodules", "docs/mid_evaluation/REPOSITORY_GUIDE.md"}:
        return 1
    if path == ".gitattributes" or path.startswith("Task_1_Simulator_Evaluation/") or (
        path.startswith("docs/mid_evaluation/") and Path(path).name.startswith("task1_")):
        return 2
    if path.startswith("Task_2/") or path == "docs/mid_evaluation/GQFT_TRANSFORMER.md" or (
        path.startswith("docs/mid_evaluation/diagrams/") and Path(path).name.startswith(("gqft_", "task2_"))) or (
        path == "docs/mid_evaluation/tools/build_gqft_svg.py"):
        return 3
    if path == "Task_3/xterra_mjlab" or path in {
        "Task_3/tools/jitter_analysis/record.py", "Task_3/tools/jitter_analysis/interactive.py",
        "Task_3/tools/jitter_analysis/test_analysis.py", "Task_3/tools/README.md"}:
        return 4
    if path.startswith("Task_3/") or (
        path.startswith("docs/mid_evaluation/diagrams/") and Path(path).name.startswith(("task3_", "analysis_architecture_"))) or (
        path == "docs/mid_evaluation/tools/build_rl_moe_svg.py"):
        return 5
    if path == "Task_4/README.md" or any(path.startswith(f"Task_4/{name}/") for name in (
        "kitchen_home_tour_before_after", "kitchen_panorama_compare",
        "kitchen_appliance_refinement_20261011", "kitchen_tray_background_repair")):
        return 7
    if path.startswith("Task_4/"):
        return 6
    if path.startswith("mid-eval/") or path.startswith("docs/mid_evaluation/presentation/") or (
        path == "docs/mid_evaluation/PRESENTATION_GUIDE.md"):
        return 9
    if path.startswith("docs/mid_evaluation/"):
        return 8
    raise ValueError(f"Unassigned publication path: {path}")


def main():
    if git("diff", "--cached", "--name-only"):
        raise SystemExit("Index already has staged changes; inspect before preparing a publication plan.")
    changed = git("diff", "--name-only").splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    paths = sorted(set(changed + untracked + [str(OUTPUT.relative_to(ROOT))]))
    groups = [dict(number=i, message=title, paths=[]) for i, title in enumerate(TITLES, 1)]
    total = 0
    for name in paths:
        path = ROOT / name
        if name == "Task_3/xterra_mjlab":
            groups[3]["paths"].append(name)
            continue
        if name == str(OUTPUT.relative_to(ROOT)):
            groups[9]["paths"].append(name)
            continue
        if not path.is_file():
            raise SystemExit(f"Unexpected non-file change: {name}")
        if path.stat().st_size > 12 * 1024 * 1024:
            raise SystemExit(f"Large artifact requires explicit review: {name}")
        if path.suffix.lower() in {".npz", ".pt", ".pth", ".glb", ".blend", ".zip", ".mp4", ".log"}:
            raise SystemExit(f"Generated artifact in publication set: {name}")
        groups[group(name) - 1]["paths"].append(name)
        total += path.stat().st_size
    if any(not item["paths"] for item in groups):
        raise SystemExit("Each of the ten groups must contain a real change.")
    revisions = []
    for name in ("Task_2/gqft_algorithm_sharing_vivekananda", "Task_3/xterra_mjlab"):
        child = ROOT / name
        revisions.append(dict(path=name, revision=git("rev-parse", "HEAD", cwd=child),
                              branch=git("branch", "--show-current", cwd=child)))
    plan = dict(scope="Ten parent commits plus one prerequisite SvanM2 source commit; no generated raw data.",
                parent_base=git("rev-parse", "HEAD"), parent_branch=git("branch", "--show-current"),
                repositories=revisions, groups=groups, selected_file_bytes=total,
                child_source_paths=[".gitignore", "svanm2_moe_stair_sim/README.md",
                                    "svanm2_moe_stair_sim/controller.py", "svanm2_moe_stair_sim/run_interactive_sim.py",
                                    "xterra_mjlab/actuators/svanm2_actuator.py"])
    OUTPUT.write_text(json.dumps(plan, indent=2) + "\n")
    print(f"Prepared {len(paths)} paths in ten groups; {total / 1024 / 1024:.1f} MiB of changed files.")
    for item in groups:
        print(f"{item['number']}: {len(item['paths'])} paths — {item['message']}")


if __name__ == "__main__":
    main()
