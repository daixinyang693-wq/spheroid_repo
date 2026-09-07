"""
compare_debris.py
-----------------
Compare Band_Mean distributions between reference and debris-positive images.
Generates a summary plot and prints classification performance.

Usage
-----
    python src/compare_debris.py \\
        --reference results/ref_results.csv \\
        --debris    results/debris_results.csv \\
        --output    results/comparison.png \\
        --threshold 115
"""

import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Compare reference vs debris Band_Mean distributions.")
    p.add_argument("--reference",  required=True, help="CSV from a clean reference image")
    p.add_argument("--debris",     required=True, help="CSV from a debris-positive image")
    p.add_argument("--output",     default="comparison.png", help="Output plot path")
    p.add_argument("--threshold",  type=float, default=115,
                   help="Debris classification threshold (default: 115)")
    return p.parse_args()


def main():
    args = parse_args()

    df_ref    = pd.read_csv(args.reference);  df_ref["Group"]    = "Reference"
    df_debris = pd.read_csv(args.debris);     df_debris["Group"] = "Debris"
    df        = pd.concat([df_ref, df_debris], ignore_index=True)

    metrics = ["Band_Count", "Band_SignalArea_um2", "Band_Std", "Band_Mean"]
    colors  = {"Reference": "#58a6ff", "Debris": "#ff7b72"}

    fig, axes = plt.subplots(2, 2, figsize=(12, 10), facecolor="#0d1117")
    fig.suptitle("Reference vs Debris — Band metric distributions",
                 color="white", fontsize=14)

    for ax, metric in zip(axes.flatten(), metrics):
        ax.set_facecolor("#161b22")
        for group, color in colors.items():
            vals = df[df["Group"] == group][metric].dropna()
            ax.hist(vals, bins=15, alpha=0.7, color=color,
                    label=f"{group} (n={len(vals)})", edgecolor="none")
        if metric == "Band_Mean":
            ax.axvline(args.threshold, color="yellow", lw=1.5,
                       linestyle="--", label=f"Threshold = {args.threshold}")
        ax.set_title(metric, color="white", fontsize=11)
        ax.tick_params(colors="gray")
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["bottom", "left"]:
            ax.spines[spine].set_color("#30363d")
        ax.legend(fontsize=9)

        ref_med = df[df["Group"] == "Reference"][metric].median()
        deb_med = df[df["Group"] == "Debris"][metric].median()
        print(f"{metric}:")
        print(f"  Reference median : {ref_med:.3f}")
        print(f"  Debris    median : {deb_med:.3f}")
        if ref_med != 0:
            print(f"  Fold change      : {deb_med/ref_med:.2f}x\n")

    plt.tight_layout()
    plt.savefig(args.output, dpi=150, facecolor="#0d1117")
    print(f"Plot saved → {args.output}")

    # Classification performance
    df["HasDebris_pred"] = df["Band_Mean"] < args.threshold
    print("\nClassification performance (threshold = {:.0f}):".format(args.threshold))
    for group in ["Reference", "Debris"]:
        sub   = df[df["Group"] == group]
        pos   = sub["HasDebris_pred"].sum()
        total = len(sub)
        print(f"  {group}: {pos}/{total} predicted debris "
              f"({100*pos/total:.0f}%)")


if __name__ == "__main__":
    main()
