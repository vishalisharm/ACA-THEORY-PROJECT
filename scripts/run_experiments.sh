#!/bin/bash
# =============================================================================
# run_experiments.sh  --  LLBP-X project experiment driver   [NEW, project team]
#
# Derived from the official artifact script artifact/scripts/eval_all.sh:
# same predictor binary, same flags (--simulate-btb), same warm-up/measure
# windows (100M / 200M instructions) and the same Opt-W table files.
# Additions: bounded job pool (no GNU parallel needed), skip-if-done,
# per-run wall-clock/max-RSS capture and a CSV run log.
#
# Usage:
#   scripts/run_experiments.sh [-j JOBS] [-w WARM] [-n SIM] [-m "models"] [-t "traces"]
# Example (full evaluation, defaults):
#   scripts/run_experiments.sh -j 14
# =============================================================================
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ART="$ROOT/artifact"
BIN="$ART/build/predictor"
RAW="${RAW_DIR:-$ROOT/results/raw}"
LOG="${LOG_FILE:-$ROOT/logs/experiments.csv}"

JOBS=$(( $(nproc) - 3 ))
N_WARM=100000000
N_SIM=200000000
MODELS="tage64kscl tage512kscl llbp llbp-timing llbpx llbpx-timing llbpx-optw \
        llbpx-timing-nodepth llbpx-timing-norange llbpx-nodepth llbpx-norange"
TRACES="mwnginxfpm-wiki dacapo-kafka dacapo-tomcat dacapo-spring \
        renaissance-finagle-chirper renaissance-finagle-http benchbase-tpcc \
        benchbase-twitter benchbase-wikipedia nodeapp-nodeapp charlie.1006518 \
        delta.507252 merced.467915 whiskey.426708"

while getopts "j:w:n:m:t:" o; do
  case $o in
    j) JOBS=$OPTARG ;; w) N_WARM=$OPTARG ;; n) N_SIM=$OPTARG ;;
    m) MODELS=$OPTARG ;; t) TRACES=$OPTARG ;;
    *) echo "bad option"; exit 1 ;;
  esac
done

[ -x "$BIN" ] || { echo "Build the simulator first (see SETUP.md)"; exit 1; }
mkdir -p "$RAW" "$(dirname "$LOG")"
[ -f "$LOG" ] || echo "timestamp,model,trace,warmup,sim,exit_code,wall_s,maxrss_kb" > "$LOG"

run_one() {
  local model=$1 fn=$2
  local trace="$ART/traces/$fn.champsim.trace.gz"
  local out="$RAW/$fn/$model.txt"
  mkdir -p "$RAW/$fn"
  # Skip completed runs (final statistics block present).
  if [ -f "$out" ] && grep -q "ROI ACCURACY" "$out"; then return 0; fi
  if [ ! -s "$trace" ]; then echo "missing trace $trace"; return 1; fi
  local tload=""
  if [ "$model" = "llbpx-optw" ]; then
    tload="--tableload $ART/traces/$fn-bestWbCtx_patterns_ODH_t16x14k_CT14_D4_264.csv"
  fi
  local t0=$(date +%s.%N)
  /usr/bin/time -f "%M" -o "$out.rss" \
    "$BIN" "$trace" --model "$model" --simulate-btb $tload \
      -w "$N_WARM" -n "$N_SIM" --output "$RAW/$fn/$model" > "$out" 2>&1
  local rc=$?
  local t1=$(date +%s.%N)
  local wall=$(echo "$t1 - $t0" | bc)
  local rss=$(tail -1 "$out.rss" 2>/dev/null); rm -f "$out.rss"
  echo "WALL_SECONDS $wall" >> "$out"
  echo "MAXRSS_KB $rss" >> "$out"
  echo "$(date -Iseconds),$model,$fn,$N_WARM,$N_SIM,$rc,$wall,$rss" >> "$LOG"
  echo "[$(date +%T)] done $model $fn rc=$rc ${wall}s"
}

# Simple bounded job pool.
for fn in $TRACES; do
  for model in $MODELS; do
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n; done
    run_one "$model" "$fn" &
  done
done
wait
echo "All requested simulations finished."
