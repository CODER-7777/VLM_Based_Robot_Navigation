# Checks before the solver Git commits

CPU-only verification passed for legacy checkpoint/output contracts, ground solver synthetic recovery and warm starts(11 checks), spatial masking(10), trainable mask/yaw integration(15), and frozen motion controls(18). The dataset-dependent section of the legacy suite was skipped because the external HSGM dataset is not local; the previously saved server validation is retained separately.

The offline restoration smoke check rebuilt episode629 in all three review conditions from prediction JSON and JPEGs only:24 trajectory views and123 PNGs, with prediction-file hashes verified. It loaded no model, regenerated no optical flow and used no GPU. Original experiment-verification receipts were restored after the checks; new receipts live in this directory.

Nested GQFT commits: e6af034(core solver and model prerequisites), f041b21(frozen inference controls). Main-repository commits add the experiment evidence/review tools and record that gitlink. No new training or server experiment ran while preparing these commits.
