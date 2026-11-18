<div class="titlepage" markdown="1">

<h1 class="title">Reproducing and Analysing LLBP-X: <br/>The Last-Level Branch Predictor Revisited</h1>

**University Research Project in Computer Architecture**

Project report

Based on: D. Schall, M. Ďuračková and B. Grot, "The Last-Level Branch Predictor Revisited," *HPCA-32*, 2026

Official artifact: <https://github.com/dhschall/LLBP-X> (commit `68e1cae`)

Report date: 16 November 2026

</div>

# Abstract

Branch mispredictions are a dominant source of lost cycles on modern server workloads, whose branch working sets far exceed the capacity of latency-constrained predictors such as the 64 KB TAGE-SC-L. The Last-Level Branch Predictor (LLBP) backs TAGE-SC-L with a large, decoupled pattern store and prefetches the patterns needed for upcoming *program contexts*. LLBP-X, proposed at HPCA 2026, revisits LLBP. It identifies contention in pattern sets of hard-to-predict branches and duplication of short-history patterns as LLBP's main inefficiencies, and introduces *dynamic context depth adaptation* together with *dynamic history range selection*.

This project reproduces the trace-based evaluation of LLBP-X using the authors' official artifact. We compare TAGE-SC-L (64 KB and an idealised 512 KB), the original LLBP and LLBP-X, including the oracle "Opt-W" variant, on all 14 official server traces. We use the paper's methodology of 100 M warm-up and 200 M measured instructions. To quantify the contribution of each optimisation, which the paper reports without a graph, we add two runtime ablation switches to the official LLBP-X model and verify that its default behaviour is bit-identical to upstream.

ABSTRACT_RESULTS_SENTENCE

All code, raw outputs, processed data, figures and scripts needed to regenerate every number in this report are included in the project repository.

# 1. Introduction

High-performance cores rely on the branch predictor to keep a deep and wide pipeline supplied with useful instructions. Every misprediction flushes the in-flight wrong-path work, typically tens of cycles and hundreds of instructions. The problem is acute for server software. Instruction footprints keep growing (Meta reports a 5.6× binary growth of a major service in four years), and Google measured that mispredictions waste 15.4 % of datacenter CPU cycles [1]. At the same time, the predictor sits on the critical fetch path, so its capacity cannot simply be increased without increasing latency [1].

LLBP [2] broke this capacity-latency trade-off with a two-level organisation. An unmodified TAGE-SC-L serves predictions at full speed. A high-capacity second level stores additional TAGE patterns grouped by *program context*, and the patterns of upcoming contexts are prefetched into a small pattern buffer. LLBP nevertheless recovers less than one third of the accuracy improvement of an equally sized (but unrealisable) 512 KB TAGE-SC-L. LLBP-X [1] analyses why and proposes a remedy that costs only about 9.4 KB of extra storage.

This report documents a complete reproduction study of LLBP-X:

* a technical analysis of the paper and its official artifact (Sections 2–6);
* the setup and integration of the official simulator and the three predictors, plus a small, verified extension that enables an ablation study (Sections 7–8);
* an evaluation on all 14 official server traces with the paper's warm-up and measurement windows (Sections 9–11);
* an analysis of the results and of what can and cannot be reproduced with the artifact (Sections 12–14).

**Contribution split.** The predictor models, the simulator, the gem5 models and the Opt-W tables are the work of the original authors. Our contributions are the experimental campaign and its infrastructure (driver, parser, plotting, PDF generation, robust trace downloader), the accuracy output and ablation switches in the simulator (90 added lines, documented in `src/patches/`), the regression validation, and all analysis and documentation.

# 2. Background and Related Work

## 2.1 TAGE and TAGE-SC-L

TAGE [3, 4] predicts with a bimodal base table plus several partially tagged tables indexed by hashes of the branch PC and global histories of geometrically increasing length. The longest matching table provides the prediction, and on a misprediction a new entry with a longer history is allocated. TAGE-SC-L [4] adds a statistical corrector (SC) for statistically biased branches and a loop predictor. The 64 KB TAGE-SC-L used as the baseline in both LLBP papers uses 21 tagged tables with histories from 6 to 3000 bits.

## 2.2 Larger and faster predictors

Making TAGE-SC-L 8× larger (512 KB) reduces mispredictions on the paper's workloads by 27.5 % on average. However, the prediction latency then grows beyond what a single-cycle or short overriding pipeline can tolerate [1, 5]. Prior approaches to hiding latency include overriding predictors [6], ahead pipelining [7, 8] and prefetching prediction counters into a small structure [5]. Whisper [9] and machine-learning predictors [10] target hard-to-predict branches with profiling and ISA support. Runahead-style pre-computation [11] targets data-dependent branches. LLBP and LLBP-X are purely microarchitectural and need neither profiling nor ISA changes.

## 2.3 The Last-Level Branch Predictor

LLBP [2] observes that the patterns needed to predict a branch depend on the global control-flow path leading to it (*context locality*). It hashes the last W unconditional branches, skipping the most recent D, into a context ID, and stores all patterns learned in that context in a 16-entry pattern set. Pattern sets live in a large pattern store indexed through a context directory. Because the context ID skips D branches, the pattern set for the next context is known early and can be prefetched into a 64-entry pattern buffer (PB) before it is needed. The PB is looked up in parallel with TAGE, and LLBP overrides TAGE when its matching pattern has an equal or longer history.

# 3. Problem Statement

Given a fixed storage budget of about 0.5 MB for branch-prediction metadata, LLBP reduces 64K TSL mispredictions by only 8.8 % on average, whereas an ideal 512K TSL reaches 27.5 % [1]. The problem addressed by LLBP-X is to **find the causes of this efficiency gap and reduce it without putting new structures on the prediction critical path**.

For this project, the problem statement is: *Using the official artifact, independently evaluate whether LLBP-X delivers the claimed accuracy improvements over TAGE-SC-L and LLBP on the official server traces, quantify the contribution of its two optimisations, and identify which claims can and cannot be reproduced with the available artifact.*

# 4. Motivation

* **Stalls from mispredictions grow with core aggressiveness.** The paper's hardware measurements show Sapphire Rapids has 15–60 % fewer mispredictions than Skylake, yet the fraction of stall cycles due to mispredictions increases by 7–45 %, because a larger instruction window hides other stalls but not flushes [1].
* **Capacity matters for servers.** The gap between 64K and 512K TSL (27.5 %) shows that much of the misprediction rate is a capacity problem.
* **LLBP leaves most of the opportunity unused.** A hierarchical design that matched the 512K TSL would be a practical way to buy a large accuracy gain.
* **Reproducibility.** The authors' README warns that artifact results "might slightly differ" from the paper, which used a ChampSim integration. An independent reproduction tells future users what to expect from the artifact.

# 5. Research Objectives

1. Understand the LLBP and LLBP-X designs and map every paper concept to the artifact code.
2. Build the official simulator and evaluate 64K TSL, 512K TSL, LLBP, LLBP-X and LLBP-X Opt-W under identical conditions on all 14 official traces.
3. Reproduce Table I (baseline MPKI) and Fig. 12 (MPKI reduction over 64K TSL) of the paper.
4. Quantify the separate contributions of dynamic context depth adaptation and dynamic history range selection (paper §VII-E).
5. Analyse accuracy, MPKI, per-workload behaviour, consistency and trade-offs, and classify each paper result as reproduced, partially reproduced or not reproducible.
6. Package everything as a clean, reproducible repository with documentation and this report.

# 6. Existing Branch Prediction Techniques

| Technique | Idea | Strength | Limitation for server workloads |
|---|---|---|---|
| Bimodal / gshare | PC-indexed or PC⊕history-indexed counters | Simple, single-cycle | Aliasing; no long-history correlation |
| Perceptron / neural predictors | Weighted sum of history bits | Long histories | Latency and energy; still capacity-bound |
| TAGE / TAGE-SC-L [3, 4] | Partial matching over geometric histories | State of the art, used commercially | 64 KB capacity too small for server branch working sets |
| Overriding / ahead pipelining [6–8] | Fast predictor overridden by slow one, or early prediction | Hides latency | Redirect penalties; whole predictor accessed every cycle |
| Profile-guided (Whisper) [9], CNN predictors [10] | Offline profiling of hard-to-predict branches | Large gains on targeted branches | Needs profiles, ISA and OS support |
| LLBP [2] | Context-organised second-level store with prefetch | Large capacity without latency | Pattern-set contention and duplication (§7) |
| **LLBP-X** [1] | LLBP + per-context adaptive context depth and history range | Better use of the same capacity | Still far from ideal 512K TSL; extra CTT energy |
