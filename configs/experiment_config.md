# Experiment configuration (all runs)

| Parameter | Value | Origin |
|---|---|---|
| Simulator | `artifact/build/predictor` (CBP-style trace-based BP simulator, Release `-O3`) | official artifact |
| Flags | `--simulate-btb` | official `scripts/eval_all.sh` |
| Warm-up | 100,000,000 instructions | official `eval_all.sh`, paper Sec. VI |
| Measurement (ROI) | 200,000,000 instructions | official `eval_all.sh`, paper Sec. VI |
| Opt-W tables | `traces/<trace>-bestWbCtx_patterns_ODH_t16x14k_CT14_D4_264.csv` via `--tableload` | official artifact |
| Traces | first min(1 GiB, file size) bytes of each Zenodo trace (record 13133243) | see SETUP.md |

Model -> paper name mapping (as in `artifact/analysis/mpki.ipynb`):

| model id | label | description |
|---|---|---|
| tage64kscl | 64K TSL | baseline |
| tage512kscl | 512K TSL | ideal 0-latency, ~same storage as LLBP |
| llbp-timing | LLBP | Fig. 12 "LLBP" |
| llbpx-timing | LLBP-X | Fig. 12 "LLBP-X" |
| llbpx-optw | LLBP-X Opt-W | Fig. 12 "LLBP-X Opt. W" |
| llbp / llbpx | LLBP-0Lat / LLBP-X-0Lat | no prefetch latency |
| llbpx-timing-nodepth / -norange | ablations | [PROJECT-MOD] |
| llbpx-nodepth / -norange | 0-latency ablations | [PROJECT-MOD] |
