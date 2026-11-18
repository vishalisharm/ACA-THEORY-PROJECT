#!/bin/bash
# [NEW, project team] Download official LLBP/LLBP-X server traces from Zenodo
# record 13133243 (alternative to artifact/scripts/download_traces.sh).
# Usage: scripts/download_traces_prefix.sh >> logs/download.log 2>&1
# Bandwidth here is ~0.2-0.8 MB/s per connection, so only the first 1 GiB of each
# gzip trace is fetched (whole file if smaller). Each prefix must hold >300M
# instructions; check by decompressing it (see SETUP.md section 5) and extend
# short ones with scripts/extend_prefix.sh.
cd "$(dirname "$0")/../artifact/traces"
fetch() {
  f=$1; target=$2; last=$((target-1))
  for try in $(seq 1 400); do
    sz=$(stat -c%s $f.champsim.trace.gz 2>/dev/null || echo 0)
    [ "$sz" -ge "$target" ] && break
    # Fetch the next byte range into a temporary chunk; a stalled connection
    # (<20 KB/s for 25 s) is aborted and the loop resumes from the new offset.
    code=$(curl -s -L --max-time 900 --speed-limit 20000 --speed-time 25 \
      -r $sz-$last -o $f.part -w '%{http_code}' \
      "https://zenodo.org/records/13133243/files/$f.champsim.trace.gz?download=1")
    # Only append genuine partial-content responses (never error pages).
    if [ "$code" = "206" ] && [ -s $f.part ]; then cat $f.part >> $f.champsim.trace.gz; fi
    rm -f $f.part
    echo "$(date +%T) $f try=$try http=$code bytes=$(stat -c%s $f.champsim.trace.gz 2>/dev/null)/$target"
    sleep 3
  done
  echo "DONE $f $(stat -c%s $f.champsim.trace.gz)"
}
export -f fetch
P=1073741824
curl -s https://zenodo.org/api/records/13133243 | python3 -c "
import json,sys
fs={f['key'].split('.champsim')[0]:f['size'] for f in json.load(sys.stdin)['files']}
order=['whiskey.426708','charlie.1006518','delta.507252','benchbase-wikipedia','dacapo-spring','renaissance-finagle-chirper','dacapo-tomcat','merced.467915','benchbase-tpcc','benchbase-twitter','mwnginxfpm-wiki','nodeapp-nodeapp','renaissance-finagle-http','dacapo-kafka']
for k in order: print(k, min(fs[k], $P))
" | xargs -P 8 -L 1 bash -c 'fetch "$0" "$1"'
