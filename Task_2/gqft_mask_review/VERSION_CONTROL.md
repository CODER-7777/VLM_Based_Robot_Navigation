# What is committed and what remains local

The Git history records the solver implementation, experiment/control scripts, exact source snapshots, research notes, validation/prediction JSON, compact keyframes, pose contracts, reports and verification receipts. The dedicated `SOLVER_REVIEW` home page, curated highlights, masked-attention evidence and four requested original-solver GIFs are included.

Model weights, flow caches, environments, transfer backups, generated font/browser caches, full solver PNG sets and large embedded solver-gallery HTML remain local. Nothing is deleted by the Git ignore policy. The complete local review folder remains available as before. The original full-artifact manifests describe that local snapshot; they are not a claim that every rendered file is tracked in Git.

To regenerate all1830 solver trajectory PNGs and their three offline galleries in a fresh checkout, with the existing analysis dependencies installed:

```bash
python -B Task_2/gqft_mask_review/restore_solver_review.py
```

This uses only committed prediction arrays and first-frame JPEGs. It does not load a model, access an external dataset, use a GPU or rerun SEA-RAFT. The original prediction/checkpoint hashes remain the source of numerical provenance. Font and plotting-library versions can change regenerated PNG byte hashes; do not overwrite original artifact-verification receipts with claims of pixel identity.

`--collection source` rebuilds the original experiment paths; `--collection all` rebuilds both source and collected review paths. Once rendering finishes, open `SOLVER_REVIEW/START_HERE.html`. The gallery defaults to original RGB, and camera-height reconstruction remains a separate experiment.

The GQFT implementation is a nested Git repository. Its code commits are made there first; the parent repository then records the resulting gitlink revision. These local commits do not imply that either repository was pushed to a remote.
