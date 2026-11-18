#!/bin/bash
# Extend trace prefixes that turned out too short for 300M instructions
# (dacapo-kafka and nodeapp-nodeapp held only ~280M / ~276M instructions in
# their first 1 GiB). Usage: extend_prefix.sh <trace> <target_bytes> ...
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
while [ $# -ge 2 ]; do fetch "$1" "$2" & shift 2; done
wait
