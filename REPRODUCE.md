# How to reproduce the results

This repository reproduces the trace-based evaluation of **LLBP-X** (*The Last-Level Branch Predictor Revisited*, HPCA 2026) with the authors' branch-predictor simulator (`artifact/`), and adds an ablation study and a depth-reversion extension.

There are two ways to reproduce it:

| Path | What it does | Needs | Time |
|---|---|---|---|
| **A. Regenerate tables and figures** | Re-parses the committed raw simulator output (`results/raw/`) and rebuilds every table and graph | Python only (Windows, Linux or macOS) | about 1 minute |
| **B. Re-run all simulations** | Builds the simulator, downloads the traces, runs 154 simulations (11 models x 14 traces) | Linux or WSL2, about 15 GiB disk, about 1.5 h on 12 cores plus download time | hours |

> **Windows users:** the shell scripts in `scripts/` use `bash`, `/usr/bin/time`, `bc`, `nproc`, `stat -c` and `wait -n`. Run Path B inside **WSL2 (Ubuntu)** or a Linux machine. Path A works anywhere Python runs.

---

## Path A: regenerate tables and figures (no simulation)

```bash
git clone https://github.com/vishalisharm/ACA-THEORY-PROJECT.git
cd ACA-THEORY-PROJECT

python3 -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

python scripts/parse_results.py      # results/raw/  ->  results/processed/all_results.csv
python scripts/make_figures.py       # -> results/graphs/ and results/tables/
```

Expected output of the last two commands:

```
wrote .../results/processed/all_results.csv with 154 rows; non-OK: 0
figures: 10 | workloads: 14 | {... 'n_ok_runs': 154, 'n_full_trace_wrapped': 22, 'n_runs': 154}
```

The regenerated tables in `results/tables/` should be identical to the committed ones. Run `git status` afterwards; no table should show as modified.

Optional extras:

```bash
python scripts/make_diagrams.py      # schematic diagrams -> REPORT/figures
python scripts/assemble_report.py    # assemble REPORT/project_report.md
python scripts/build_report_pdf.py   # PDF (needs weasyprint and its system libraries)
python scripts/extension_analysis.py revert   # extension tables and figure -> results/extension/
```

---

## Path B: re-run the simulations (Linux or WSL2)

### 1. System packages
```bash
sudo apt update
sudo apt install -y build-essential cmake libboost-all-dev gzip curl bc time python3-venv
```
Tested with GCC 13.3, CMake 3.28, Boost 1.83, Python 3.12 on Ubuntu 24.04. The artifact needs a C++20 compiler and CMake 3.22 or newer.

### 2. Python environment
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Build the simulator
```bash
cmake -S artifact -B artifact/build -DCMAKE_BUILD_TYPE=Release
cmake --build artifact/build -j $(nproc)
```
This produces `artifact/build/predictor`. Check it with `artifact/build/predictor --help`.

The `artifact/` folder is the authors' code (upstream commit `68e1cae`) with our changes marked `[PROJECT-MOD]`. The exact diff is in `src/patches/project-modifications.patch`.

### 4. Download the traces
The 14 server traces are on Zenodo (record 13133243, DOI 10.5281/zenodo.13133242, 22.4 GiB in total).

```bash
chmod +x scripts/*.sh
scripts/download_traces_prefix.sh >> logs/download.log 2>&1
scripts/extend_prefix.sh dacapo-kafka 1610612736 nodeapp-nodeapp 1610612736
python3 scripts/trace_manifest.py          # records exactly which bytes were used
```

- To save time and disk, the first script fetches only the first 1 GiB of each trace (the whole file if it is smaller). That covers the 300 M instructions simulated (100 M warm-up + 200 M measured).
- Kafka and NodeApp need 1.5 GiB, which the second command fetches.
- The script is resumable. If a download stalls, run it again.
- To download the complete files instead, use the authors' script: `artifact/scripts/download_traces.sh`.

### 5. Run a single simulation (quick test)
```bash
artifact/build/predictor artifact/traces/merced.467915.champsim.trace.gz \
    --model llbpx-timing --simulate-btb -w 100000000 -n 200000000
```
Models: `tage64kscl`, `tage512kscl`, `llbp`, `llbp-timing`, `llbpx`, `llbpx-timing`, `llbpx-optw`, and the ablations `llbpx-timing-nodepth`, `llbpx-timing-norange`, `llbpx-nodepth`, `llbpx-norange`. Models ending in `-timing` model the pattern-store latency; the others use 0-cycle latency.

### 6. Run all experiments
```bash
scripts/run_experiments.sh -j 12          # 11 models x 14 traces = 154 runs
```
Useful options:
```bash
scripts/run_experiments.sh -m "tage64kscl llbp-timing llbpx-timing" -t "merced.467915"   # a subset
```
- `-j` sets parallel jobs, `-m` the models, `-t` the traces, `-w` and `-n` the warm-up and measured instruction counts.
- Output goes to `results/raw/<trace>/<model>.txt` and a run log to `logs/experiments.csv`.
- Finished runs are skipped, so you can stop and resume.
- Each run takes roughly 3 to 9 minutes and uses about 7 to 47 MB of memory, so 12 parallel jobs are fine on a normal laptop.

### 7. Parse the results and build the figures
```bash
python scripts/parse_results.py
python scripts/make_figures.py
python scripts/make_diagrams.py
python scripts/assemble_report.py
python scripts/build_report_pdf.py        # optional PDF
```

### 8. Reproduce the extension (deep-to-shallow reversion)
```bash
scripts/run_experiments.sh -m "llbpx-timing-revert" \
  -t "nodeapp-nodeapp dacapo-spring benchbase-tpcc benchbase-wikipedia dacapo-tomcat merced.467915 whiskey.426708"
python scripts/extension_analysis.py revert
```
The `revertDepth` switch is added by `src/patches/extension-revert.patch`; the code in this repository already includes it.

### 9. gem5 (optional)
Only a hello-world test was run with gem5, to check that the authors' LLBP-X model builds and runs. The full-system server setup used for the speedup figures is not part of the artifact. Steps and results: `docs/SETUP.md` section 6 and `logs/gem5_summary.md`.

---

## Expected results (14 workloads, 100 M warm-up + 200 M measured instructions)

| Predictor | Mean MPKI | MPKI reduction vs 64K TSL (ours) | Paper |
|---|---|---|---|
| 64K TSL | 2.916 | - | - |
| LLBP | 2.655 | 8.97 % | 8.8 % |
| LLBP-X | 2.564 | 12.06 % | 12.1 % |
| LLBP-X Opt-W | 2.546 | 12.70 % | 12.6 % |
| 512K TSL (ideal, 0-latency) | 2.114 | 27.52 % | 27.5 % |

Small differences from these numbers are possible if you use different trace prefixes, since the 11 non-Google traces are prefixes of the full files. The simulator itself is deterministic: the same trace bytes and the same model always give identical output.

## Notes and limitations
- **Wrapped traces:** Charlie and Whiskey contain fewer than 300 M instructions, so the official simulator repeats them. These runs are labelled `OK_FULL_TRACE_WRAPPED` in `all_results.csv`, and our 64K TSL MPKI for them matches the paper's Table I.
- **Trace status without downloads:** `parse_results.py` checks the local trace files to decide which traces are complete. If a trace is not on disk, it falls back to the record in `logs/trace_manifest.csv`, so Path A gives the same 14-workload results without downloading anything.
- **Not reproduced:** the paper's gem5 speedup study and a few other figures (see `docs/FINAL_CHECKLIST.md`).
- **Troubleshooting:** a `\r: command not found` error means a `.sh` file has Windows line endings. Fix it with `sed -i 's/\r$//' scripts/*.sh`.
