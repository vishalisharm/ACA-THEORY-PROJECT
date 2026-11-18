# Figure captions

* **fig_mpki_all_predictors** — Absolute conditional-branch MPKI of 64K TSL, LLBP, LLBP-X, LLBP-X Opt-W and the ideal 512K TSL on the 14 server traces (100M warm-up + 200M measured instructions). 'Mean' is the arithmetic mean MPKI.
* **fig_accuracy** — Conditional-branch direction prediction accuracy (1 - mispredictions / conditional branches, in %) in the measured region. The y-axis does not start at zero because this is a position (dot) encoding; differences are small in absolute terms.
* **fig12_mpki_reduction_vs_64k_tsl** — Reproduction of Fig. 12 of the paper: MPKI reduction relative to 64K TSL. 'Mean' = reduction of mean MPKI (method of the official notebook). Black ticks on the Mean group mark the averages reported in the paper text.
* **fig_llbpx_vs_llbp_per_workload** — Per-workload MPKI improvement of LLBP-X over LLBP, (MPKI_LLBP - MPKI_LLBP-X)/MPKI_LLBP x 100, sorted. Grey bars would indicate regressions.
* **fig_llbpx_vs_tsl_scatter** — Per-workload MPKI of LLBP-X and of the ideal 512K TSL plotted against the 64K TSL baseline.
* **fig_overall_mean_mpki** — Arithmetic-mean MPKI over the 14 workloads; the percentage is the reduction of mean MPKI vs. 64K TSL. '-0Lat' variants do not model the pattern-store prefetch latency. IPC is not available from the trace-based simulator.
* **fig_table1_reproduction** — Baseline 64K TSL MPKI measured with the official CBP-style simulator vs. the values in Table I of the paper (which were obtained with the authors' ChampSim integration).
* **fig_ablation_breakdown** — Ablation of the two LLBP-X optimizations, all with prefetch latency modelled, relative to LLBP. Ablation models are project additions (runtime switches in the official LLBP-X model).
* **fig_simulation_time** — Mean wall-clock time per simulation run. Runs executed concurrently on a 17-core VM, so absolute times include contention; they are not predictor latencies.
* **fig_bandwidth** — Pattern-store traffic per instruction, averaged over the 14 workloads: reads = pattern sets fetched from the pattern store (HitInCI), writes = dirty write-backs, 288 bits each. Trace-based (no wrong-path execution), so it is not directly comparable with the gem5 numbers of the paper.
