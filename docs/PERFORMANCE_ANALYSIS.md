# Performance Analysis

All numbers below come from `results/processed/all_results.csv` (154 runs: 11 configurations × 14 traces, 100 M warm-up + 200 M measured instructions, `--simulate-btb`) and from the tables generated from it in `results/tables/`. Paper values are quoted from the paper text (`configs/paper_*.csv`).

**Label convention.** "LLBP" and "LLBP-X" are the latency-modelled models (`llbp-timing`, `llbpx-timing`), which correspond to the paper's Fig. 12 (as in the official notebook). The "-0Lat" models do not model the pattern-store latency.

**Improvement formula** (used throughout):

$$\text{MPKI improvement (\%)} = \frac{\text{MPKI}_{\text{baseline}} - \text{MPKI}_{\text{LLBP-X}}}{\text{MPKI}_{\text{baseline}}}\times 100$$

**Worked example (Spring, LLBP-X vs LLBP):** (3.256 − 2.844) / 3.256 × 100 = 12.65 %. The table value, computed from unrounded MPKI, is 12.65 %.

**Two aggregates** are reported. **Mean** is the improvement of the arithmetic-mean MPKI over the 14 workloads; the official notebook uses this. **AvgRed** is the arithmetic mean of the 14 per-workload improvements.

---

## 1. Headline results

*Table A. Mean over 14 workloads (from `table_mpki_all_predictors.csv`, `table_accuracy_all_predictors.csv`, `table_mpki_reduction_vs_64k_tsl.csv`).*

| Predictor | Mean MPKI | Mean accuracy (%) | Total ROI mispredictions | MPKI reduction vs 64K TSL: Mean / AvgRed (%) | Paper (avg, %) |
|---|---|---|---|---|---|
| 64K TSL | 2.916 | 98.086 | 8,165,225 | – | – |
| LLBP | 2.655 | 98.258 | 7,433,058 | 8.97 / 7.93 | 8.8 |
| **LLBP-X** | **2.564** | **98.316** | **7,180,407** | **12.06 / 11.20** | **12.1** |
| LLBP-X Opt-W | 2.546 | 98.328 | 7,127,906 | 12.70 / 11.60 | 12.6 |
| 512K TSL (ideal) | 2.114 | 98.612 | 5,917,809 | 27.52 / 27.13 | 27.5 |
| LLBP-0Lat | 2.610 | 98.288 | 7,307,650 | 10.50 / 9.51 | – |
| LLBP-X-0Lat | 2.525 | 98.341 | 7,070,554 | 13.41 / 12.60 | – |

Mean-MPKI calculation for LLBP-X: (2.9162 − 2.5644) / 2.9162 × 100 = 12.06 %.

## 2. Answers to the analysis questions

### Q1. Which predictor achieves the highest accuracy?
The **idealised 512K TSL** is the most accurate (98.61 % mean; best on all 14 workloads), but it cannot be built with single-cycle latency. Among realisable designs, **LLBP-X Opt-W** (98.33 %) and **LLBP-X** (98.32 %) lead, followed by LLBP (98.26 %) and 64K TSL (98.09 %). Accuracy differences look small in absolute terms because more than 98 % of conditional branches are easy. The relevant quantity is the misprediction count: LLBP-X removes 984,818 more ROI mispredictions than 64K TSL, and 252,651 more than LLBP.

### Q2. Which predictor has the lowest MPKI?
512K TSL (2.114). Among realisable predictors: LLBP-X Opt-W (2.546), then LLBP-X (2.564). LLBP-X has a lower MPKI than LLBP on **all 14 workloads** and a lower MPKI than 64K TSL on all 14.

### Q3. How much does LLBP-X improve over original LLBP?
*Table B. LLBP-X vs LLBP (`table_llbpx_vs_llbp.csv`).*

| | Ours | Paper |
|---|---|---|
| Per-workload range | 0.78 % (Whiskey) – 12.65 % (Spring) | 0.8 % – 11.5 % |
| Average (AvgRed) | **3.57 %** | **3.6 %** |
| Mean-MPKI improvement | 3.40 % | – |
| Median / std. dev. | 2.86 % / 2.89 pp | – |
| Relative growth of the TSL-relative gain | (12.06 / 8.97) − 1 = 34.5 % (Mean basis); 41.2 % (AvgRed basis) | "36 % average improvement over the original design" |

LLBP-X closes 43.8 % of the 64K→512K TSL gap, against 32.6 % for LLBP (Mean basis).

### Q4. How does LLBP-X compare with TAGE-SC-L?
Compared with the 64K TSL baseline, LLBP-X reduces MPKI by **1.36 % (Delta) to 26.92 % (NodeApp)**, with a mean of 12.06 %. The paper reports 1.4–27 % (avg. 12.1 %); our range and average agree to within 0.1 pp. Compared with the idealised 512K TSL, LLBP-X still leaves most of the opportunity unused: 512K TSL achieves 27.52 % (12.34–46.13 %). On every workload, 512K TSL achieves a larger reduction than LLBP-X, by a factor of 1.7× (NodeApp) to 9.3× (Delta). This matches the paper's statement that "a substantial gap remains".

### Q5. Which workloads benefit most?
* **Over LLBP:** Spring (+12.65 %), Chirper (+5.15 %), Kafka (+4.41 %), TPCC (+4.23 %), Wikipedia (+4.07 %).
* **Over 64K TSL:** NodeApp (26.92 %), Spring (20.58 %), Merced (17.91 %), TPCC (14.65 %), Kafka (13.56 %).

Spring stands out. LLBP gains only 9.1 % over TSL there, while the ideal 512K TSL gains 40.8 %, which points to a large capacity problem that a fixed W=8 cannot address. The ablation (§3) shows that almost all of Spring's improvement comes from **depth adaptation** (13.4 % on its own). That is consistent with the paper's explanation that H2P branches overflow their pattern sets.

### Q6. Which workloads show limited improvement or regressions?
* Improvement over LLBP is limited on **Whiskey (0.78 %)**, **PHPWiki (1.53 %)**, **Delta (1.74 %)** and **Charlie (1.98 %)**. Three of these are Google traces with large, flat branch working sets.
* **Delta:** LLBP is slightly *worse* than 64K TSL (−0.38 %). Delta and Whiskey also have the smallest 512K-TSL headroom of all workloads (12.7 % and 12.3 %).
* **No regression of LLBP-X vs LLBP** occurs with latency modelled. In the 0-latency configuration, LLBP-X-0Lat is **2.23 % worse** than LLBP-0Lat on PHPWiki (2.617 vs 2.560 MPKI). This is the only case where the "X" design loses to its predecessor.
* **Opt-W vs LLBP-X:** the oracle W is *not* always best. LLBP-X beats Opt-W on Chirper (the paper reports this too), HTTP, PHPWiki and Wikipedia. On PHPWiki, Opt-W is even worse than LLBP (8.30 % vs 10.00 % over TSL). Opt-W fixes W per context offline and cannot follow phase changes; the paper gives the same explanation for Chirper.

### Q7. Are the improvements consistent?
They are consistent in **sign** (14/14 improve over LLBP and over TSL with latency modelled), but not in **magnitude**. The per-workload improvement over LLBP has a standard deviation of 2.89 pp around a median of 2.86 %, and a single workload (Spring) contributes a disproportionate share of the average. Without Spring, AvgRed over LLBP would be 2.87 % ((50.01 − 12.65) / 13, from the per-workload values in `table_llbpx_vs_llbp.csv`). The gain over LLBP correlates moderately with the 512K-TSL headroom of a workload (Pearson r = 0.50). Workloads with more capacity-bound mispredictions benefit more.

### Q8. What explains the differences?
* **Capacity pressure from H2P branches** (workloads with large 512K-TSL headroom: NodeApp, Spring, Merced, TPCC). Depth adaptation spreads their patterns over W=64 contexts and recovers capacity that LLBP loses to overflowing sets.
* **Duplication and training time.** Default W=2 contexts merge patterns that LLBP (W=8) replicates. This helps workloads with many short-history patterns; see the range-only ablation below, which is shallow-only.
* **Flat branch working sets** (Google traces Whiskey, Delta, Charlie). The ideal 512K TSL gains comparatively little there (12–21 %), so there is little capacity headroom for any second-level design to recover.
* **Prefetch latency** costs LLBP 1.81 % and LLBP-X 1.67 % MPKI on average (timing vs 0-latency, AvgRed). LLBP-X is slightly *less* sensitive to latency.

### Q9. Contribution of dynamic context depth adaptation (supported by our ablation)
*Table C. Ablation, latency modelled (`table_ablation_breakdown.csv`, Mean rows).*

| Configuration | Mean MPKI | Reduction vs LLBP (Mean basis) |
|---|---|---|
| LLBP | 2.655 | – |
| LLBP-X, range selection only (depth adaptation off) | 2.618 | 1.37 % |
| LLBP-X, depth adaptation only (range selection off) | 2.577 | 2.94 % |
| **Full LLBP-X** | **2.564** | **3.40 %** |

With incremental attribution in the order LLBP → +depth adaptation → +range selection, **depth adaptation contributes 86.4 %** of the LLBP→LLBP-X MPKI gain (on mean MPKI): (2.6547 − 2.5767) / (2.6547 − 2.5644). With 0-latency models the share is 77.1 %. **The paper reports 82 %.** Depth adaptation is clearly the dominant mechanism. It is decisive on Spring (13.4 % alone) and NodeApp, where turning it off makes LLBP-X *worse* than LLBP (−2.36 %).

### Q10. Contribution of dynamic history range selection
On the same basis, range selection contributes **13.6 %** with latency modelled (22.9 % at 0 latency); **the paper reports 18 %.** Its effect is workload-dependent:
* Adding range selection on top of depth adaptation helps 12 of 14 workloads (depth-only is worse than full LLBP-X except on NodeApp and Spring).
* The *range-only* configuration (no depth adaptation, i.e. all contexts W=2 with short histories) beats full LLBP-X on **Charlie, Delta, Kafka, Merced and Whiskey**, mostly Google traces. For those workloads the cost of switching contexts to W=64 (retraining) outweighs the capacity gain.

*Caveat:* the paper does not specify how its breakdown was computed. Because the mechanisms interact, a different attribution order gives different shares; with range selection added first, it would get 40 % (1.37 / 3.40). Our ablation switches are additions to the official model (see `IMPLEMENTATION.md` §3.2). We report this as **partially reproduced**: the same ranking and similar shares, but an unknown original methodology.

### Q11. Trade-offs
* **Storage:** +9.36 KB (+1.8 %) over LLBP (paper), mostly the CTT.
* **Simulator-measured memory and time** (not hardware costs): peak RSS 46.5 MB for LLBP-X vs 38.2 MB for LLBP; mean simulation time 6.0 vs 5.6 min per 300 M-instruction run.
* **Transfer bandwidth** (trace-based estimate of Fig. 15a, `table_bandwidth_bits_per_instr.csv`): LLBP-X moves **9.69 bits/instr** between pattern store and buffer, against **10.05** for LLBP (−3.6 %). Reads are 80 % of traffic. The paper's gem5 figures are 9.9 vs 10.6 (−6.1 %), and the paper also finds reads dominate (writes ≈ 1/5). LLBP-X is not uniformly cheaper: on Chirper (+11 %), HTTP (+7 %) and Delta (+22 %) it moves more data than LLBP. Opt-W needs the least (8.29).
* **Energy:** not measurable here. The paper estimates +1.5 % vs LLBP, because the CTT's energy outweighs the read savings.
* **Complexity:** an extra set-associative table, a 64-branch-deep RCR with two rolling hashes, an 8-way history mux, and a CTT access per unconditional branch, all off the critical path.

### Q12. Limitations of the technique
1. **Large remaining gap to TAGE at equal storage**: LLBP-X recovers only 43.8 % of the 512K-TSL opportunity.
2. **Switching cost**: patterns are lost when a context changes depth, which is why only two depths are used and why range-only (shallow-only) beats LLBP-X on five workloads.
3. **Heuristic thresholds** (T<sub>max</sub> = 7, H<sub>th</sub> = 232, CTT size) were tuned on these same 14 workloads; the paper reports Spring and Merced preferring other H<sub>th</sub> values.
4. **Uneven gains**: much of the average improvement comes from a few H2P-heavy workloads.
5. **Artifact behaviour vs paper description**: deep contexts revert to W=2 only on CTT eviction; the counter-based reversion branch is unreachable (`IMPLEMENTATION.md` §2.3).
6. **Modest performance impact**: the paper's gem5 speedup is 1.0 % (vs 0.71 % for LLBP).

## 3. Reproduction status of paper results

| Paper result | Our result | Status | Notes |
|---|---|---|---|
| Table I: 64K TSL MPKI per workload | All 14 within ±0.005 MPKI (max 0.63 % relative), mean 2.916 vs 2.916 | **Successfully reproduced** | `table1_reproduction_64k_tsl.md` |
| Fig. 12: LLBP-X reduction vs 64K TSL, 1.4–27 % (12.1 %) | 1.36–26.92 % (12.06 %) | **Successfully reproduced** | Per-workload bar heights cannot be compared exactly because the paper gives no numeric table |
| Fig. 12: Opt-W 1.7–28.4 % (12.6 %) | 1.93–28.26 % (12.70 %) | **Successfully reproduced** | |
| Fig. 12: 512K TSL 12.7–46.1 % (27.5 %) | 12.34–46.13 % (27.52 %) | **Successfully reproduced** | Minimum (Whiskey) is 0.36 pp lower |
| Fig. 4 / §II-C.5: LLBP 0.6–25 % (8.8 %) | −0.38–25.03 % (8.97 %) | **Partially reproduced** | Average matches; on Delta, LLBP is slightly worse than TSL in the artifact |
| LLBP-X over LLBP 0.8–11.5 % (avg 3.6 %) | 0.78–12.65 % (avg 3.57 %) | **Successfully reproduced** | Maximum (Spring) is 1.2 pp higher |
| LLBP-X within 97 % of Opt-W | 94.9 % (Mean basis), 96.6 % (AvgRed basis) | **Partially reproduced** | |
| LLBP-X surpasses Opt-W on Chirper | Yes (also HTTP, PHPWiki, Wikipedia) | **Successfully reproduced** | |
| §VII-E: 82 % depth / 18 % range | 86 % / 14 % (timing), 77 % / 23 % (0-lat) | **Partially reproduced** | Required our ablation switches; attribution method not given in paper |
| Fig. 15a: bandwidth 10.6 → 9.9 bits/instr | 10.05 → 9.69 bits/instr (trace-based) | **Partially reproduced** | No wrong-path prefetches in the trace model |
| Fig. 1, Figs. 5–9 (hardware counters, limit study, NodeApp characterisation) | – | **Not reproducible with the artifact** | Requires Intel servers / unconstrained-model variants not exposed in the artifact |
| Fig. 13, 14 (gem5 speedup, prefetch timeliness, false path, overriding) | – | **Not reproducible with the artifact** | The full-system server setup is not provided; the trace simulator has no pipeline (no IPC) |
| Fig. 15b (energy, CACTI) | – | **Not reproducible with the artifact** | CACTI models not included |
| Fig. 16, §VII-F sensitivity (H<sub>th</sub>, CTT size, PS size, TSL size) | – | **Not attempted** | Possible in principle by editing `LLBPXConfig`; not scripted; left as future work |

**Why the reproduction is this close:** the paper's Table I numbers match the official CBP-style simulator to within rounding. That includes Charlie and Whiskey, where the complete official trace is shorter than 300 M instructions and the simulator repeats it. This strongly suggests that the paper's accuracy results were produced with essentially this simulator and these settings, despite the README's caution that the paper used a ChampSim integration.

## 4. IPC / overall performance

The trace-based simulator models only the branch predictor and BTB, so **IPC is not available**. The paper's IPC results (Fig. 13) come from gem5 full-system simulation of the ten non-Google workloads, whose disk images and checkpoints are not part of the artifact. As a proxy for overall performance we report mean MPKI (`fig_overall_mean_mpki`). Section 5 describes what was achieved with gem5.

## 5. gem5

gem5 was built with the official LLBP/LLBP-X gem5 models (gem5 commit 51759b5 + `artifact/scripts/llbpx.patch`) and the artifact's SE-mode hello-world test was run for TSL64k, LLBP and LLBP-X: all three completed, printed "Hello world!", and reported 58 conditional-branch mispredictions on 5,208 instructions (artifact README: "around 56"); this verifies the integration but is far too short to measure accuracy or IPC differences.

| gem5 model | Branch predictor SimObject(s) | Instructions | DirectCond lookups | Mispredictions (DirectCond) | IPC | Wall time |
|---|---|---|---|---|---|---|
| TSL64k | TAGE_SC_L_64KB | 5,208 | 2,003 | 58 | 0.1364 | 6.5 s |
| LLBP | LLBP (adaptCtxDepth=false, CIT 64×4) | 5,208 | 2,003 | 58 | 0.1364 | 4.6 s |
| LLBPX | LLBP (adaptCtxDepth=true, CIT 6144×6, 3-bit ctx counters) | 5,208 | 2,003 | 58 | 0.1364 | 4.5 s |

Build notes: the ARM build was OOM-killed twice on the 10 GiB VM (`arch/arm/generated/inst-constrs-3.o` needs ≈4 GB at `-O3 -g`); it succeeded after compiling that object alone (`-j 1`) and the rest with `-j 3` (see `logs/gem5_build.log`). Outputs: `results/gem5/<model>/{stats.txt,config.ini}` and `results/gem5/<model>.log`.


**Why no gem5 IPC comparison on the server workloads:** the paper's speedup study needs full-system disk images, kernels and checkpoints for the ten server applications, which the artifact explicitly does not provide ("we do not provide the full system setup used in our evaluation"). Building that environment, i.e. booting Ubuntu 20.04 in gem5 FS mode, installing and warming each server stack, and running 200 M + 300 M instructions per configuration with a detailed O3 core, was not feasible on a 17-vCPU / 10 GiB VM within this project. The four Google traces cannot be run in gem5 at all (paper §VI). Fig. 13/14 are therefore classified as **not reproducible with the available artifact**.
