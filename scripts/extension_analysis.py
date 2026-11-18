#!/usr/bin/env python3
"""extension_analysis.py -- analysis of this project's extension experiment.

Usage:  extension_analysis.py hth      (Group 2: H_th sensitivity)
        extension_analysis.py revert   (Group 3: deep->shallow reversion fix)

Reads results/raw/<trace>/<model>.txt (simulator output) for the 7-workload
subset, writes results/extension/{table_*.csv,table_*.md,fig_*.png|pdf}.
MPKI reduction (%) = (MPKI_base - MPKI_model) / MPKI_base * 100.
"""
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"
OUT = ROOT / "results" / "extension"
SUBSET = {"nodeapp-nodeapp": "NodeApp", "dacapo-spring": "Spring", "benchbase-tpcc": "TPCC",
          "benchbase-wikipedia": "Wikipedia", "dacapo-tomcat": "Tomcat",
          "merced.467915": "Merced", "whiskey.426708": "Whiskey"}
MODES = {
    "hth": {"tage64kscl": "64K TSL", "llbp-timing": "LLBP",
            "llbpx-timing-hth112": "LLBP-X H_th=112", "llbpx-timing": "LLBP-X H_th=232 (default)",
            "llbpx-timing-hth482": "LLBP-X H_th=482"},
    "revert": {"tage64kscl": "64K TSL", "llbp-timing": "LLBP",
               "llbpx-timing": "LLBP-X (upstream)", "llbpx-timing-revert": "LLBP-X + reversion fix"},
}
COL = {"64K TSL": "#8a8984", "LLBP": "#2a78d6", "LLBP-X H_th=112": "#1baf7a",
       "LLBP-X H_th=232 (default)": "#eb6834", "LLBP-X H_th=482": "#eda100",
       "LLBP-X (upstream)": "#eb6834", "LLBP-X + reversion fix": "#6250d6"}


def parse(path):
    t = path.read_text(errors="replace")
    g = lambda p: re.search(p, t)
    final = t.split("REGION OF INTEREST")[-1]
    m = re.search(r"Hist alloc W\nN:(\d+) Min:\d+ Max:\d+ Sum:(\d+)", final)
    return {"mpki": float(g(r"ROI MPKI\s*:\s*([\d.]+)").group(1)),
            "misp": int(g(r"ROI MISPREDICTIONS\s*:\s*(\d+)").group(1)),
            "accuracy": float(g(r"ROI ACCURACY\s*:\s*([\d.]+)").group(1)) * 100,
            "deep_alloc_pct": (100 * int(m.group(2)) / int(m.group(1))) if m else np.nan,
            "wrapped": "Reached end of trace" in t}


def main(mode):
    models = MODES[mode]
    rows = []
    for tr, wl in SUBSET.items():
        for mid, lab in models.items():
            f = RAW / tr / f"{mid}.txt"
            if not f.exists():
                sys.exit(f"missing {f}")
            rows.append({"workload": wl, "model_id": mid, "predictor": lab, **parse(f)})
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"extension_{mode}_results.csv", index=False)
    labs = list(models.values())
    mp = df.pivot(index="workload", columns="predictor", values="mpki").reindex(SUBSET.values())[labs]
    mp.loc["Mean"] = mp.mean()
    red = pd.DataFrame({l: (mp["64K TSL"] - mp[l]) / mp["64K TSL"] * 100 for l in labs[1:]})
    ref = labs[3] if mode == "hth" else labs[2]          # default LLBP-X
    vs = pd.DataFrame({l: (mp[ref] - mp[l]) / mp[ref] * 100 for l in labs[2:] if l != ref})
    tab = mp.round(4).join(red.round(3).add_prefix("red_vs_TSL_%: ")).join(vs.round(3).add_prefix(f"change_vs_default_%: "))
    if mode == "revert":
        dp = df.pivot(index="workload", columns="predictor", values="deep_alloc_pct").reindex(SUBSET.values())[labs[2:]]
        dp.loc["Mean"] = dp.mean()
        tab = tab.join(dp.round(2).add_prefix("deep_alloc_%: "))
    tab.to_csv(OUT / f"table_{mode}.csv")
    cols = ["workload"] + list(tab.columns)
    md = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for w, r in tab.iterrows():
        md.append("| " + " | ".join([w] + [f"{v:.3f}" if abs(v) < 100 else f"{v:.1f}" for v in r.values]) + " |")
    (OUT / f"table_{mode}.md").write_text("\n".join(md) + "\n")

    # figure: MPKI reduction vs 64K TSL
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "axes.grid.axis": "y", "grid.color": "#e4e3df", "axes.axisbelow": True,
                         "legend.frameon": False, "savefig.dpi": 300})
    x = np.arange(len(red)); x[-1:] = x[-1:] + 0.4
    n = red.shape[1]; w = 0.84 / n
    fig, ax = plt.subplots(figsize=(10, 3.8))
    for i, l in enumerate(red.columns):
        ax.bar(x - 0.42 + (i + 0.5) * w, red[l].values, w * 0.92, color=COL[l], label=l)
    ax.axhline(0, color="#52514e", lw=0.8)
    ax.set_xticks(x, red.index, rotation=25, ha="right")
    ax.set_ylabel("MPKI reduction vs. 64K TSL (%)")
    ax.set_ylim(min(0, red.values.min()) - 1, red.values.max() * 1.25)
    title = {"hth": "LLBP-X sensitivity to the history-length threshold H_th",
             "revert": "LLBP-X with the deep→shallow reversion made reachable"}[mode]
    ax.set_title(title + " (higher is better)")
    ax.legend(ncol=n, loc="upper left", fontsize=8)
    fig.savefig(OUT / f"fig_{mode}.png", bbox_inches="tight")
    fig.savefig(OUT / f"fig_{mode}.pdf", bbox_inches="tight")
    print(tab.round(3).to_string())
    print("wrapped runs (complete short traces):", sorted(df[df.wrapped].workload.unique()))


if __name__ == "__main__":
    main(sys.argv[1])
