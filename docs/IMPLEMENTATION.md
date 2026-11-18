# Implementation and Integration of the Three Predictors

This document explains where each predictor's code comes from, what the project team changed, and how all predictors are evaluated under identical conditions.

## 1. Provenance at a glance

| Item | Origin | Location |
|---|---|---|
| CBP-style trace-driven simulator (`main.cc`, trace readers, BTB model) | **Original authors** (LLBP-X artifact, MIT) | `artifact/main.cc`, `artifact/utils/`, `artifact/btb/` |
| TAGE-SC-L 64 KB / 512 KB | **Original authors**, based on Seznec's CBP-5 TAGE-SC-L | `artifact/bpmodels/tage/` |
| Original LLBP | **Original authors** (from the MICRO'24 LLBP artifact) | `artifact/bpmodels/llbp/` |
| LLBP-X (+ timing, + Opt-W) | **Original authors** | `artifact/bpmodels/llbpx/` |
| gem5 models of LLBP / LLBP-X + gem5 patch | **Original authors** | `artifact/gem5models/`, `artifact/scripts/llbpx.patch` |
| Opt-W per-context best-W tables | **Original authors** (generated offline, shipped as CSV) | `artifact/traces/*-bestWbCtx_*.csv` |
| ROI accuracy output (7 lines) | **Modification by project team** | `artifact/main.cc` |
| LLBP-X ablation switches `depthAdaptation`, `histRangeSel` and 4 ablation models | **Modification by project team** | `artifact/bpmodels/llbpx/llbpx.{h,cc}`, `artifact/bpmodels/base_predictor.cc` |
| Experiment driver, parser, figure/table generator, PDF builder, trace downloader | **New code by project team** | `scripts/` |
| All documentation and the report | **New, by project team** | `*.md`, `REPORT/` |

The upstream artifact is vendored unchanged except for the files listed as modified. The complete diff against upstream commit `68e1cae` is `src/patches/project-modifications.patch` (90 lines added, 3 changed, 4 files). Every modified hunk carries a `[PROJECT-MOD]` comment.

**Design decision:** the official implementations of all three predictors already exist and are correct by construction (they are the authors' own models). We therefore **reused them as-is** and did not re-implement anything. Rewriting LLBP-X would only add risk.

## 2. The three predictors in the artifact

All models are created in `artifact/bpmodels/base_predictor.cc::CreateBP()` by name:

| CLI name | C++ class | Description |
|---|---|---|
| `tage64kscl` | `LLBP::TageSCL64k` | **A. TAGE-SC-L 64 KB** (primary baseline): 21 tagged tables, 6–3000-bit histories, SC and loop predictor. |
| `tage512kscl` | `LLBP::TageSCL512k` | 512 KB TAGE-SC-L (8× entries per table), idealised with 0 access latency. Serves as the upper bound. |
| `llbp` / `llbp-timing` | `LLBPTageSCL64k` / `…Timing` | **B. Original LLBP** on top of the 64K TSL. `-timing` models the pattern-store access delay via the prefetch queue. |
| `llbpx` / `llbpx-timing` | `LLBPXTSCL64k` / `…Timing` | **C. LLBP-X**, same base TSL. |
| `llbpx-optw` | `LLBPXTSCL64kTimingOptW` | LLBP-X with each context's offline-optimal W loaded from `--tableload` (paper "Opt-W"), timing on. |

### 2.1 TAGE-SC-L (`bpmodels/tage/tage.cc`, `tage_scl.cc`)
* A `TageBase` class with `Tage64kConfig` (`nhist=36` logical tables, of which 21 are used, `LogG=10`, `minhist=6`, `maxhist=3000`), plus `TageSCL` adding the statistical corrector and loop predictor. Total ≈ 64 KB.
* `TageSCL512k` uses `LogG=13` (8× entries).

### 2.2 Original LLBP (`bpmodels/llbp/llbp.{h,cc}`), subclass of `TageSCL`
* **RCR:** `T=3` (unconditional branches), `W=8`, `D=4`, `S=1`. The CCID hashes UBs D…D+W, and the PCID hashes the most recent W.
* **LLBPStorage (CD+PS):** `BaseCache<uint64_t, Context>`, 14336 contexts, 7-way. Each `Context` owns a 16-entry, 4-way `PatternSet`.
* **History filter:** `FILTER_TABLES` limits LLBP to TAGE indices `{6,10,13,14,15,16,17,18,19,20,22,24,26,28,32,36}`, four per bucket.
* **Arbitration:** `chooseProvider()` uses LLBP when its matching history is ≥ TAGE's. `OVERWRITE_SCL` suppresses SC when LLBP provides.
* **Timing:** `prefetch()`, `tickPrefetchQueue()`, `installInPB()`. A pattern set must be in the 64-entry PB to be used, and it arrives `accessDelay` ticks after the prefetch.

### 2.3 LLBP-X (`bpmodels/llbpx/llbpx.{h,cc}`), subclass of `TageSCL`
Compile-time features enabled upstream: `FILTER_TABLES_HLEN_16`, `ADAPTIVE_W_CTX`, `ADAPTIVE_W_BY_CONF`, `ADAPTIVE_W_REALISTIC`, `USE_BESTW_CTX`.

| Paper concept | Code |
|---|---|
| Two context depths W=2 / W=64 | `const int WS[nW] = {2,64}`; per-context depth index `wi` |
| CID₂ / CID₆₄ computed in parallel | `RCR::getCCID(pc, w)`, `RCR::getPCID(w)`, `RCR::getBaseCtx()` (16-bit W=2 base context) |
| Context Tracking Table, 6K entries, 6-way | `CtxInfoTable cit(CitSize=6*1024, CitAssoc=6)` holding `ContextInfo{wi, fullPatternSets, allocVsDrop}` |
| Overflow signal at 7 confident patterns | `llbpUpdate`: when `confidentPtrns == adaptThreshold (7)`, `cit.insert(baseCtx)` and `fullPatternSets++` |
| avg-hist-len counter, H_th = 232 | `llbpAllocate`: `allocVsDrop` ±1 depending on `histLen < histLenThreshold (22)` (TAGE index 22 = 232 bits). When `> 7`, `wi` switches 0→1. The 1→0 branch is unreachable because of the guard `ci->wi < nW-1`; deep contexts revert only on CTT eviction. |
| History range selection | `fltTables[0]` = TAGE indices ≤22 (6–232 bits), `fltTables[1]` = indices ≥12 (37–3000 bits). Out-of-range allocations are dropped. |
| PB / prefetch | Same mechanism as LLBP, with `accessDelay = 4` ticks in `LLBPXConfig` |
| Opt-W | `LoadTables()` fills `baseContexts[ctx].wi` from the CSV; `optW` disables the CTT |

**Note on the timing parameter:** `LLBPConfig.accessDelay = 5` and `LLBPXConfig.accessDelay = 4` in the artifact. The paper states "6 cycles access latency for LLBP". We kept the authors' values. This is a property of the official artifact, which we did not "fix".

## 3. Modifications by the project team

### 3.1 Accuracy output (`main.cc`)
The upstream simulator prints ROI instructions, mispredictions and MPKI, but not the ROI conditional-branch count needed for *accuracy*. We added:
```
ROI COND BRANCHES  : <total_stats.numCond - warmup_stats.numCond>
ROI ACCURACY       : 1 - ROI_MISPREDICTIONS / ROI_COND_BRANCHES
```
This is output only; simulated behaviour is unchanged.

### 3.2 Ablation switches for the optimization breakdown (paper §VII-E)
The paper attributes 82 % of LLBP-X's gain to depth adaptation and 18 % to history range selection, but omits the graph, and the artifact has no way to reproduce it. We added two runtime fields to `LLBPXConfig` (both default `true`, which is the upstream behaviour):

* **`depthAdaptation = false`:** the `allocVsDrop > 7` transition is never taken, so every context stays at W=2 (`wi=0`). Everything else is unchanged, including the CTT, the overflow trigger and the shallow-range filter. The model therefore equals LLBP-X with **only history range selection** (all contexts using the 6–232-bit range).
* **`histRangeSel = false`:** both `fltTables[0]` and `fltTables[1]` are rebuilt from the **original LLBP 16-length set** (the same list as `FILTER_TABLES` in `llbp.cc`, four per bucket). The range-drop rule is replaced by "drop if not in that set". Depth adaptation still works. The model therefore equals LLBP-X with **only dynamic context depth adaptation**.

| New CLI name | timing | depthAdaptation | histRangeSel |
|---|---|---|---|
| `llbpx-timing-nodepth` | yes | off | on |
| `llbpx-timing-norange` | yes | on | off |
| `llbpx-nodepth` | no | off | on |
| `llbpx-norange` | no | on | off |

Implemented as `template<bool Timing, bool Depth, bool Range> class LLBPXAblation` in `llbpx.h`.

**Caveats (stated honestly):**
* For contexts not tracked in the CTT (`ci == nullptr`), upstream LLBP-X applies no history filter at all. We leave that path untouched in both ablations so that the only difference is the switched mechanism.
* The paper does not describe exactly how its breakdown was computed. Our attribution is incremental in the order LLBP → +depth adaptation (`no-range`) → +range selection (full LLBP-X). Because the mechanisms interact, other orderings give other shares. Both single-mechanism results are reported.
* Note that LLBP → `no-range` differs from LLBP in more than depth adaptation alone (e.g. W=2 default instead of W=8, CTT, SC not suppressed). The ablation therefore measures "LLBP-X without range selection", not "LLBP + depth adaptation" in isolation.

**Regression check:** with default switches, the modified binary reproduces the pre-modification output bit-for-bit on the small test trace (64K TSL 2.6999, LLBP 2.3567, LLBP-X 2.3163 ROI MPKI for 5M+10M instructions; see `logs/validation.md`).

## 4. Equivalent evaluation conditions

All predictors run:
* from the **same binary** (`artifact/build/predictor`, CMake Release, `-O3 -g`, GCC 13.3),
* on the **same trace bytes**,
* with the same flags `--simulate-btb -w 100000000 -n 200000000` (from the official `eval_all.sh`),
* and with the same base predictor: all LLBP variants wrap the identical `Tage64kConfig` TSL with SC and loop predictor.

Opt-W additionally loads its official per-trace table. The driver records every run's wall time, max RSS and exit code in `logs/experiments.csv`.

## 5. gem5 integration

The artifact's gem5 models (`gem5models/llbp.{cc,hh}`, `cache.h`) and `scripts/llbpx.patch` were applied unchanged to gem5 commit `51759b5` (the commit pinned by `scripts/setup_gem5.sh`), and `build/ARM/gem5.opt` was built. See `SETUP.md` §6 and `PERFORMANCE_ANALYSIS.md` for the outcome. The server workloads' full-system setup is not part of the artifact, so gem5 was used only for the functional SE-mode check that the artifact provides.
