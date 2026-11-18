#!/bin/bash
# [NEW, project team] Runs all models on each trace as soon as logs/download.sh
# reports it complete ("DONE <trace> <bytes>"), one trace at a time.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ALL="mwnginxfpm-wiki dacapo-kafka dacapo-tomcat dacapo-spring renaissance-finagle-chirper renaissance-finagle-http benchbase-tpcc benchbase-twitter benchbase-wikipedia nodeapp-nodeapp charlie.1006518 delta.507252 merced.467915 whiskey.426708"
declare -A started
while :; do
  left=0
  for t in $ALL; do
    [ -n "${started[$t]}" ] && continue
    left=1
    if grep -q "^DONE $t " "$ROOT/logs/download.log"; then
      started[$t]=1
      echo "[$(date +%T)] starting $t"
      "$ROOT/scripts/run_experiments.sh" -j ${JOBS:-11} -t "$t"
    fi
  done
  [ $left -eq 0 ] && break
  sleep 30
done
echo "[$(date +%T)] all traces simulated"
