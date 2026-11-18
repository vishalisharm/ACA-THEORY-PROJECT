# Regression check: upstream 68e1cae vs. project-modified binary

Trace: nodeapp-nodeapp-small (official Zenodo test trace, md5 d9dd9a1b… verified), `-w 5000000 -n 20000000 --simulate-btb`. Run on 2026-11-16.
Comparison: full stdout diff after removing only the lines the project added (ROI COND BRANCHES, ROI ACCURACY, the extended 'LLBP Config:' print, and the output-path line).

| model | upstream ROI MISP | modified ROI MISP | upstream ROI MPKI | modified ROI MPKI | all other output identical |
|---|---|---|---|---|---|
| tage64kscl | 54533 | 54533 | 2.7267 | 2.7267 | YES |
| tage512kscl | 35240 | 35240 | 1.7620 | 1.7620 | YES |
| llbp | 42845 | 42845 | 2.1423 | 2.1423 | YES |
| llbp-timing | 44610 | 44610 | 2.2305 | 2.2305 | YES |
| llbpx | 41826 | 41826 | 2.0913 | 2.0913 | YES |
| llbpx-timing | 43552 | 43552 | 2.1776 | 2.1776 | YES |

Note: the small trace is only ~40M instructions long, so these runs are a regression test only (not experimental results).
