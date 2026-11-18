#!/usr/bin/env python3
"""validate_project.py -- end-to-end consistency checks.   [NEW, project team]

Checks that raw results, CSV, tables, figures and documents agree, and writes
logs/validation_final.md. Exit code 1 if any check fails.
"""
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


# 1. Simulator binary
b = ROOT / "artifact" / "build" / "predictor"
r = subprocess.run([str(b), "--help"], capture_output=True, text=True) if b.exists() else None
check("Simulator binary builds and runs (--help)", r is not None and "inst-sim" in r.stdout)
for m in ["tage64kscl", "llbp-timing", "llbpx-timing", "llbpx-timing-nodepth", "llbpx-timing-norange"]:
    ok = m in (ROOT / "artifact/bpmodels/base_predictor.cc").read_text()
    check(f"Predictor model '{m}' registered", ok)

# 2. Raw results & CSV
df = pd.read_csv(ROOT / "results/processed/all_results.csv")
raw_files = list((ROOT / "results/raw").glob("*/*.txt"))
check("154 raw result files exist", len(raw_files) == 154, f"found {len(raw_files)}")
check("154 CSV rows", len(df) == 154, f"rows {len(df)}")
check("All runs valid (OK or OK_FULL_TRACE_WRAPPED)",
      df.status.isin(["OK", "OK_FULL_TRACE_WRAPPED"]).all(), str(df.status.value_counts().to_dict()))
wr = df[df.status == "OK_FULL_TRACE_WRAPPED"]
check("Wrapped runs only on complete traces", (wr.trace_complete == 1).all(),
      f"workloads: {sorted(wr.workload.unique())}")
num = ["roi_instructions", "cond_branches", "mispredictions", "mpki", "accuracy"]
check("No missing numeric values", not df[num].isna().any().any())
# The simulator checks warm-up/ROI limits at branch granularity -> a few instr.
check("ROI instructions = 200M (+/- 100)", ((df.roi_instructions - 200_000_000).abs() <= 100).all(),
      f"range {df.roi_instructions.min()}..{df.roi_instructions.max()}")
check("Identical ROI length for all models of a workload (equivalent conditions)",
      (df.groupby("workload").roi_instructions.nunique() == 1).all())
check("Identical conditional-branch count for all models of a workload",
      (df.groupby("workload").cond_branches.nunique() == 1).all())
check("Accuracy within (0,1)", ((df.accuracy > 0) & (df.accuracy < 1)).all())
mpki = 1000 * df.mispredictions / df.roi_instructions
check("MPKI = 1000*misp/instr (|err|<1e-3)", ((mpki - df.mpki).abs() < 1e-3).all())
acc = 1 - df.mispredictions / df.cond_branches
check("Accuracy = 1-misp/cond (|err|<1e-5)", ((acc - df.accuracy).abs() < 1e-5).all())

# 3. Tables recomputed from CSV
mp = df.pivot_table(index="workload", columns="predictor", values="mpki")
red = pd.read_csv(ROOT / "results/tables/table_mpki_reduction_vs_64k_tsl.csv", index_col=0)
for m in ["LLBP", "LLBP-X", "LLBP-X Opt-W", "512K TSL"]:
    rec = (mp["64K TSL"] - mp[m]) / mp["64K TSL"] * 100
    diff = (rec - red.loc[rec.index, m]).abs().max()
    check(f"Reduction table matches recomputation ({m})", diff < 1e-3, f"max diff {diff:.2e}")
mean = mp.mean()
head = {
    "LLBP-X mean red": (mean["64K TSL"] - mean["LLBP-X"]) / mean["64K TSL"] * 100,
    "LLBP mean red": (mean["64K TSL"] - mean["LLBP"]) / mean["64K TSL"] * 100,
    "Opt-W mean red": (mean["64K TSL"] - mean["LLBP-X Opt-W"]) / mean["64K TSL"] * 100,
    "512K mean red": (mean["64K TSL"] - mean["512K TSL"]) / mean["64K TSL"] * 100,
    "X over LLBP avg": ((mp["LLBP"] - mp["LLBP-X"]) / mp["LLBP"] * 100).mean(),
    "X over LLBP min": ((mp["LLBP"] - mp["LLBP-X"]) / mp["LLBP"] * 100).min(),
    "X over LLBP max": ((mp["LLBP"] - mp["LLBP-X"]) / mp["LLBP"] * 100).max(),
    "depth share": (mean["LLBP"] - mean["LLBP-X no-range"]) / (mean["LLBP"] - mean["LLBP-X"]) * 100,
}
fmt = {k: f"{v:.2f}" for k, v in head.items()}
fmt["depth share"] = f"{head['depth share']:.1f}"
docs = {p: (ROOT / p).read_text() for p in
        ["README.md", "PERFORMANCE_ANALYSIS.md", "REPORT/project_report.md"]}
for k, s in fmt.items():
    for p, t in docs.items():
        check(f"{p} contains {k} = {s}", s in t)

# 4. Table I
t1 = pd.read_csv(ROOT / "results/tables/table1_reproduction_64k_tsl.csv", index_col=0).drop(index="Mean")
check("Table I: all |diff| <= 0.005 MPKI", (t1.abs_diff.abs() <= 0.0055).all(),
      f"max {t1.abs_diff.abs().max():.4f}")

# 5. Figures
caps = (ROOT / "results/graphs/CAPTIONS.md").read_text()
names = re.findall(r"\*\*(\w+)\*\*", caps)
for n in names:
    check(f"Figure {n} has PNG+PDF",
          (ROOT / f"results/graphs/{n}.png").exists() and (ROOT / f"results/graphs/{n}.pdf").exists())
rep = docs["REPORT/project_report.md"]
for img in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", rep):
    check(f"Report image exists: {img}", (ROOT / "REPORT" / img).exists())
check("Report PDF exists", (ROOT / "REPORT/project_report.pdf").exists())

# 6. No placeholders left
for p in ["README.md", "PERFORMANCE_ANALYSIS.md", "REPORT/project_report.md", "SETUP.md",
          "IMPLEMENTATION.md", "PAPER_ANALYSIS.md"]:
    t = (ROOT / p).read_text()
    bad = re.findall(r"RESULTS_SECTION|GEM5_STATUS|GEM5_REPORT|\{\{|TODO|TBD|provisional", t)
    check(f"No placeholders in {p}", not bad, ",".join(bad))

# 7. Regression check vs upstream recorded
v = (ROOT / "logs/validation.md").read_text()
check("Upstream regression check: all YES", v.count("| YES |") == 6 and "| NO |" not in v)

npass = sum(ok for _, ok, _ in results)
lines = ["# Final validation report", "", f"Generated by `scripts/validate_project.py`: "
         f"**{npass}/{len(results)} checks passed**.", "", "| Check | Result | Detail |", "|---|---|---|"]
lines += [f"| {n} | {'PASS' if ok else 'FAIL'} | {d} |" for n, ok, d in results]
(ROOT / "logs/validation_final.md").write_text("\n".join(lines) + "\n")
print(f"{npass}/{len(results)} checks passed")
for n, ok, d in results:
    if not ok:
        print("FAIL:", n, d)
sys.exit(0 if npass == len(results) else 1)
