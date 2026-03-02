import json
from typing import Dict, Any


LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

def latex_escape(s: str) -> str:
    out = []
    for ch in s:
        out.append(LATEX_SPECIALS.get(ch, ch))
    return "".join(out)

def main():
    with open("template_meta.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    with open("filled_values.json", "r", encoding="utf-8") as f:
        filled = json.load(f)["filled_values"]

    # Build macro map
    field_to_macro: Dict[str, str] = {x["field_id"]: x["latex_macro"] for x in meta["fields"]}

    lines = []
    lines.append("% Auto-generated values for LaTeX macros")
    lines.append("% DO NOT EDIT MANUALLY\n")

    for fid, macro in field_to_macro.items():
        item: Dict[str, Any] = filled.get(fid, {})
        value = str(item.get("value", ""))
        value = latex_escape(value)
        # define macro
        lines.append(rf"\renewcommand\{macro}{{{value}}}")

    content = "\n".join(lines) + "\n"

    with open("values.tex", "w", encoding="utf-8") as f:
        f.write(content)

    print("Generated values.tex")

if __name__ == "__main__":
    main()
