# Paper Analysis — *The Last-Level Branch Predictor Revisited* (LLBP-X)

**Paper:** D. Schall, M. Ďuračková, B. Grot, "The Last-Level Branch Predictor Revisited," *Proc. 32nd IEEE Int. Symp. on High-Performance Computer Architecture (HPCA-32)*, 2026.
**Copy used:** `docs/paper/LLBP_X_HPCA26.pdf`, not committed; see `docs/paper/README.md` (downloaded from the EASE Lab publication page, <https://ease-lab.github.io/ease_website/pubs/LLBPX_HPCA26.pdf>). The predecessor paper (LLBP, MICRO 2024) was also read (<https://dhschall.github.io/assets/pdf/LLBP_MICRO24.pdf>).
**Official artifact:** <https://github.com/dhschall/LLBP-X>, inspected at commit `68e1cae` ("Fix eval script"), and vendored in `artifact/`.

All statements below come from the paper text or from the artifact's source code. Section and figure numbers refer to the HPCA'26 paper. Where the paper and the code differ, both are given.

---

## 1. What problem does the paper address?

Server workloads have very large instruction and branch working sets. The paper cites a 5.6× growth in a Meta web-service binary over four years, and a Google study finding that branch mispredictions waste 15.4 % of datacenter execution cycles. Meanwhile, branch-predictor capacity is stuck because the predictor sits on the latency-critical fetch path. A larger single-level predictor is more accurate but slower, and beyond some point the extra latency cancels the accuracy gain (§II-B, the "capacity-latency trade-off").

The paper's motivating measurement (§I, §II-A): on its server workloads, a 64 KB TAGE-SC-L (TSL) mispredicts at 0.29–6.4 MPKI (avg. 2.91), i.e. one pipeline flush every ~344 instructions. Hardware counters show that Sapphire Rapids has 15–60 % fewer mispredictions than Skylake. Yet the *fraction* of stall cycles caused by mispredictions *rises* by 7–45 % (avg. 30 %), because a wider and deeper core hides other stalls but cannot hide flushes.

**Objective of LLBP-X:** to understand why the hierarchical LLBP design (MICRO'24) recovers less than one third of the accuracy of an equally sized but impractical 512 KB TAGE-SC-L, and to close part of that gap with minimal hardware changes.

## 2. Why are existing predictors insufficient?

* **TAGE-SC-L (64 KB):** state of the art and used commercially. However, its capacity is too small for server branch working sets. Going from 64 KB to 512 KB cuts mispredictions by 12.7–46.1 % (avg. 27.5 %). A 512 KB TSL cannot be accessed within a cycle, so it is unrealisable.
* **TAGE hashing kills locality:** TAGE hashes PC with global history and spreads a branch's patterns over all tables. You therefore cannot tell which patterns belong to an upcoming branch, which makes a simple two-level TAGE hierarchy impossible to prefetch for (§I).
* **Huge variance in patterns per branch:** most branches need a few patterns, while hard-to-predict (H2P) branches need hundreds to thousands. Google traces show >9K patterns for the hardest branches, far too many to prefetch.
* **Original LLBP:** solves the latency problem, but only reaches an 8.8 % average MPKI reduction over 64K TSL (0.6–25 %). The ideal 512K TSL reaches 27.5 % (§II-C.5, Fig. 4).

## 3. Original LLBP architecture (§II-C, Fig. 3)

LLBP keeps an **unmodified 64K TSL** as the first level and adds a decoupled, high-capacity second level of TAGE-style patterns.

| Component | Role | Artifact parameter (`bpmodels/llbp/llbp.h`) |
|---|---|---|
| **Rolling Context Register (RCR)** | Hashes the last W unconditional branches (UBs), skipping the most recent D, to form a *context ID* (CCID). It also forms a prefetch context ID (PCID) from the most recent UBs. | `T=3` (all UBs), `W=8`, `D=4`, `S=1` |
| **Context Directory (CD)** | Tag array for pattern sets: 14K contexts, 7-way. | `numContexts=14336`, `ctxAssoc=7`, `CTWidth=14` |
| **LLBP Pattern Store (PS)** | Data array: one 16-pattern *pattern set* per context (4 buckets × 4 patterns). | `numPatterns=16`, `ptrnAssoc=4`, `TTWidth=13` |
| **Pattern Buffer (PB)** | Small in-core cache of the active and prefetched pattern sets, looked up in parallel with TAGE. | `pbSize=64`, `pbAssoc=4` |

* **Prediction:** the PB tag-matches all patterns of the current context. The longest matching pattern wins. LLBP overrides TAGE only if its match has the *same or a longer* history than TAGE's provider. When LLBP provides the prediction, the SC is suppressed.
* **Pattern:** a tag, a history-length field and a 3-bit prediction counter. Only **16 of TAGE's 21 history lengths** are kept (artifact: TAGE table indices `{6,10,13,14,15,16,17,18,19,20,22,24,26,28,32,36}`), four per bucket.
* **Prefetching:** because the CCID skips the D most recent UBs, the pattern set can be fetched D UBs ahead, which hides the multi-cycle PS access (6 cycles in the paper; `accessDelay` ticks in the CBP model).
* **Allocation:** on a misprediction, both TAGE and LLBP allocate a longer pattern. A missing pattern set is created and its context written to the CD; the least-confident pattern is replaced.

## 4. Where LLBP loses accuracy (§III)

The paper runs a limit study (Fig. 5) on a 0-latency LLBP and removes one constraint at a time:

| Step removed | Additional MPKI reduction |
|---|---|
| Design tweaks (bucketing, 16 history lengths, SC suppression) | 4.6 % |
| 13-bit → 20-bit pattern tag | 1.3 % |
| Unlimited contexts | 3.9 % |
| **Unlimited patterns per set** | **9.1 %** (largest) |
| **No contextualization** (context = branch PC) | **4.3 %** |

With every constraint removed, LLBP almost matches an infinite TSL. The remainder is due to the prefetch distance D; with D=0 it matches exactly.

Two findings follow (Figs. 6–9, NodeApp):

1. **Skewed pattern-set utilization.** Only 14 % of contexts exceed 16 useful patterns, while 68 % hold 8 or fewer. The over-full contexts are exactly those whose useful patterns have long histories (avg. up to 112 bits), i.e. contexts holding **H2P branches**.
2. **Duplication caused by contextualization.** Short-history patterns are copied into many contexts, and more so for larger W. At history length 6, 8.5 % (W=2), 10.1 % (W=8) and 17.2 % (W=64) of patterns are duplicates. Duplication wastes capacity and lengthens training/adaptation time. Fig. 9: W=2 increases useful predictions for short histories (6–37 bits) by 63–213 %, while W=64 increases useful predictions for long histories (232–3000 bits) by 4.2–95 %.

**Summary (§III-D):** there is a 25.1 % accuracy gap between a 0-latency 512 KB LLBP and an infinite TSL. 53 % of it comes from pattern-set capacity plus contextualization overhead.

## 5. What LLBP-X changes (§V, Fig. 10)

LLBP-X keeps the LLBP structure and adds two mechanisms.

### 5.1 Dynamic context depth adaptation

* **Default shallow depth W = 2** for every context, which minimises duplication and training time.
* **Deep depth W = 64** for contexts under pressure, which spreads their patterns over many pattern sets. Only two depths are used. More depths gave marginal gains, because every switch discards learned patterns (switching penalty).
* **Context Tracking Table (CTT):** a new 6K-entry, 6-way, LRU structure (9 KB). Each entry holds a 6-bit tag, a 3-bit `avg-hist-len` saturating counter, a 1-bit depth flag and 2 replacement bits. It is indexed by the shallow context ID CID₂, *regardless of the depth in use*.
* **Trigger, heuristic 1 (pattern pressure):** the PB raises an *overflow* signal once a pattern set holds **T_max = 7 confident patterns**. The context then starts being tracked in the CTT.
* **Trigger, heuristic 2 (history length):** for a tracked context, `avg-hist-len` increments when an allocated pattern's history exceeds **H_th = 232 bits** and decrements otherwise. When it saturates (exceeds 7), the depth bit flips to W=64. The same mechanism with hysteresis can switch back to W=2 if allocations become short.
* **RCR change:** the RCR computes **CID₂ and CID₆₄ in parallel** (its depth grows from 8 to 64 UBs). A multiplexer controlled by the CTT depth bit picks one of them for both the PCID (prefetch) and the CCID (PB index). All of this is off the critical path.

**How the artifact implements this** (`bpmodels/llbpx/llbpx.cc`, macros `ADAPTIVE_W_CTX`, `ADAPTIVE_W_BY_CONF`, `ADAPTIVE_W_REALISTIC`):
* `WS[2] = {2, 64}`. The CTT is `cit` (`CitSize = 6*1024`, `CitAssoc = 6`), keyed by `rcr.getBaseCtx()`, a 16-bit (`BCTWidth`) W=2 base context.
* When a pattern becomes confident and the set's `confidentPtrns == adaptThreshold (7)`, the context is inserted into the CTT (`fullPatternSets++`).
* In `llbpAllocate`, the counter `allocVsDrop` moves up or down depending on whether `histLen` is at least `histLenThreshold = 22`. That is a *TAGE table index*, and index 22 corresponds to the 232-bit history. Once `allocVsDrop > 7`, the depth `wi` switches from 0 (W=2) to 1 (W=64). **Discrepancy:** the switch block is guarded by `ci->wi < nW-1`, so the coded W=64→W=2 transition is unreachable. A deep context reverts to W=2 only when its CTT entry is evicted, not via the counter-based hysteresis the paper describes (§V-B.1).

### 5.2 Dynamic history range selection (§V-C, Fig. 11)

Shallow contexts mostly hold short patterns and deep contexts hold long ones. LLBP-X therefore supports **all 21 TAGE history lengths** but limits each depth to 16 of them:
* W = 2 → the 16 shortest lengths, **6–232 bits**;
* W = 64 → the 16 longest lengths, **37–3000 bits**.

An allocation outside the active range is dropped, but it still updates `avg-hist-len`. Bucketing stays at 4 buckets × 4 lengths. In hardware, the depth bit feeds the history-length mux, which grows from 4-way to 8-way.

**Artifact:** macro `FILTER_TABLES_HLEN_16` builds `fltTables[0]` from TAGE indices ≤ 22 and `fltTables[1]` from indices ≥ 12. `llbpAllocate` drops `wi==0 && histLen>22` and `wi==1 && histLen<12`.

### 5.3 Other details
* The combined PB+TAGE result is fed to the SC (§VI). LLBP-X does not suppress SC the way LLBP does.
* **Storage overhead:** CTT 9 KB + RCR 224 B + 3-bit CD replacement counters 142 B ≈ 9.36 KB, i.e. 1.8 % over LLBP's 515 KB.
* **Discussion points:** multiple predictions per cycle (§V-D.1), and use in an overriding predictor, since the PB is <5 % of TAGE's size (§V-D.2).

## 6. LLBP-X vs. TAGE-SC-L and LLBP: the paper's claims

| Claim | Value | Source |
|---|---|---|
| LLBP MPKI reduction vs. 64K TSL | 0.6–25 % (avg. 8.8 %) | §II-C.5 / Fig. 4 |
| **LLBP-X** MPKI reduction vs. 64K TSL | **1.4–27 % (avg. 12.1 %)**, max on NodeApp | §VII-A / Fig. 12 |
| LLBP-X Opt-W (offline-optimal W per context) | 1.7–28.4 % (avg. 12.6 %); LLBP-X reaches 97 % of optimal | §VII-A |
| 512K TSL (ideal, 0-latency) | 12.7–46.1 % (avg. 27.5 %) | §VII-A |
| LLBP-X accuracy gain over LLBP | 0.8–11.5 % (avg. 3.6 %); "36 % average improvement over the original design" | Abstract, §VII-A |
| Optimization breakdown | depth adaptation 82 %, history range selection 18 % of the LLBP→LLBP-X MPKI gain (graph omitted in paper) | §VII-E |
| H_th sweep | best 232 (13.6 % reduction), worst 1444 (12.2 %) | §VII-F |
| CTT size sweep | 4K entries: 12.8 %; 6K entries: 13.6 %; no gain beyond | §VII-F |
| Speedup (gem5, 10 non-Google workloads) | LLBP-X 1.0 % avg (0.08–2.7 %), LLBP 0.71 %, 512K TSL 2.4 % | §VII-B / Fig. 13 |
| Overriding scheme (3-cycle) | LLBP-X 1.4 % vs. 128K TSL 0.6 % | §VII-C / Fig. 14b |
| Prefetch coverage | 84 % on time, ~40 % over-prefetch | Fig. 14a |
| Transfer bandwidth | 9.9 vs. 10.6 bits/instr (−6.1 %) | Fig. 15a |
| Energy | +1.5 % vs. LLBP (CTT +5.2 %, PS −5.4 %) | Fig. 15b |
| Pattern-store size sweep | 10.5 % (8K ctx) → 17.6 % (128K ctx) | Fig. 16a |
| Smaller base TSL | still 2.6 % reduction on a 16K TSL | Fig. 16b |

Note that the "13.6 %" in §VII-F and the "12.1 %" in §VII-A differ. The paper does not explain this; the sensitivity study probably used a different (e.g. 0-latency) configuration.

## 7. Benchmark workloads (Table I)

There are 14 server traces in ChampSim format, with user and kernel instructions (Zenodo 10.5281/zenodo.13133242). The paper lists 64K TSL MPKI as follows:

| Paper name | Trace file | Suite | 64K TSL MPKI (paper) |
|---|---|---|---|
| NodeApp | nodeapp-nodeapp | NodeJS web server | 4.43 |
| PHPWiki | mwnginxfpm-wiki | PHP-FPM wiki server | 3.08 |
| TPCC | benchbase-tpcc | Java BenchBase | 3.74 |
| Twitter | benchbase-twitter | Java BenchBase | 3.03 |
| Wikipedia | benchbase-wikipedia | Java BenchBase | 2.52 |
| Kafka | dacapo-kafka | Java DaCapo | 0.26 |
| Spring | dacapo-spring | Java DaCapo | 3.58 |
| Tomcat | dacapo-tomcat | Java DaCapo | 3.40 |
| Chirper | renaissance-finagle-chirper | Java Renaissance | 0.48 |
| HTTP | renaissance-finagle-http | Java Renaissance | 2.81 |
| Charlie | charlie.1006518 | Google workload traces | 2.89 |
| Delta | delta.507252 | Google workload traces | 1.09 |
| Merced | merced.467915 | Google workload traces | 4.13 |
| Whiskey | whiskey.426708 | Google workload traces | 5.38 |

Ten traces were collected by the authors in gem5 full-system mode (Ubuntu 20.04, kernel 5.4.84). The four Google traces come from the DynamoRIO Google Workload Traces. The Google traces cannot be used in gem5, so they are excluded from the speedup study.

## 8. Metrics and methodology (§VI)

* **Primary metric:** conditional-branch **MPKI** (mispredictions per 1000 instructions), reported as *MPKI reduction relative to 64K TSL*.
* **Trace-based (CBP-style) simulation:** 100M warm-up + 200M measured instructions. The simulator models only the predictor and a BTB, not the pipeline.
* **gem5 (v25.0/25.1):** 200M warm-up + 300M measured instructions; 4 GHz 8-wide OoO, 576-entry ROB, 16K-entry BTB, FDIP (Table II). Used for speedup, prefetch, false-path and overriding studies.
* **Energy:** CACTI 7.0 at 22 nm.

## 9. Major findings, in short
1. LLBP's accuracy loss is concentrated in a few over-subscribed pattern sets (H2P branches) and in duplicated short patterns.
2. Choosing the context depth per context (shallow by default, deep under pressure) addresses both problems with ~9.4 KB of extra state.
3. LLBP-X improves the average MPKI reduction over 64K TSL from 8.8 % (LLBP) to 12.1 %, within 97 % of an oracle W choice. It still lags far behind the ideal 512K TSL (27.5 %), which the authors leave as an open opportunity.
4. The IPC gains are modest (1.0 % avg. vs. 0.71 % for LLBP). Bandwidth drops slightly and energy rises slightly.

## 10. What the artifact provides vs. what the paper reports

| Paper item | In artifact? | Notes |
|---|---|---|
| Fig. 12 MPKI reduction (LLBP, LLBP-X, Opt-W, 512K TSL) | **Yes**: `scripts/eval_all.sh`, `analysis/mpki.ipynb` | The README warns that results "might slightly differ" because the paper used a ChampSim integration. |
| Table I 64K TSL MPKI | **Yes** (model `tage64kscl`) | |
| Opt-W | **Yes**: `llbpx-optw` + per-trace `*-bestWbCtx_*.csv` tables shipped in `traces/` | The tables were produced offline by the authors; the script that generates them is not included. |
| §VII-E optimization breakdown | **No** | We added runtime ablation switches (see `IMPLEMENTATION.md`). |
| Figs. 5–9 limit study | **No** | Needs unconstrained/infinite variants that are not exposed. |
| §VII-F/G sensitivity (H_th, CTT size, PS size, TSL size) | Partially (parameters exist in `LLBPXConfig`) | Not scripted; not run by us. |
| Fig. 13/14 speedup, prefetch, overriding | gem5 model + SE "hello world" only | The full-system server setup is explicitly *not* provided. |
| Fig. 15 bandwidth/energy | **No** | CACTI models are not included. |
