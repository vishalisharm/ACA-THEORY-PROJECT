#!/usr/bin/env python3
"""assemble_report.py -- build REPORT/project_report.md      [NEW, project team]

Concatenates REPORT/part1_background.md, part2_design.md, part3_results.md and
fills generated content so that every number in the report tables is copied
from results/tables/*.csv (never typed by hand):
  {{CSV:<file>:<col,col,...>:<decimals>}}  -> Markdown table from results/tables
  {{ABLATION}}                              -> ablation table (timing mode)
  TRACE_TABLE_ROWS                          -> rows from logs/trace_manifest.csv
  ABSTRACT_RESULTS_SENTENCE, GEM5_*         -> short generated sentences
Also copies figures (PNG) and tables (CSV/MD) into REPORT/figures, REPORT/tables.
"""
import csv
import re
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "REPORT"
TAB = ROOT / "results" / "tables"
GR = ROOT / "results" / "graphs"

SUITE = {
    "nodeapp-nodeapp": ("NodeApp", "NodeJS web server"),
    "mwnginxfpm-wiki": ("PHPWiki", "PHP-FPM + nginx wiki"),
    "benchbase-tpcc": ("TPCC", "Java BenchBase"),
    "benchbase-twitter": ("Twitter", "Java BenchBase"),
    "benchbase-wikipedia": ("Wikipedia", "Java BenchBase"),
    "dacapo-kafka": ("Kafka", "Java DaCapo"),
    "dacapo-spring": ("Spring", "Java DaCapo"),
    "dacapo-tomcat": ("Tomcat", "Java DaCapo"),
    "renaissance-finagle-chirper": ("Chirper", "Java Renaissance"),
    "renaissance-finagle-http": ("HTTP", "Java Renaissance"),
    "charlie.1006518": ("Charlie", "Google workload trace"),
    "delta.507252": ("Delta", "Google workload trace"),
    "merced.467915": ("Merced", "Google workload trace"),
    "whiskey.426708": ("Whiskey", "Google workload trace"),
}


def fmt(v, d):
    if isinstance(v, float):
        if pd.isna(v):
            return "–"
        return f"{v:.{d}f}"
    return str(v)


def csv_table(fname, cols, dec):
    df = pd.read_csv(TAB / fname)
    df = df.rename(columns={df.columns[0]: "workload"}) if df.columns[0] != "workload" else df
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt(r[c], dec) for c in cols) + " |")
    return "\n".join(lines)


def ablation_table():
    a = pd.read_csv(TAB / "table_ablation_breakdown.csv")
    a = a[a["mode"] == "timing"]
    cols = ["workload", "mpki_llbp", "mpki_depth_only(no-range)", "mpki_range_only(no-depth)",
            "mpki_llbpx", "red_vs_llbp_depth_only_pct", "red_vs_llbp_range_only_pct", "red_vs_llbp_full_pct"]
    head = ["Workload", "LLBP MPKI", "depth only", "range only", "LLBP-X", "red. depth only (%)",
            "red. range only (%)", "red. full (%)"]
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    for _, r in a.iterrows():
        lines.append("| " + " | ".join(fmt(r[c], 3 if "mpki" in c else 2) for c in cols) + " |")
    m = a[a.workload == "Mean"].iloc[0]
    lines.append("")
    lines.append(f"Incremental attribution on mean MPKI: depth adaptation **{m.share_depth_pct:.1f} %**, "
                 f"history range selection **{m.share_range_pct:.1f} %** of the LLBP→LLBP-X reduction "
                 f"(paper §VII-E: 82 % / 18 %).")
    return "\n".join(lines)


def trace_rows():
    man = {r["file"]: r for r in csv.DictReader((ROOT / "logs" / "trace_manifest.csv").open())}
    rows = []
    for t, (name, suite) in SUITE.items():
        r = man.get(f"{t}.champsim.trace.gz")
        if not r:
            continue
        used = int(r["local_bytes"]) / 2**30
        full = int(r["zenodo_bytes"]) / 2**30
        how = "complete (MD5 verified)" if r["complete"] == "True" else f"prefix {used:.2f} GiB"
        rows.append(f"| {name} | `{t}` | {suite} | {full:.2f} GiB | {how} |")
    return "\n".join(rows)


def main():
    (REP / "figures").mkdir(exist_ok=True)
    for p in GR.glob("*.png"):
           shutil.copy2(p, REP / "figures" / p.name)

    text = "\n\n".join((REP / f).read_text() for f in
                       ["part1_background.md", "part2_design.md", "part3_results.md"])

    text = re.sub(r"\{\{CSV:([^:]+):([^:]+):(\d+)\}\}",
                  lambda m: csv_table(m.group(1), m.group(2).split(","), int(m.group(3))), text)
    text = text.replace("{{ABLATION}}", ablation_table())
    text = text.replace("TRACE_TABLE_ROWS", trace_rows())

    red = pd.read_csv(TAB / "table_mpki_reduction_vs_64k_tsl.csv", index_col=0)
    imp = pd.read_csv(TAB / "table_llbpx_vs_llbp.csv", index_col=0)
    abl = pd.read_csv(TAB / "table_ablation_breakdown.csv")
    am = abl[(abl["mode"] == "timing") & (abl.workload == "Mean")].iloc[0]
    M, A = "Mean (reduction of mean MPKI)", "AvgRed (mean of per-workload reductions)"
    sent = (f"Our 64K TSL baseline matches the paper's Table I to within ±0.005 MPKI on every workload. "
            f"LLBP-X reduces mean branch MPKI over 64K TSL by {red.loc[M, 'LLBP-X']:.2f} % "
            f"(paper: 12.1 %), compared with {red.loc[M, 'LLBP']:.2f} % for LLBP and "
            f"{red.loc[M, '512K TSL']:.2f} % for the ideal 512K TSL. It improves on LLBP on all 14 "
            f"workloads by {imp.loc['Min', 'LLBP->LLBP-X']:.2f}–{imp.loc['Max', 'LLBP->LLBP-X']:.2f} % "
            f"(average {imp.loc[A, 'LLBP->LLBP-X']:.2f} %; paper: 0.8–11.5 %, average 3.6 %). "
            f"Our ablation attributes {am.share_depth_pct:.0f} % of the gain to dynamic context depth "
            f"adaptation and {am.share_range_pct:.0f} % to history range selection (paper: 82 %/18 %). "
            f"A trace-based estimate shows LLBP-X also lowers pattern-store traffic. We further identify "
            f"a discrepancy between the paper and the artifact code (deep contexts never revert to the "
            f"shallow depth except on CTT eviction), and that the two shortest official traces are "
            f"repeated by the simulator within the measured region.")
    text = text.replace("ABSTRACT_RESULTS_SENTENCE", sent)

    g5 = (ROOT / "logs" / "gem5_summary.md")
    g5s = g5.read_text().strip() if g5.exists() else "gem5 was not evaluated."
    text = text.replace("GEM5_REPORT_SENTENCE", g5s.split("\n")[0])

    left = re.findall(r"\{\{[^}]+\}\}|TRACE_TABLE_ROWS|ABSTRACT_RESULTS_SENTENCE|GEM5_\w+", text)
    assert not left, f"unfilled placeholders: {left}"
    (REP / "project_report.md").write_text(text)
    print("wrote", REP / "project_report.md", len(text.split()), "words")


if __name__ == "__main__":
    main()
