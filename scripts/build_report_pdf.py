#!/usr/bin/env python3
"""build_report_pdf.py -- REPORT/project_report.md -> REPORT/project_report.pdf
[NEW, project team]  Uses python-markdown + WeasyPrint (no pandoc/LaTeX needed).
"""
from pathlib import Path
import re
import sys

import markdown
import weasyprint

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "REPORT" / "project_report.md"
DST = SRC.with_suffix(".pdf")

CSS = """
@page { size: A4; margin: 22mm 20mm 22mm 20mm;
        @bottom-center { content: counter(page); font-size: 9pt; color: #52514e; } }
@page :first { @bottom-center { content: none; } }
body { font-family: "DejaVu Serif", "Liberation Serif", serif; font-size: 10.5pt;
       line-height: 1.42; color: #111; text-align: justify; hyphens: auto; }
h1 { font-size: 17pt; margin: 1.4em 0 0.4em; page-break-after: avoid;
     font-family: "DejaVu Sans", sans-serif; color: #0b0b0b; }
h1.title { page-break-before: avoid; }
h2 { font-size: 13pt; margin: 1.1em 0 0.35em; page-break-after: avoid; font-family: "DejaVu Sans", sans-serif; }
h3 { font-size: 11pt; margin: 0.9em 0 0.3em; font-family: "DejaVu Sans", sans-serif; }
p { margin: 0.35em 0 0.55em; }
table { border-collapse: collapse; margin: 0.6em auto 0.9em; font-size: 8.6pt;
        font-family: "DejaVu Sans", sans-serif; page-break-inside: avoid; }
th, td { border-bottom: 0.5pt solid #c3c2b7; padding: 2.5pt 5pt; text-align: right; }
th { border-bottom: 1pt solid #52514e; text-align: center; background: #f4f3ef; }
td:first-child, th:first-child { text-align: left; }
p.eq { text-align: center; margin: 0.5em 0; }
p.eq img { display: inline; margin: 0; }
img { max-width: 100%; display: block; margin: 0.4em auto 0.2em; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.6pt; }
pre { background: #f6f5f1; padding: 6pt 8pt; font-size: 8pt; white-space: pre-wrap;
      border-left: 2pt solid #c3c2b7; page-break-inside: avoid; }
blockquote { margin: 0.5em 1.5em; color: #333; font-style: italic; }
em.caption, p.caption { font-size: 9pt; color: #333; }
.titlepage { text-align: center; margin-top: 35mm; page-break-after: always; }
.titlepage h1 { font-size: 22pt; page-break-before: avoid; }
.titlepage p { text-align: center; }
div.toc { font-size: 9.5pt; }
div.toc ul { list-style: none; padding-left: 1.2em; }
"""


def render_equations(md_text):
    """Render $$...$$ display math to PNG with matplotlib mathtext (WeasyPrint
    has no math engine). GitHub renders the same $$ blocks natively."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams["mathtext.fontset"] = "dejavuserif"
    out = SRC.parent / "figures" / "eq"
    out.mkdir(parents=True, exist_ok=True)
    count = [0]

    def repl(m):
        tex = " ".join(m.group(1).split())
        count[0] += 1
        f = out / f"eq_{count[0]:02d}.png"
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${tex}$", fontsize=13)
        fig.savefig(f, dpi=220, bbox_inches="tight", pad_inches=0.04, transparent=True)
        plt.close(fig)
        from PIL import Image
        w, h = Image.open(f).size
        return (f'\n<p class="eq"><img src="figures/eq/{f.name}" '
                f'style="width:{w / 220 * 72 * 0.82:.1f}pt"/></p>\n')

    return re.sub(r"\$\$(.+?)\$\$", repl, md_text, flags=re.S)


def main():
    md_text = render_equations(SRC.read_text())
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "attr_list", "md_in_html", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "1-2"}},
    )
    # Figure captions: paragraphs that start with "Figure N." or "Table N." in italics
    html_body = re.sub(r"<p><em>((?:Figure|Table) [^<]*)</em></p>",
                       r'<p class="caption"><em>\1</em></p>', html_body)
    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}</body></html>"
    weasyprint.HTML(string=html, base_url=str(SRC.parent)).write_pdf(DST)
    print("wrote", DST, f"{DST.stat().st_size/1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
