#!/usr/bin/env python3
"""make_figures.py -- tables and graphs from results/processed/all_results.csv
[NEW, project team]

Every plotted / tabulated number is read from the consolidated CSV produced by
parse_results.py (which in turn is parsed from raw simulator output).  The only
non-experimental inputs are the paper reference values transcribed from the
paper text into configs/paper_*.csv; these are always labelled "paper".

MPKI improvement (%) = (Baseline MPKI - Model MPKI) / Baseline MPKI * 100

Two aggregates are reported and always labelled:
  * "Mean"  : reduction of the arithmetic-mean MPKI over workloads -- this is
              what the official notebook artifact/analysis/mpki.ipynb plots.
  * "AvgRed": arithmetic mean of the per-workload reductions.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "results" / "processed" / "all_results.csv"
GRAPHS = ROOT / "results" / "graphs"
TABLES = ROOT / "results" / "tables"
PROC = ROOT / "results" / "processed"
CFG = ROOT / "configs"

ORDER = ["NodeApp", "PHPWiki", "TPCC", "Twitter", "Wikipedia", "Kafka", "Spring",
         "Tomcat", "Chirper", "HTTP", "Charlie", "Delta", "Merced", "Whiskey"]

# Fixed categorical slots (reference palette, documented adjacent-safe order).
# Colour follows the predictor everywhere; the baseline is neutral grey.
COL = {
    "64K TSL": "#8a8984",
    "LLBP": "#2a78d6",          # slot 1 blue
    "LLBP-X": "#eb6834",        # slot 2 orange
    "LLBP-X Opt-W": "#1baf7a",  # slot 3 aqua
    "512K TSL": "#eda100",      # slot 4 yellow
    "LLBP-X no-depth": "#e87ba4",  # slot 5 magenta
    "LLBP-X no-range": "#6250d6",  # slot 7 violet
    "LLBP-0Lat": "#2a78d6",
    "LLBP-X-0Lat": "#eb6834",
    "LLBP-X-0Lat no-depth": "#e87ba4",
    "LLBP-X-0Lat no-range": "#6250d6",
}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False,
    "savefig.dpi": 300, "figure.dpi": 110, "pdf.fonttype": 42,
})


def save(fig, name, caption):
    GRAPHS.mkdir(parents=True, exist_ok=True)
    fig.savefig(GRAPHS / f"{name}.png", bbox_inches="tight")
    fig.savefig(GRAPHS / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    CAPTIONS.append((name, caption))


CAPTIONS = []


def load():
    df = pd.read_csv(CSV)
    ok = df[df.status.isin(["OK", "OK_FULL_TRACE_WRAPPED"])].copy()
    return df, ok


def pivot(ok, metric="mpki"):
    p = ok.pivot_table(index="workload", columns="predictor", values=metric)
    return p.reindex([w for w in ORDER if w in p.index])


def reduction(p, base, model):
    return (p[base] - p[model]) / p[base] * 100.0


def grouped_bars(ax, p, models, x, width_total=0.84, labels=True):
    n = len(models)
    w = width_total / n
    for i, m in enumerate(models):
        off = -width_total / 2 + (i + 0.5) * w
        ax.bar(x + off, p[m].values, width=w * 0.92, color=COL[m], label=m,
               linewidth=0)


def md_table(df, path, floatfmt="{:.3f}"):
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
             "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    path.write_text("\n".join(lines) + "\n")


def main():
    df, ok = load()
    TABLES.mkdir(parents=True, exist_ok=True)
    mp = pivot(ok, "mpki")
    acc = pivot(ok, "accuracy") * 100.0
    misp = pivot(ok, "mispredictions")
    present = [m for m in COL if m in mp.columns]
    wl = list(mp.index)
    nW = len(wl)

    # ------------------------------------------------------------------ tables
    # T1: absolute MPKI, all predictors (+ Mean of MPKI)
    t = mp[present].copy()
    t.loc["Mean"] = t.mean()
    t.round(4).to_csv(TABLES / "table_mpki_all_predictors.csv")
    md_table(t.reset_index().rename(columns={"index": "workload"}),
             TABLES / "table_mpki_all_predictors.md", "{:.3f}")

    # T2: accuracy
    a = acc[present].copy()
    a.loc["Mean"] = a.mean()
    a.round(4).to_csv(TABLES / "table_accuracy_all_predictors.csv")
    md_table(a.reset_index().rename(columns={"index": "workload"}),
             TABLES / "table_accuracy_all_predictors.md", "{:.3f}")

    # T3: mispredictions
    misp[present].astype("Int64").to_csv(TABLES / "table_mispredictions.csv")

    # T4: reductions vs 64K TSL (Fig. 12 reproduction) + both aggregates
    fig12_models = [m for m in ["LLBP", "LLBP-X", "LLBP-X Opt-W", "512K TSL",
                                "LLBP-0Lat", "LLBP-X-0Lat"] if m in mp.columns]
    red = pd.DataFrame({m: reduction(mp, "64K TSL", m) for m in fig12_models})
    meanm = mp.mean()
    agg_mean = {m: (meanm["64K TSL"] - meanm[m]) / meanm["64K TSL"] * 100 for m in fig12_models}
    red_out = red.copy()
    red_out.loc["Mean (reduction of mean MPKI)"] = pd.Series(agg_mean)
    red_out.loc["AvgRed (mean of per-workload reductions)"] = red.mean()
    red_out.loc["Min"] = red.min()
    red_out.loc["Max"] = red.max()
    red_out.round(4).to_csv(TABLES / "table_mpki_reduction_vs_64k_tsl.csv")
    md_table(red_out.reset_index().rename(columns={"index": "workload"}),
             TABLES / "table_mpki_reduction_vs_64k_tsl.md", "{:.2f}")

    # T5: LLBP-X vs LLBP improvement (timing and 0-lat)
    pairs = [("LLBP", "LLBP-X"), ("LLBP-0Lat", "LLBP-X-0Lat"), ("LLBP", "LLBP-X Opt-W")]
    imp = pd.DataFrame({f"{b}->{m}": reduction(mp, b, m) for b, m in pairs
                        if b in mp.columns and m in mp.columns})
    imp_out = imp.copy()
    imp_out.loc["Mean (reduction of mean MPKI)"] = {
        f"{b}->{m}": (meanm[b] - meanm[m]) / meanm[b] * 100 for b, m in pairs
        if b in mp.columns and m in mp.columns}
    imp_out.loc["AvgRed (mean of per-workload reductions)"] = imp.mean()
    imp_out.loc["Min"] = imp.min()
    imp_out.loc["Max"] = imp.max()
    imp_out.round(4).to_csv(TABLES / "table_llbpx_vs_llbp.csv")
    md_table(imp_out.reset_index().rename(columns={"index": "workload"}),
             TABLES / "table_llbpx_vs_llbp.md", "{:.2f}")

    # T6: Table I reproduction
    paper = pd.read_csv(CFG / "paper_table1_mpki.csv").set_index("workload")
    t1 = pd.DataFrame({"paper_64k_tsl_mpki": paper.loc[wl, "paper_64k_tsl_mpki"],
                       "measured_64k_tsl_mpki": mp["64K TSL"]})
    t1["abs_diff"] = t1.measured_64k_tsl_mpki - t1.paper_64k_tsl_mpki
    t1["rel_diff_pct"] = t1.abs_diff / t1.paper_64k_tsl_mpki * 100
    t1.loc["Mean"] = [t1.paper_64k_tsl_mpki.mean(), t1.measured_64k_tsl_mpki.mean(),
                      np.nan, np.nan]
    t1.loc["Mean", "abs_diff"] = t1.loc["Mean", "measured_64k_tsl_mpki"] - t1.loc["Mean", "paper_64k_tsl_mpki"]
    t1.loc["Mean", "rel_diff_pct"] = t1.loc["Mean", "abs_diff"] / t1.loc["Mean", "paper_64k_tsl_mpki"] * 100
    t1.round(4).to_csv(TABLES / "table1_reproduction_64k_tsl.csv")
    md_table(t1.reset_index().rename(columns={"index": "workload"}),
             TABLES / "table1_reproduction_64k_tsl.md", "{:.3f}")

    # T7: Ablation / optimisation breakdown
    abl_sets = [("LLBP", "LLBP-X no-range", "LLBP-X no-depth", "LLBP-X", "timing"),
                ("LLBP-0Lat", "LLBP-X-0Lat no-range", "LLBP-X-0Lat no-depth", "LLBP-X-0Lat", "0-latency")]
    abl_rows = []
    for base, norange, nodepth, full, mode in abl_sets:
        if not all(c in mp.columns for c in (base, norange, nodepth, full)):
            continue
        for w in wl + ["Mean"]:
            v = meanm if w == "Mean" else mp.loc[w]
            gain_full = v[base] - v[full]
            abl_rows.append({
                "mode": mode, "workload": w,
                "mpki_llbp": v[base], "mpki_depth_only(no-range)": v[norange],
                "mpki_range_only(no-depth)": v[nodepth], "mpki_llbpx": v[full],
                "red_vs_llbp_depth_only_pct": (v[base] - v[norange]) / v[base] * 100,
                "red_vs_llbp_range_only_pct": (v[base] - v[nodepth]) / v[base] * 100,
                "red_vs_llbp_full_pct": gain_full / v[base] * 100,
                # Incremental attribution, order LLBP -> +depth -> +range:
                "share_depth_pct": (v[base] - v[norange]) / gain_full * 100 if gain_full else np.nan,
                "share_range_pct": (v[norange] - v[full]) / gain_full * 100 if gain_full else np.nan,
            })
    abl = pd.DataFrame(abl_rows)
    abl.round(4).to_csv(TABLES / "table_ablation_breakdown.csv", index=False)
    if len(abl):
        md_table(abl[abl.workload == "Mean"], TABLES / "table_ablation_breakdown_mean.md", "{:.3f}")

    # T8: runtime
    rt = ok.pivot_table(index="workload", columns="predictor", values="wall_s").reindex(wl)
    rt.round(1).to_csv(TABLES / "table_runtime_seconds.csv")

    # ------------------------------------------------------------------ graphs
    x = np.arange(nW + 1, dtype=float)
    x[-1] += 0.4
    xl = wl + ["Mean"]

    # G1 absolute MPKI
    models = [m for m in ["64K TSL", "LLBP", "LLBP-X", "LLBP-X Opt-W", "512K TSL"] if m in mp.columns]
    pm = mp[models].copy(); pm.loc["Mean"] = pm.mean()
    fig, ax = plt.subplots(figsize=(12, 3.8))
    grouped_bars(ax, pm, models, x)
    ax.set_xticks(x, xl, rotation=30, ha="right")
    ax.set_ylabel("Branch MPKI (mispredictions / 1000 instr.)")
    ax.set_ylim(0, np.nanmax(pm.values) * 1.22)
    ax.set_title("Conditional-branch MPKI per workload (lower is better)")
    ax.legend(ncol=len(models), loc="upper left", bbox_to_anchor=(0, 1.0))
    save(fig, "fig_mpki_all_predictors",
         "Absolute conditional-branch MPKI of 64K TSL, LLBP, LLBP-X, LLBP-X Opt-W and the "
         "ideal 512K TSL on the 14 server traces (100M warm-up + 200M measured instructions). "
         "'Mean' is the arithmetic mean MPKI.")

    # G2 accuracy (dot plot; non-zero axis is legitimate for position encodings)
    am = [m for m in ["64K TSL", "LLBP", "LLBP-X", "512K TSL"] if m in acc.columns]
    pa = acc[am].copy(); pa.loc["Mean"] = pa.mean()
    fig, ax = plt.subplots(figsize=(12, 3.8))
    offs = np.linspace(-0.27, 0.27, len(am))
    for i, m in enumerate(am):
        ax.plot(x + offs[i], pa[m].values, "o", ms=6, color=COL[m], label=m,
                markeredgecolor="white", markeredgewidth=0.8)
    ax.set_xticks(x, xl, rotation=30, ha="right")
    ax.set_ylabel("Prediction accuracy (%)")
    ax.set_title("Conditional-branch prediction accuracy per workload (higher is better)")
    ax.legend(ncol=len(am), loc="lower left")
    save(fig, "fig_accuracy",
         "Conditional-branch direction prediction accuracy (1 - mispredictions / conditional "
         "branches, in %) in the measured region. The y-axis does not start at zero because "
         "this is a position (dot) encoding; differences are small in absolute terms.")

    # G3 Fig. 12 reproduction: reduction vs 64K TSL
    fm = [m for m in ["LLBP", "LLBP-X", "LLBP-X Opt-W", "512K TSL"] if m in red.columns]
    pr = red[fm].copy(); pr.loc["Mean"] = pd.Series(agg_mean)[fm]
    fig, ax = plt.subplots(figsize=(12, 3.8))
    grouped_bars(ax, pr, fm, x)
    paper_agg = pd.read_csv(CFG / "paper_reported_aggregates.csv")
    for i, m in enumerate(fm):
        r = paper_agg[(paper_agg.predictor == m) & (paper_agg.metric == "MPKI reduction vs 64K TSL")]
        if len(r):
            off = -0.42 + (i + 0.5) * 0.84 / len(fm)
            ax.plot(x[-1] + off, r.avg_pct.values[0], marker="_", ms=14, mew=2.5, color=INK,
                    label="Paper-reported average" if i == 0 else None)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(x, xl, rotation=30, ha="right")
    ax.set_ylabel("MPKI reduction vs. 64K TSL (%)")
    ax.set_ylim(min(0, np.nanmin(pr.values)) - 1, np.nanmax(pr.values) * 1.2)
    ax.set_title("Reproduction of paper Fig. 12: branch MPKI reduction over 64K TSL (higher is better)")
    ax.legend(ncol=5, loc="upper left")
    save(fig, "fig12_mpki_reduction_vs_64k_tsl",
         "Reproduction of Fig. 12 of the paper: MPKI reduction relative to 64K TSL. "
         "'Mean' = reduction of mean MPKI (method of the official notebook). Black ticks on "
         "the Mean group mark the averages reported in the paper text.")

    # G4 LLBP-X vs LLBP per workload (sorted)
    if "LLBP->LLBP-X" in imp.columns:
        s = imp["LLBP->LLBP-X"].sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(10, 3.6))
        colors = [COL["LLBP-X"] if v >= 0 else "#8a8984" for v in s.values]
        ax.bar(np.arange(len(s)), s.values, color=colors, width=0.7)
        for i, v in enumerate(s.values):
            ax.text(i, v + (0.15 if v >= 0 else -0.15), f"{v:.1f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8, color=INK2, zorder=4,
                    bbox=dict(fc="white", ec="none", pad=0.6))
        ax.axhline(0, color=INK2, lw=0.8)
        m_ = imp_out.loc["Mean (reduction of mean MPKI)", "LLBP->LLBP-X"]
        ax.axhline(m_, color=INK, lw=1, ls="--")
        ax.text(len(s) - 0.5, m_, f" mean-MPKI reduction {m_:.2f}%", va="bottom", ha="right",
                fontsize=8, color=INK)
        ax.set_xticks(np.arange(len(s)), s.index, rotation=30, ha="right")
        ax.set_ylabel("MPKI improvement over LLBP (%)")
        ax.set_title("Workload-wise improvement of LLBP-X over original LLBP (both with prefetch latency)")
        save(fig, "fig_llbpx_vs_llbp_per_workload",
             "Per-workload MPKI improvement of LLBP-X over LLBP, "
             "(MPKI_LLBP - MPKI_LLBP-X)/MPKI_LLBP x 100, sorted. Grey bars would indicate regressions.")

    # G5 LLBP-X vs TAGE-SC-L scatter
    fig, ax = plt.subplots(figsize=(5.6, 5.0))
    lim = max(mp["64K TSL"].max(), mp["LLBP-X"].max()) * 1.08
    ax.plot([0, lim], [0, lim], color=INK2, lw=0.8, ls="--", label="y = x (no change)")
    ax.scatter(mp["64K TSL"], mp["LLBP-X"], s=40, color=COL["LLBP-X"], label="LLBP-X",
               edgecolor="white", linewidth=0.8, zorder=3)
    if "512K TSL" in mp:
        ax.scatter(mp["64K TSL"], mp["512K TSL"], s=40, color=COL["512K TSL"], marker="s",
                   label="512K TSL (ideal)", edgecolor="white", linewidth=0.8, zorder=3)
    # Hand-tuned label offsets (points) to avoid collisions in the dense cluster.
    offs = {"HTTP": (-17, -3), "Charlie": (-22, 4), "PHPWiki": (4, -6), "Twitter": (-20, 5),
            "Tomcat": (-20, 4), "TPCC": (4, -6), "Kafka": (5, -5), "Spring": (4, 2)}
    for w in wl:
        ax.annotate(w, (mp.loc[w, "64K TSL"], mp.loc[w, "LLBP-X"]), fontsize=7,
                    color=INK2, xytext=offs.get(w, (3, 3)), textcoords="offset points")
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.grid(True, axis="both")
    ax.set_xlabel("64K TAGE-SC-L MPKI")
    ax.set_ylabel("Predictor MPKI")
    ax.set_title("LLBP-X vs. 64K TAGE-SC-L (points below diagonal = fewer mispredictions)")
    ax.legend(loc="upper left", fontsize=8)
    save(fig, "fig_llbpx_vs_tsl_scatter",
         "Per-workload MPKI of LLBP-X and of the ideal 512K TSL plotted against the 64K TSL baseline.")

    # G6 overall comparison: mean MPKI per configuration
    allm = [m for m in ["64K TSL", "LLBP-0Lat", "LLBP", "LLBP-X-0Lat", "LLBP-X",
                        "LLBP-X Opt-W", "512K TSL"] if m in mp.columns]
    mm = mp[allm].mean()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    y = np.arange(len(allm))[::-1]
    ax.barh(y, mm.values, color=[COL[m] for m in allm], height=0.62)
    for yi, m in zip(y, allm):
        r = (mm["64K TSL"] - mm[m]) / mm["64K TSL"] * 100
        ax.text(mm[m] + 0.02, yi, f"{mm[m]:.3f}" + ("" if m == "64K TSL" else f"  (-{r:.1f}%)"),
                va="center", fontsize=8, color=INK)
    ax.set_yticks(y, allm)
    ax.grid(True, axis="x"); ax.grid(False, axis="y")
    ax.set_xlabel("Mean branch MPKI over 14 workloads")
    ax.set_xlim(0, mm.max() * 1.3)
    ax.set_title("Overall comparison: mean MPKI per predictor configuration")
    save(fig, "fig_overall_mean_mpki",
         "Arithmetic-mean MPKI over the 14 workloads; the percentage is the reduction of mean MPKI vs. 64K TSL. "
         "'-0Lat' variants do not model the pattern-store prefetch latency. IPC is not available "
         "from the trace-based simulator.")

    # G7 Table I reproduction
    fig, ax = plt.subplots(figsize=(11, 3.4))
    t1w = t1.drop(index="Mean")
    xx = np.arange(len(t1w))
    ax.bar(xx - 0.2, t1w.paper_64k_tsl_mpki, 0.38, color="#c3c2b7", label="Paper Table I")
    ax.bar(xx + 0.2, t1w.measured_64k_tsl_mpki, 0.38, color=COL["64K TSL"], label="This work (measured)")
    ax.set_xticks(xx, t1w.index, rotation=30, ha="right")
    ax.set_ylabel("64K TSL branch MPKI")
    ax.set_title("Reproduction of paper Table I: 64K TAGE-SC-L baseline MPKI")
    ax.legend()
    save(fig, "fig_table1_reproduction",
         "Baseline 64K TSL MPKI measured with the official CBP-style simulator vs. the values in Table I "
         "of the paper (which were obtained with the authors' ChampSim integration).")

    # G8 ablation
    if len(abl):
        ab = abl[abl["mode"] == "timing"].set_index("workload").reindex(wl + ["Mean"])
        cols = [("red_vs_llbp_range_only_pct", "LLBP-X no-depth"),
                ("red_vs_llbp_depth_only_pct", "LLBP-X no-range"),
                ("red_vs_llbp_full_pct", "LLBP-X")]
        fig, ax = plt.subplots(figsize=(12, 3.8))
        wt = 0.84 / 3
        for i, (c, lab) in enumerate(cols):
            ax.bar(x - 0.42 + (i + 0.5) * wt, ab[c].values, wt * 0.92, color=COL[lab],
                   label={"LLBP-X no-depth": "Range selection only (depth adaptation off)",
                          "LLBP-X no-range": "Depth adaptation only (range selection off)",
                          "LLBP-X": "Full LLBP-X"}[lab])
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_xticks(x, xl, rotation=30, ha="right")
        ax.set_ylabel("MPKI reduction vs. LLBP (%)")
        vals_ = ab[[c for c, _ in cols]].values
        ax.set_ylim(np.nanmin(vals_) - 1, np.nanmax(vals_) * 1.25)
        ax.set_title("Optimization breakdown (our ablation; paper Sec. VII-E, graph omitted in paper)")
        ax.legend(ncol=3, loc="upper left", fontsize=8)
        save(fig, "fig_ablation_breakdown",
             "Ablation of the two LLBP-X optimizations, all with prefetch latency modelled, relative to LLBP. "
             "Ablation models are project additions (runtime switches in the official LLBP-X model).")

    # G9 simulation time
    rm = [m for m in ["64K TSL", "512K TSL", "LLBP", "LLBP-X", "LLBP-X Opt-W"] if m in rt.columns]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    vals = rt[rm].mean() / 60
    ax.bar(np.arange(len(rm)), vals.values, color=[COL[m] for m in rm], width=0.6)
    for i, v in enumerate(vals.values):
        ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(np.arange(len(rm)), rm)
    ax.set_ylabel("Mean wall-clock time (min)")
    ax.set_title("Simulation cost per run (300M instructions, concurrent runs)")
    save(fig, "fig_simulation_time",
         "Mean wall-clock time per simulation run. Runs executed concurrently on a 17-core VM, so "
         "absolute times include contention; they are not predictor latencies.")

    # G10 / T9 pattern-store transfer bandwidth (trace-based estimate of paper Fig. 15a)
    bw_models = [m for m in ["LLBP", "LLBP-X", "LLBP-X Opt-W"] if m in mp.columns]
    sub = ok[ok.predictor.isin(bw_models) & ok.ps_reads.notna()].copy()
    if len(sub):
        BITS = 288  # bits per pattern-set read/write transaction (paper Sec. VII-D)
        sub["read_bits_per_instr"] = sub.ps_reads * BITS / sub.roi_instructions
        sub["write_bits_per_instr"] = sub.ps_writes * BITS / sub.roi_instructions
        sub["total_bits_per_instr"] = sub.read_bits_per_instr + sub.write_bits_per_instr
        bw = sub.pivot_table(index="workload", columns="predictor",
                             values="total_bits_per_instr").reindex(wl)
        bw.loc["Mean"] = bw.mean()
        bw.round(4).to_csv(TABLES / "table_bandwidth_bits_per_instr.csv")
        md_table(bw.reset_index().rename(columns={"index": "workload"}),
                 TABLES / "table_bandwidth_bits_per_instr.md", "{:.2f}")
        agg = sub.groupby("predictor")[["read_bits_per_instr", "write_bits_per_instr"]].mean().reindex(bw_models)
        agg.round(4).to_csv(TABLES / "table_bandwidth_mean_read_write.csv")
        fig, ax = plt.subplots(figsize=(8, 2.8))
        y = np.arange(len(bw_models))[::-1]
        ax.barh(y, agg.read_bits_per_instr, height=0.55, color=[COL[m] for m in bw_models], label="Reads")
        ax.barh(y, agg.write_bits_per_instr, left=agg.read_bits_per_instr + 0.03, height=0.55,
                color=[COL[m] for m in bw_models], alpha=0.45, label="Writes (lighter)")
        for yi, m in zip(y, bw_models):
            t = agg.loc[m].sum()
            ax.text(t + 0.12, yi, f"{t:.2f} bits/instr (R {agg.loc[m, 'read_bits_per_instr']:.2f} + "
                    f"W {agg.loc[m, 'write_bits_per_instr']:.2f})", va="center", fontsize=8, color=INK)
        ax.set_yticks(y, bw_models)
        ax.set_xlim(0, agg.sum(axis=1).max() * 1.7)
        ax.grid(True, axis="x"); ax.grid(False, axis="y")
        ax.set_xlabel("Pattern store <-> pattern buffer traffic (bits per instruction)")
        ax.set_title("Transfer bandwidth (trace-based estimate of paper Fig. 15a)")
        save(fig, "fig_bandwidth",
             "Pattern-store traffic per instruction, averaged over the 14 workloads: reads = pattern sets "
             "fetched from the pattern store (HitInCI), writes = dirty write-backs, 288 bits each. Trace-based "
             "(no wrong-path execution), so it is not directly comparable with the gem5 numbers of the paper.")

    # captions index
    (GRAPHS / "CAPTIONS.md").write_text(
        "# Figure captions\n\n" + "\n".join(f"* **{n}** — {c}" for n, c in CAPTIONS) + "\n")
    # Summary json-ish for the report
    summ = {
        "n_workloads": nW,
        "n_ok_runs": int(df.status.isin(["OK", "OK_FULL_TRACE_WRAPPED"]).sum()),
        "n_full_trace_wrapped": int((df.status == "OK_FULL_TRACE_WRAPPED").sum()),
        "n_runs": int(len(df)),
    }
    pd.Series(summ).to_csv(PROC / "summary_counts.csv", header=["value"])
    print("figures:", len(CAPTIONS), "| workloads:", nW, "|", summ)


if __name__ == "__main__":
    main()
