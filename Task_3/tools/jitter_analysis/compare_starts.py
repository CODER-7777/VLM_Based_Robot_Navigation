"""Show paired start sensitivity without hiding regressions behind averages."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from plot_help import refresh_page


def compare(path):
    path = Path(path)
    runs = json.loads((path / "comparison.json").read_text())
    terms = [("q_8_30_hz_rms_deg_mean", "Measured joint 8–30 Hz RMS (degrees)"),
             ("vx_body_rmse", "Forward speed RMSE (m/s)"),
             ("target_removed_fraction_mean", "Target removed fraction (joint-samples)")]
    fig, axs = plt.subplots(2, 3, figsize=(14, 8))
    summaries = {}
    for row, sensor in enumerate(["viewer", "fresh"]):
        for col, (term, title) in enumerate(terms):
            ax = axs[row, col]
            pairs = []
            for start in range(3):
                pair = []
                for label in ["original90000", "candidate90500"]:
                    match = [r for r in runs if r["run"] == f"{label}_stairs_{sensor}_start{start}"]
                    if match:
                        pair.append(match[0]["phases"]["fixed_motion_4_8"][term])
                if len(pair) == 2:
                    ax.plot([0, 1], pair, "o-", alpha=.75, label=f"start {start}")
                    pairs.append(pair)
            if pairs:
                mean = np.mean(pairs, axis=0)
                ax.plot([0, 1], mean, "k--", label="arithmetic mean")
                summaries[f"{sensor}_{term}"] = dict(pairs=pairs, mean=mean.tolist(),
                                                    candidate_percent_change=float(100 * (mean[1] / mean[0] - 1)))
            ax.set_xticks([0, 1], ["Original 90000", "Candidate 90500"])
            ax.set_title(sensor + ": " + title, fontsize=10)
            ax.set_xlim(-.2, 1.2); ax.grid(alpha=.25)
    axs[0, 0].legend(fontsize=8)
    fig.suptitle("Matched 4–8 s early approach; each line pairs the same starting pose\nThree deterministic starts, not confidence intervals or independent training seeds")
    fig.tight_layout(); fig.savefig(path / "paired_starts.png", dpi=150); plt.close(fig)
    (path / "paired_starts.json").write_text(json.dumps(summaries, indent=2) + "\n")
    page = path / "index.html"
    text = page.read_text()
    if 'src="paired_starts.png"' not in text:
        page.write_text(text.replace('</html>', '<h2>Starting-pose sensitivity</h2><a href="paired_starts.png"><img style="max-width:100%" src="paired_starts.png"></a></html>'))
    refresh_page(page)
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("suite", type=Path)
    print(json.dumps(compare(parser.parse_args().suite), indent=2))
