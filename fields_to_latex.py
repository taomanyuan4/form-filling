import json
import re
from typing import Dict, Any, List

def slugify_macro(label: str) -> str:
    """
    Label -> LaTeX macro name, e.g. "Student Name" -> StudentName
    """
    parts = re.findall(r"[A-Za-z0-9]+", label)
    if not parts:
        return "Field"
    # CamelCase
    return "".join(p[:1].upper() + p[1:] for p in parts)

def px_to_cm(px: float, page_w_px: float, textwidth_cm: float) -> float:
    return (px / page_w_px) * textwidth_cm

def render_latex(fields: List[Dict[str, Any]], page_w: float,
                 textwidth_cm: float = 17.0) -> str:
    """
    Render a simple 2-column form using tabularx.
    textwidth_cm: approximate LaTeX \\textwidth in cm given your geometry settings.
    """
    # split columns
    left = [f for f in fields if f["col"] == "left"]
    right = [f for f in fields if f["col"] == "right"]

    # Align rows by order (simple). For many real forms, you may want y-based pairing later.
    n = max(len(left), len(right))
    left += [None] * (n - len(left))
    right += [None] * (n - len(right))

    # Build macro definitions
    macros = []
    for f in fields:
        macro = slugify_macro(f["label"])
        macros.append(f"\\newcommand\\{macro}{{}}")

    macros_block = "\n".join(sorted(set(macros)))

    def field_cell(f, line_cm):
        if f is None:
            return "", ""
        label = f["label"] + ":"
        macro = "\\" + slugify_macro(f["label"])
        # line length limited to avoid overflow; you can tune
        return label, f"\\FormLine{{{line_cm:.2f}cm}}{{{macro}}}"

    # For each field, compute line length from value_bbox width in px
    # Note: For tabularx, the line length is better set as a constant per column,
    # but here we demonstrate direct mapping for research/prototyping.
    latex_rows = []
    for i in range(n):
        lf = left[i]
        rf = right[i]

        if lf:
            v = lf["value_bbox"]
            wpx = float(v[2]) - float(v[0])
            lcm = px_to_cm(wpx, page_w, textwidth_cm * 0.48)  # ~ half textwidth per column
        else:
            lcm = 0.0
        l_label, l_line = field_cell(lf, lcm)

        if rf:
            v = rf["value_bbox"]
            wpx = float(v[2]) - float(v[0])
            rcm = px_to_cm(wpx, page_w, textwidth_cm * 0.32)  # right col often narrower
        else:
            rcm = 0.0
        r_label, r_line = field_cell(rf, rcm)

        latex_rows.append(
            f"{l_label} & {l_line} & {r_label} & {r_line} \\\\"
        )

    rows_block = "\n".join(latex_rows)

    tex = rf"""
% !TEX program = xelatex
\documentclass[11pt]{{article}}
\usepackage[a4paper,margin=18mm]{{geometry}}
\usepackage{{fontspec}}
\setmainfont{{TeX Gyre Termes}}
\usepackage{{tabularx}}
\usepackage{{array}}
\pagenumbering{{gobble}}
\setlength{{\parindent}}{{0pt}}
\renewcommand{{\arraystretch}}{{1.25}}

% -------------------------
% Auto-generated field macros
% -------------------------
{macros_block}

\newcommand{{\FormLine}}[2]{{\rule{{0pt}}{{2.4ex}}\underline{{\makebox[#1][l]{{#2}}}}}}

\begin{{document}}
{{\LARGE\bfseries STUDENT INFORMATION FORM}}\par
\vspace{{8mm}}

\noindent
\begin{{tabularx}}{{\textwidth}}{{@{{}}>{{\bfseries}}l X @{{\hspace{{8mm}}}} >{{\bfseries}}l X@{{}}}}
{rows_block}
\end{{tabularx}}

\end{{document}}
""".strip()

    return tex

def main():
    with open("fields.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    page_w = float(data["page"]["w"])
    fields = data["fields"]

    tex = render_latex(fields, page_w)

    with open("template.tex", "w", encoding="utf-8") as f:
        f.write(tex)

    print("Generated template.tex")

if __name__ == "__main__":
    main()
