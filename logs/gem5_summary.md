gem5 was built with the official LLBP/LLBP-X gem5 models (gem5 commit 51759b5 + `artifact/scripts/llbpx.patch`) and the artifact's SE-mode hello-world test was run for TSL64k, LLBP and LLBP-X: all three completed, printed "Hello world!", and reported 58 conditional-branch mispredictions on 5,208 instructions (artifact README: "around 56"); this verifies the integration but is far too short to measure accuracy or IPC differences.

| gem5 model | Branch predictor SimObject(s) | Instructions | DirectCond lookups | Mispredictions (DirectCond) | IPC | Wall time |
|---|---|---|---|---|---|---|
| TSL64k | TAGE_SC_L_64KB | 5,208 | 2,003 | 58 | 0.1364 | 6.5 s |
| LLBP | LLBP (adaptCtxDepth=false, CIT 64×4) | 5,208 | 2,003 | 58 | 0.1364 | 4.6 s |
| LLBPX | LLBP (adaptCtxDepth=true, CIT 6144×6, 3-bit ctx counters) | 5,208 | 2,003 | 58 | 0.1364 | 4.5 s |

Build notes: the ARM build was OOM-killed twice on the 10 GiB VM (`arch/arm/generated/inst-constrs-3.o` needs ≈4 GB at `-O3 -g`); it succeeded after compiling that object alone (`-j 1`) and the rest with `-j 3` (see `logs/gem5_build.log`). Outputs: `results/gem5/<model>/{stats.txt,config.ini}` and `results/gem5/<model>.log`.
