# Setup: Environment, Dependencies and Exact Commands

## 1. System used for this project (inspected before installing anything)

| Item | Value |
|---|---|
| OS | Ubuntu 24.04.4 LTS (VirtualBox VM), kernel 7.0.0-38-generic, x86-64 |
| CPU | 17 vCPUs |
| RAM | 10 GiB (+3 GiB swap); ~6 GiB available during runs |
| Free disk | 49 GiB on `/` at start |
| C++ compiler | g++ 13.3.0 (C++20 used by the artifact; supported) |
| CMake | 3.28.3 |
| Python | 3.12.3 (venv `.venv/` with pandas, numpy, matplotlib 3.11.x) |
| Boost | 1.83 `program_options` (system package, already installed) |
| gzip | system `gzip` (the simulator pipes traces through `gzip -dc`) |
| sudo | **not available**, so nothing was installed system-wide. SCons was pip-installed into the venv. GNU `parallel` is missing, so our driver uses a bash job pool instead. |
| PDF tooling | no pandoc/LaTeX; the report PDF is produced with Python (see §7) |

The artifact documentation asks for Ubuntu 20.04/22.04, GCC 9.4/11.4 and CMake ≥ 3.22. The newer toolchain here builds the simulator without errors (warnings only). CMake prints a deprecation warning for `cmake_minimum_required(VERSION 3.0.0)`, which is harmless.

## 2. Obtain the code

```bash
mkdir ACA-THEORY-PROJECT && cd ACA-THEORY-PROJECT
git clone https://github.com/dhschall/LLBP-X.git artifact      # upstream commit 68e1cae
# (this repository already contains artifact/ with our modifications applied;
#  the exact diff is src/patches/project-modifications.patch)
```

To recreate our modified artifact from a fresh upstream clone:
```bash
cd artifact && git checkout 68e1cae && git apply ../src/patches/project-modifications.patch
```

## 3. Dependencies

```bash
# System packages (documented by the artifact; already present on our VM)
sudo apt install -y cmake libboost-all-dev build-essential wget
# Python (project venv; no root needed)
python3 -m venv .venv
.venv/bin/pip install pandas numpy matplotlib scons
```

## 4. Build the simulator

```bash
cmake -S artifact -B artifact/build -DCMAKE_BUILD_TYPE=Release
cmake --build artifact/build -j 12
ls artifact/build/predictor            # the CBP-style branch-predictor simulator
artifact/build/predictor --help
```
We use `Release` (`-O3 -g`) rather than the README's `Debug` (`-g`). This is only an optimisation level; predictor behaviour is identical and verified (see `logs/validation.md`).

## 5. Benchmark traces

The 14 official server traces are on Zenodo, record **13133243** (DOI 10.5281/zenodo.13133242), 22.4 GiB in total. The official `artifact/scripts/download_traces.sh` fetches whole files with `wget`.

**Constraint we hit:** Zenodo delivered only ≈0.2–0.8 MB/s per connection, and connections regularly stalled at 0 B/s. A full download would have taken well over a day. The simulator consumes only the first 300M instructions (100M warm-up + 200M ROI), and traces compress to about 2.2–2.5 bytes/instruction. We therefore download the **first 1 GiB of each trace**, or the whole file when it is smaller (Charlie, Delta, Whiskey are fetched completely):

```bash
scripts/download_traces_prefix.sh        # resumable; 8 parallel HTTP range requests; aborts stalled
                        # connections (<20 KB/s for 25 s) and resumes; appends a chunk
                        # only when the server answered 206 Partial Content
```

How we ensure this is valid:
* The simulator reads traces sequentially through `gzip -dc`, so a prefix yields exactly the same instruction stream as the full file for as many instructions as it contains.
* If a trace ends early, the simulator prints `*** Reached end of trace. Repeating trace` and restarts it. `scripts/parse_results.py` flags any such run as `TRACE_WRAPPED`, and it would not count as a valid result. Every reported run was checked for this.
* Every prefix was fully decompressed before use to check that it is intact and long enough. Two 1 GiB prefixes held only ~280 M (Kafka) and ~276 M (NodeApp) instructions, so they were extended to 1.5 GiB (≈ 410–420 M instructions) **before** any simulation used them:
  ```bash
  scripts/extend_prefix.sh dacapo-kafka 1610612736 nodeapp-nodeapp 1610612736
  ```
* Complete files are verified against Zenodo's MD5 checksums (`logs/zenodo_checksums.txt`). For prefixes, `logs/trace_manifest.csv` records the byte count and SHA-256 of what we used.

The small test trace `nodeapp-nodeapp-small` (100 MB, MD5 `d9dd9a1b000eb9c7084ba74ce4f10983`, verified) was used for smoke and regression tests.

**Incident (documented for transparency):** an early version of our downloader left orphaned `curl` processes that appended to the same files as a later version, which corrupted four partial files (one grew beyond the real file size). All affected files were deleted and re-downloaded from scratch by a single writer. No simulation had used them.

## 6. gem5 (optional part of the artifact)

```bash
# Pinned commit from artifact/scripts/setup_gem5.sh
mkdir gem5 && cd gem5 && git init && git remote add origin https://github.com/gem5/gem5.git
git fetch --depth 1 origin 51759b538e1d1268acf3b3a09057be13b85a3c3e && git checkout FETCH_HEAD
cp -r ../artifact/gem5models/* src/cpu/pred/
git apply ../artifact/scripts/llbpx.patch
source ../.venv/bin/activate          # provides scons
# On a 10 GiB machine, -j 6 and -j 4 were OOM-killed on one huge generated file.
# What worked: build that object alone, then the rest with -j 3.
scons build/ARM/arch/arm/generated/inst-constrs-3.o --ignore-style -j 1
scons build/ARM/gem5.opt --ignore-style -j 3
cd ..
# Equivalent of artifact/scripts/run_all_gem5.sh with this repository's paths:
for m in TSL64k LLBP LLBPX; do
  ./gem5/build/ARM/gem5.opt --outdir=results/gem5/$m artifact/scripts/se-llbp.py --bp=$m > results/gem5/$m.log 2>&1
  awk '/.+mispredictDueToPredictor_0.+DirectCond/ {print "'$m'", $2}' results/gem5/$m/stats.txt
done
```
The artifact provides only an SE-mode *hello-world* for gem5 (it downloads `arm-hello64-static` from gem5-resources). The full-system server setup used for the paper's speedup figures is explicitly not included. Outcome: all three models ran the hello-world and reported 58 mispredictions each (`logs/gem5_summary.md`, `PERFORMANCE_ANALYSIS.md` §5).

## 7. Running the experiments

```bash
# Full evaluation: 11 models x 14 traces, 100M warm-up + 200M measured instructions
scripts/run_experiments.sh -j 12

# A subset, e.g. only the three main predictors on two traces
scripts/run_experiments.sh -m "tage64kscl llbp-timing llbpx-timing" -t "nodeapp-nodeapp dacapo-kafka"

# Small validation run (separate output directory)
RAW_DIR=results/validation_small LOG_FILE=logs/validation_small.csv \
  scripts/run_experiments.sh -w 10000000 -n 40000000 -t nodeapp-nodeapp-small
```
`scripts/run_when_downloaded.sh` is a convenience wrapper we used during the campaign: it starts all models for a trace as soon as the downloader logs it as `DONE`.

Each run writes `results/raw/<trace>/<model>.txt`, the simulator's full stdout statistics plus wall-time and max-RSS lines. Completed runs are skipped on re-invocation. A single run is simply:
```bash
artifact/build/predictor artifact/traces/nodeapp-nodeapp.champsim.trace.gz \
    --model llbpx-timing --simulate-btb -w 100000000 -n 200000000
```

## 8. Processing, graphs, report

```bash
.venv/bin/python scripts/parse_results.py      # -> results/processed/all_results.csv
.venv/bin/python scripts/make_figures.py       # -> results/graphs/*.png|pdf, results/tables/*
.venv/bin/python scripts/build_report_pdf.py   # -> REPORT/project_report.pdf
```

## 9. Resource usage observed
* Simulator peak RSS over the full runs: 7.4 MB (64K TSL), 19 MB (512K TSL), 38 MB (LLBP), 46.5 MB (LLBP-X).
* Wall time per 300 M-instruction run with 11–16 concurrent runs: ~3.2 min (TSL), ~5.6 min (LLBP), ~6.0 min (LLBP-X). That is roughly 0.8–1.6 M instructions/s. The 154 runs took ≈ 1.5 h of wall-clock time.
* gem5 ARM build: ~2 h total on this VM including two OOM restarts; `gem5.opt` is 1.09 GB. Each hello-world run takes 5–7 s and ~120 MB RSS.
