# Manual commit and upload commands

This page retains the earlier manual sequence. The current authorized update uses the [ten-commit publication plan](../PUBLICATION_PLAN.md); its explicit groups supersede the single parent commit below.

The previous seven commits remain in history. This update includes current-contact source changes, product-mesh tooling, concise technical READMEs, slide text and six independent diagrams. No PPT, training, server restart or push is performed automatically.

From the project root, first commit and push the SvanM2 source revision. The controller's tighter limits are existing local edits, documented as the current study contract.

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation

git -C Task_3/xterra_mjlab add \
  svanm2_moe_stair_sim/README.md \
  svanm2_moe_stair_sim/controller.py \
  svanm2_moe_stair_sim/run_interactive_sim.py \
  xterra_mjlab/actuators/svanm2_actuator.py
git -C Task_3/xterra_mjlab diff --cached --stat
git -C Task_3/xterra_mjlab commit -m "feat(svanm2): expose contact intervention and document current actuator contract"
git -C Task_3/xterra_mjlab push -u origin master
```

After that source push succeeds, publish the parent update using the explicit file list. It includes source/fit/licence metadata, not downloaded models, full scene binaries, raw traces or environments.

```bash
python3 docs/mid_evaluation/tools/validate_package.py --check-sources
git add --pathspec-from-file=docs/mid_evaluation/presentation/COMMIT_PATHS.txt
git diff --cached --stat
git commit -m "docs: connect failure evidence to fixes and prepare ten-slide review assets"
git push -u origin main
```

The GQFT source has no new edits from this presentation update. If its previous commit has not been uploaded, push `git -C Task_2/gqft_algorithm_sharing_vivekananda push -u origin main` before the parent push. No force-push is needed. These commands publish existing selected working-tree source; they do not regenerate benchmark results.
