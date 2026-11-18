# Final Checklist

Status legend: **COMPLETED**, **PARTIALLY COMPLETED**, **NOT COMPLETED**. Automated consistency checks: `scripts/validate_project.py` → `logs/validation_final.md` (**77/77 passed**).

## 1. Main objectives

| # | Requirement | Status | Evidence / explanation |
|---|---|---|---|
| 1 | Understand the paper | COMPLETED | `PAPER_ANALYSIS.md`. The paper was not in the working directory, so it was downloaded from the authors' lab page (`docs/paper/`). |
| 2 | Inspect the official implementation | COMPLETED | Every paper concept mapped to code (`IMPLEMENTATION.md` §2). Found one paper/code discrepancy (unreachable deep→shallow reversion). |
| 3 | Set up simulator, compiler, dependencies, traces | COMPLETED | `SETUP.md`. All 14 official traces obtained (3 complete with MD5 verified; 11 verified prefixes of ≥300 M instructions). |
| 4 | Implement / integrate LLBP-X correctly | COMPLETED | Official LLBP-X reused unchanged. Our additions are output-only plus ablation switches whose defaults are bit-identical to upstream (`logs/validation.md`). |
| 5 | Compare against TAGE-SC-L and LLBP | COMPLETED | 11 configurations × 14 traces. |
| 6 | Run experiments on available traces | COMPLETED | 154/154 runs valid (`logs/experiments.csv`, `results/raw/`). |
| 7 | Reproduce paper graphs/tables | PARTIALLY COMPLETED | Table I and Fig. 12 reproduced; §VII-E breakdown and Fig. 15a partially reproduced; Figs. 1, 5–9, 13, 14, 15b and 16 not reproducible or not attempted (see §3 below). |
| 8 | Additional graphs/tables | COMPLETED | 10 data figures (PNG + PDF) + 3 schematic diagrams; 10 CSV tables (7 also as Markdown). |
| 9 | Analyse results | COMPLETED | `PERFORMANCE_ANALYSIS.md` answers all 12 questions. |
| 10 | Clean, reproducible repository | COMPLETED | Git repository with `.gitignore` (traces, venv, gem5 and builds excluded), pushed to <https://github.com/vishalisharm/ACA-THEORY-PROJECT> (public). |
| 11 | Academic report | COMPLETED | `REPORT/project_report.md` (~7.5 k words, all 22 required sections plus appendices). |
| 12 | Report as Markdown and PDF | COMPLETED | `REPORT/project_report.pdf` (23 pages, generated with WeasyPrint). |
| 13 | Verify the project | COMPLETED | §2 below. |

## 2. Validation items (Section 11 of the task)

| Check | Status | How verified |
|---|---|---|
| Source code compiles | COMPLETED | Fresh CMake configure and build in an empty directory using the README commands; also upstream `68e1cae` built separately for the regression test. |
| Predictor implementations accessible | COMPLETED | All 11 model names run (`base_predictor.cc`); validated by the script. |
| Scripts execute correctly | COMPLETED | `run_experiments.sh`, `parse_results.py`, `make_figures.py`, `make_diagrams.py`, `assemble_report.py`, `build_report_pdf.py`, `trace_manifest.py` and `validate_project.py` were all run end to end. |
| Experiment commands work | COMPLETED | 154 runs with exit code 0; README single-run command matches the driver's. |
| Result files exist | COMPLETED | 154 raw files; checked by script. |
| CSV values valid | COMPLETED | No missing values; MPKI and accuracy recomputed from counts (assertions in parser and validator); identical ROI length and conditional-branch count for every model of a workload. |
| Graphs generated from CSV | COMPLETED | `make_figures.py` reads only `all_results.csv` (plus labelled paper reference values). |
| Graph values match data | COMPLETED | Figures and tables are produced by the same code from the same DataFrame; figures were visually inspected. |
| Percentage calculations correct | COMPLETED | Validator recomputes every reduction column from MPKI (max diff < 1e-3); worked example in `PERFORMANCE_ANALYSIS.md`. |
| Report values match result tables | COMPLETED | Report tables are generated from CSVs by `assemble_report.py`; the validator checks headline numbers in README, analysis and report. |
| All report figures and tables exist | COMPLETED | Validator checks every image reference. |
| README instructions correct | COMPLETED | Build, run, parse, plot and PDF commands executed as written. The clone URL points at the hosted repository. |
| No fabricated or unsupported claims | COMPLETED | Paper numbers are always labelled as such; every unreproduced item is labelled. |
| Determinism | COMPLETED | Re-run of `llbpx-timing` on Delta with a freshly built binary gives identical ROI mispredictions (`logs/determinism_check.txt`). |
| Repository structure clean | COMPLETED | See README §11. |

## 3. Reproduction classification

| Paper item | Classification |
|---|---|
| Table I (64K TSL MPKI) | Successfully reproduced (±0.005 MPKI) |
| Fig. 12 (LLBP-X, Opt-W, 512K TSL reductions) | Successfully reproduced (averages within 0.1 pp) |
| LLBP-X over LLBP (0.8–11.5 %, avg 3.6 %) | Successfully reproduced (0.78–12.65 %, avg 3.57 %) |
| LLBP vs 64K TSL (0.6–25 %, 8.8 %) | Partially reproduced (avg 8.97 %; min −0.38 % on Delta) |
| Opt-W efficiency (97 %) | Partially reproduced (94.9–96.6 %) |
| §VII-E breakdown (82 % / 18 %) | Partially reproduced via our ablation (86 % / 14 %) |
| Fig. 15a bandwidth | Partially reproduced (trace-based estimate, −3.6 % vs −6.1 %) |
| Figs. 1, 5–9 | Not reproducible with the available artifact |
| Figs. 13, 14 (gem5 speedup etc.) | Not reproducible with the available artifact (no full-system setup) |
| Fig. 15b (energy) | Not reproducible with the available artifact (no CACTI models) |
| Fig. 16, §VII-F sensitivity | Not attempted (time) |

## 4. Incomplete items, explained

| Item | Status | Reason |
|---|---|---|
| IPC / speedup comparison | NOT COMPLETED | The trace simulator has no pipeline model. The paper's gem5 full-system server images are not in the artifact; building them was infeasible on a 10 GiB, 17-vCPU VM. gem5 itself *was* built and the artifact's hello-world test passed for all three predictors (IPC 0.136, 58 mispredictions each), which validates the integration only. |
| Full-length traces | PARTIALLY COMPLETED | Zenodo throughput (~0.2–0.8 MB/s per connection, frequent stalls) made 22 GiB impractical. We used verified prefixes containing ≥300 M instructions, enough for the official 100 M + 200 M window, so the results are unaffected. |
| Sensitivity studies (Fig. 16, §VII-F) | NOT COMPLETED | Not part of the official scripts; omitted for time. Listed as future work. |
| Energy estimate | NOT COMPLETED | Requires CACTI 7 models that are not provided. |
| Remote GitHub publication | COMPLETED | Pushed to the public repository <https://github.com/vishalisharm/ACA-THEORY-PROJECT> (branch `main`). |
