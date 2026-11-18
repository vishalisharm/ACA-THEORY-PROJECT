#!/usr/bin/env python3
"""trace_manifest.py -- record exactly which trace bytes were used.  [NEW, project team]
Writes logs/trace_manifest.csv: local size, Zenodo size, completeness, SHA-256 of
the local file, and (for complete files) MD5 match against Zenodo.
"""
import csv, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
z = {r["file"]: r for r in csv.DictReader((ROOT / "configs/zenodo_trace_files.csv").open())}
rows = []
for p in sorted((ROOT / "artifact/traces").glob("*.champsim.trace.gz")):
    md5, sha = hashlib.md5(), hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            md5.update(chunk); sha.update(chunk)
    zs = int(z[p.name]["size_bytes"]) if p.name in z else -1
    complete = p.stat().st_size == zs
    rows.append({"file": p.name, "local_bytes": p.stat().st_size, "zenodo_bytes": zs,
                 "complete": complete, "fraction_used": round(p.stat().st_size / zs, 4),
                 "md5_matches_zenodo": (md5.hexdigest() == z[p.name]["md5"]) if complete else "n/a (prefix)",
                 "sha256": sha.hexdigest()})
    print(rows[-1]["file"], rows[-1]["local_bytes"], rows[-1]["complete"], rows[-1]["md5_matches_zenodo"])
with (ROOT / "logs/trace_manifest.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
