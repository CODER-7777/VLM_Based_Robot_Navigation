# Project boundaries and working rules

- On ISL, write only under `/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda`. Relevant files elsewhere may be read only. Do not install packages or write caches into shared environments or datasets.
- Ask the user before using any server GPU. Default all analysis/inference/evaluation to CPU. Do not infer permission from GPU availability.
- Never stop, kill, restart, or interrupt another running task without asking the user.
- Preserve Sir's released baseline under `baseline/released_gqft`; do not edit its source, checkpoint, or recorded results.
- Do not use horizontal flipping or any flip augmentation in active experiments. Historical flip runs belong only in `archive/discontinued_flip`.
- Establish failure evidence on validation data before selecting an algorithm change. Distinguish hypotheses, measured associations, and demonstrated causes.
- Load checkpoints strictly with their matching architectures. Never silently initialize missing weights.
- Keep the camera, data split, query policy, evaluation windows, and history protocol explicit. Do not tune on the locked test scene or repeat test evaluation to select changes.
- Preserve existing artifacts through reversible archival; do not delete historical evidence to make the directory look clean.
