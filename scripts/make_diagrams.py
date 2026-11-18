#!/usr/bin/env python3
"""make_diagrams.py -- schematic diagrams for the report.  [NEW, project team]
Drawn from the paper's description (Figs. 3, 10, 11) and the artifact code;
these are explanatory schematics, not data.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "REPORT" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
INK, INK2 = "#0b0b0b", "#52514e"
NEW = "#fde3d6"     # LLBP-X additions (light orange)
OLD = "#dbe8f8"     # LLBP components (light blue)
BASE = "#ecebe6"    # baseline TSL


def box(ax, x, y, w, h, text, fc, fs=9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec=INK2, lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=INK, weight="bold" if bold else "normal", wrap=True)


def arrow(ax, x0, y0, x1, y1, text=None, fs=7.5):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.1))
    if text:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, text, fontsize=fs, color=INK2,
                ha="center", va="bottom", backgroundcolor="white")


def architecture():
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.5); ax.axis("off")
    # top row: context formation and storage
    box(ax, 0.1, 3.7, 2.1, 1.2, "Rolling Context Register\nCID$_2$ and CID$_{64}$\n(RCR depth 8 → 64 UBs)", NEW, 8.3)
    box(ax, 2.9, 3.7, 1.7, 1.2, "Depth MUX\nselects CID$_2$\nor CID$_{64}$", NEW, 8.3)
    box(ax, 5.3, 3.7, 1.9, 1.2, "Context Directory\n14K contexts, 7-way", OLD, 8.3)
    box(ax, 7.9, 3.7, 2.0, 1.2, "LLBP Pattern Store\n16 patterns / set\n(4 buckets × 4)", OLD, 8.3)
    # middle row
    box(ax, 0.1, 1.8, 2.5, 1.2, "Context Tracking Table\n6K entries, 6-way\ntag | avg-hist-len | depth", NEW, 8.3)
    box(ax, 5.3, 1.8, 2.3, 1.2, "Pattern Buffer (64 sets)\nhistory range chosen\nby depth bit (8-way mux)", NEW, 8.1)
    box(ax, 7.9, 1.8, 2.0, 1.2, "64K TAGE-SC-L\n(unmodified)", BASE, 8.6)
    # bottom
    box(ax, 5.3, 0.2, 4.6, 0.8, "Final prediction: longest match wins,\nSC applied to the combined result", BASE, 8.2)
    arrow(ax, 2.2, 4.3, 2.9, 4.3)
    arrow(ax, 1.1, 3.7, 1.1, 3.0); ax.text(1.17, 3.3, "index by CID$_2$", fontsize=7.5, color=INK2)
    arrow(ax, 2.6, 2.8, 3.5, 3.7); ax.text(3.15, 3.05, "depth bit", fontsize=7.5, color=INK2)
    arrow(ax, 4.6, 4.3, 5.3, 4.3); ax.text(4.95, 4.38, "PCID", fontsize=7.5, color=INK2, ha="center")
    arrow(ax, 7.2, 4.3, 7.9, 4.3); ax.text(7.55, 4.38, "hit", fontsize=7.5, color=INK2, ha="center")
    arrow(ax, 8.6, 3.7, 7.3, 3.0); ax.text(8.25, 3.2, "prefetch\nset", fontsize=7.2, color=INK2)
    arrow(ax, 7.0, 3.0, 8.3, 3.7); ax.text(6.55, 3.25, "write-\nback", fontsize=7.2, color=INK2)
    arrow(ax, 5.3, 2.4, 2.6, 2.4)
    ax.text(3.95, 2.48, "overflow (7 confident patterns)\n+ allocated history lengths", fontsize=7.2,
            color=INK2, ha="center", va="bottom")
    arrow(ax, 6.45, 1.8, 6.45, 1.0)
    arrow(ax, 8.9, 1.8, 8.9, 1.0)
    for i, (fc, t) in enumerate([(NEW, "new / modified in LLBP-X"), (OLD, "original LLBP"), (BASE, "baseline")]):
        x = 0.1 + i * 2.6
        ax.add_patch(FancyBboxPatch((x, 5.1), 0.3, 0.25, boxstyle="round,pad=0.01", fc=fc, ec=INK2))
        ax.text(x + 0.4, 5.22, t, fontsize=8, va="center")
    fig.savefig(OUT / "diagram_llbpx_architecture.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def depth_fsm():
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.set_xlim(0, 10); ax.set_ylim(-0.6, 3); ax.axis("off")
    box(ax, 0.1, 1.0, 2.0, 1.1, "Untracked context\nW = 2\n(all hist. lengths)", BASE, 8.5)
    box(ax, 3.4, 1.0, 2.2, 1.1, "Tracked, shallow\nW = 2, histories 6–232\n(16 shortest)", OLD, 8.5)
    box(ax, 7.0, 1.0, 2.6, 1.1, "Tracked, deep\nW = 64, histories 37–3000\n(16 longest)", NEW, 8.5)
    arrow(ax, 2.1, 1.55, 3.4, 1.55)
    ax.text(2.75, 2.25, "pattern set reaches\n7 confident patterns", fontsize=7.5, ha="center", color=INK2)
    ax.annotate("", xy=(7.0, 1.85), xytext=(5.6, 1.85),
                arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.1, connectionstyle="arc3,rad=-0.3"))
    ax.text(6.3, 2.45, "counter > 7: many allocations\nwith history ≥ 232 bits", fontsize=7.5,
            ha="center", color=INK2)
    ax.annotate("", xy=(5.6, 1.25), xytext=(7.0, 1.25),
                arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.1, ls="--",
                                connectionstyle="arc3,rad=-0.3"))
    ax.text(6.3, 0.55, "paper: revert when allocations become short\n"
            "(artifact: this path is unreachable)", fontsize=7.3, ha="center", color=INK2, bbox=dict(fc="white", ec="none", pad=1.5), zorder=5)
    ax.annotate("", xy=(1.1, 1.0), xytext=(8.3, 1.0),
                arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.0,
                                connectionstyle="arc3,rad=-0.22"))
    ax.text(4.0, -0.35, "artifact: CTT entry evicted (LRU)\n→ context falls back to W = 2",
            fontsize=7.3, ha="center", color=INK2)
    fig.savefig(OUT / "diagram_depth_adaptation.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def methodology():
    fig, ax = plt.subplots(figsize=(10, 2.7))
    ax.set_xlim(0, 10); ax.set_ylim(0, 2.6); ax.axis("off")
    steps = [
        ("Paper +\nartifact study", BASE),
        ("Build official\nsimulator\n(+ ablation switches)", OLD),
        ("Download 14\nZenodo traces\n(1 GiB prefixes)", BASE),
        ("Smoke + regression\ntests (small trace,\nupstream binary)", OLD),
        ("11 models × 14\ntraces, 100M warm +\n200M measured", NEW),
        ("Parse → CSV →\ntables & graphs\n→ analysis/report", OLD),
    ]
    w, gap = 1.45, 0.2
    for i, (t, c) in enumerate(steps):
        x = 0.1 + i * (w + gap)
        box(ax, x, 0.7, w, 1.3, t, BASE if c != NEW else NEW, 6.9)
        if i < len(steps) - 1:
            arrow(ax, x + w, 1.35, x + w + gap, 1.35)
    ax.text(5.0, 0.25, "gem5: official LLBP/LLBP-X models patched into gem5 51759b5, SE-mode hello-world check",
            ha="center", fontsize=7.8, color=INK2)
    fig.savefig(OUT / "diagram_methodology.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    architecture(); depth_fsm(); methodology()
    print("diagrams written to", OUT)
