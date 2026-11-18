#!/usr/bin/env python3
"""parse_results.py -- consolidate raw simulator logs into CSV.  [NEW, project team]

Reads every results/raw/<trace>/<model>.txt written by run_experiments.sh and
extracts the statistics printed by the official simulator (artifact/main.cc):
  ROI INSTRUCTIONS, ROI MISPREDICTIONS, ROI MPKI, ROI COND BRANCHES, ROI ACCURACY
plus wall time / max RSS appended by the driver.  No value is computed by hand
except accuracy re-derivation as a cross-check.

Output: results/processed/all_results.csv  (one row per predictor x workload)
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"
OUT = ROOT / "results" / "processed" / "all_results.csv"

# Display names used in the paper (Table I).
WORKLOADS = {
    "nodeapp-nodeapp": "NodeApp",
    "mwnginxfpm-wiki": "PHPWiki",
    "benchbase-tpcc": "TPCC",
    "benchbase-twitter": "Twitter",
    "benchbase-wikipedia": "Wikipedia",
    "dacapo-kafka": "Kafka",
    "dacapo-spring": "Spring",
    "dacapo-tomcat": "Tomcat",
    "renaissance-finagle-chirper": "Chirper",
    "renaissance-finagle-http": "HTTP",
    "charlie.1006518": "Charlie",
    "delta.507252": "Delta",
    "merced.467915": "Merced",
    "whiskey.426708": "Whiskey",
}
WORKLOAD_ORDER = list(WORKLOADS)

# Human-readable description of each model (see artifact/bpmodels/*).
MODELS = {
    "tage64kscl": ("64K TSL", "TAGE-SC-L 64KB baseline"),
    "tage512kscl": ("512K TSL", "TAGE-SC-L 512KB, idealised 0-latency upper bound"),
    "llbp": ("LLBP-0Lat", "LLBP, W=8, D=4, no prefetch latency"),
    "llbp-timing": ("LLBP", "LLBP, W=8, D=4, prefetch latency modelled"),
    "llbpx": ("LLBP-X-0Lat", "LLBP-X, no prefetch latency"),
    "llbpx-timing": ("LLBP-X", "LLBP-X, prefetch latency modelled"),
    "llbpx-optw": ("LLBP-X Opt-W", "LLBP-X with offline-optimal W per context, latency modelled"),
    "llbpx-timing-nodepth": ("LLBP-X no-depth", "Ablation: depth adaptation off, latency modelled"),
    "llbpx-timing-norange": ("LLBP-X no-range", "Ablation: history range selection off, latency modelled"),
    "llbpx-nodepth": ("LLBP-X-0Lat no-depth", "Ablation: depth adaptation off, 0-latency"),
    "llbpx-norange": ("LLBP-X-0Lat no-range", "Ablation: history range selection off, 0-latency"),
}

PATTERNS = {
    "roi_instructions": r"ROI INSTRUCTIONS\s*:\s*(\d+)",
    "mispredictions": r"ROI MISPREDICTIONS\s*:\s*(\d+)",
    "mpki": r"ROI MPKI\s*:\s*([\d.]+)",
    "cond_branches": r"ROI COND BRANCHES\s*:\s*(\d+)",
    "accuracy": r"ROI ACCURACY\s*:\s*([\d.]+)",
    "total_instructions": r"NUM_INSTRUCTIONS\s*:\s*(\d+)",
    "wall_s": r"WALL_SECONDS\s+([\d.]+)",
    "maxrss_kb": r"MAXRSS_KB\s+(\d+)",
}


def zenodo_sizes():
    f = ROOT / "configs" / "zenodo_trace_files.csv"
    sizes = {}
    if f.exists():
        for r in csv.DictReader(f.open()):
            sizes[r["file"].split(".champsim")[0]] = int(r["size_bytes"])
    return sizes


def trace_complete(trace: str, sizes: dict) -> bool:
    """True if the local trace file is the complete Zenodo file."""
    p = ROOT / "artifact" / "traces" / f"{trace}.champsim.trace.gz"
    if p.exists():
        return trace in sizes and p.stat().st_size == sizes[trace]
    # Trace not downloaded (e.g. only re-parsing the committed raw results):
    # fall back to the manifest recorded when the original runs were made.
    m = ROOT / "logs" / "trace_manifest.csv"
    if m.exists():
        for r in csv.DictReader(m.open(newline="")):
            if r["file"] == f"{trace}.champsim.trace.gz":
                return r["complete"] == "True"
    return False
def parse(path: Path, warm: int, sim: int, complete: bool = False) -> dict:
    text = path.read_text(errors="replace")
    row = {}
    for key, pat in PATTERNS.items():
        m = re.search(pat, text)
        row[key] = m.group(1) if m else ""
    # Pattern-store traffic of the timing models, from the final statistics
    # block (after "REGION OF INTEREST"; counters are reset after warm-up):
    #   reads  = PB Prefetch HitInCI (pattern set read from the pattern store)
    #   writes = PB Evict Dirty      (dirty pattern set written back)
    final = text.split("REGION OF INTEREST")[-1] if "REGION OF INTEREST" in text else ""
    m1 = re.search(r"HitInCI:(\d+)", final)
    m2 = re.search(r"PB Evict:\[Clean:(\d+)\([\d.]+\) Dirty:(\d+)", final)
    row["ps_reads"] = m1.group(1) if m1 else ""
    row["ps_writes"] = m2.group(2) if m2 else ""
    wrapped = "Reached end of trace" in text
    # Instruction count (in M) of the last heartbeat before the trace wrapped.
    row["wrap_at_minstr"] = ""
    if wrapped:
        head = text.split("Reached end of trace")[0]
        hb = re.findall(r"Ninst: (\d+)M", head)
        row["wrap_at_minstr"] = hb[-1] if hb else ""
    row["trace_complete"] = int(complete)
    m = re.search(r"Loading (\d+) useful entries", text)
    row["optw_entries"] = m.group(1) if m else ""
    if not row["accuracy"]:
        status = "FAILED"
    elif wrapped and complete:
        # The complete official trace is shorter than warm-up + ROI; the
        # official simulator repeats it. Inherent to the official methodology.
        status = "OK_FULL_TRACE_WRAPPED"
    elif wrapped:
        # Our prefix was too short -> invalid, must be re-run on a longer prefix.
        status = "TRACE_WRAPPED"
    elif int(row["roi_instructions"]) < 0.99 * sim:
        status = "SHORT"
    elif row["optw_entries"] == "0":
        status = "OPTW_NO_TABLE"
    else:
        status = "OK"
    row["status"] = status
    return row


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=RAW)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--warm", type=int, default=100_000_000)
    ap.add_argument("--sim", type=int, default=200_000_000)
    a = ap.parse_args()
    warm, sim, raw, out = a.warm, a.sim, a.raw, a.out
    rows = []
    sizes = zenodo_sizes()
    extra = sorted(p.name for p in raw.iterdir() if p.is_dir() and p.name not in WORKLOADS)
    for trace in WORKLOAD_ORDER + extra:
        d = raw / trace
        if not d.is_dir():
            continue
        for model, (label, desc) in MODELS.items():
            f = d / f"{model}.txt"
            if not f.exists():
                continue
            r = parse(f, warm, sim, trace_complete(trace, sizes))
            # Cross-check: accuracy = 1 - misp / cond_branches
            if r["accuracy"] and r["cond_branches"]:
                acc = 1 - int(r["mispredictions"]) / int(r["cond_branches"])
                assert abs(acc - float(r["accuracy"])) < 1e-5, (f, acc)
                mpki = 1000 * int(r["mispredictions"]) / int(r["roi_instructions"])
                assert abs(mpki - float(r["mpki"])) < 1e-3, (f, mpki)
            rows.append({
                "predictor": label,
                "model_id": model,
                "configuration": desc,
                "workload": WORKLOADS.get(trace, trace),
                "trace": f"{trace}.champsim.trace.gz",
                "warmup_instructions": warm,
                "sim_instructions": sim,
                **r,
            })
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["predictor", "model_id", "configuration", "workload", "trace",
            "warmup_instructions", "sim_instructions", "roi_instructions",
            "total_instructions", "cond_branches", "mispredictions", "mpki",
            "accuracy", "ps_reads", "ps_writes", "optw_entries", "trace_complete", "wrap_at_minstr",
            "wall_s", "maxrss_kb", "status"]
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    bad = [r for r in rows if r["status"] not in ("OK", "OK_FULL_TRACE_WRAPPED")]
    nw = sum(r["status"] == "OK_FULL_TRACE_WRAPPED" for r in rows)
    print(f"valid runs on complete-but-short traces (wrapped, labelled): {nw}")
    print(f"wrote {out} with {len(rows)} rows; non-OK: {len(bad)}")
    for r in bad:
        print("  ", r["model_id"], r["workload"], r["status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
