import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

@dataclass
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def h(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0

def bbox_from_list(b):
    return BBox(float(b[0]), float(b[1]), float(b[2]), float(b[3]))

def y_overlap_ratio(a: BBox, y0: float, y1: float) -> float:
    """Overlap ratio between bbox a and a [y0,y1] interval."""
    inter = max(0.0, min(a.y1, y1) - max(a.y0, y0))
    return inter / max(1e-6, a.h)

def is_label_text(t: str) -> bool:
    """Minimal label heuristic: colon indicates label."""
    t = t.strip()
    return (":" in t) and (len(t) <= 50)

def normalize_label(t: str) -> str:
    t = t.strip()
    if t.endswith(":"):
        t = t[:-1]
    return " ".join(t.split())

def line_is_horizontal(line: Dict[str, Any], slope_tol: float = 2.0) -> bool:
    return abs(float(line["y2"]) - float(line["y1"])) <= slope_tol

def pick_value_line_for_label(label_box: BBox, lines: List[Dict[str, Any]],
                              min_len: float = 40.0,
                              y_band_scale: float = 0.8) -> Optional[Dict[str, Any]]:
    """
    Choose the best horizontal line to the right of label_box on same row.
    """
    y0 = label_box.y0 + (1.0 - y_band_scale) * label_box.h / 2.0
    y1 = label_box.y1 - (1.0 - y_band_scale) * label_box.h / 2.0

    candidates = []
    for ln in lines:
        if not line_is_horizontal(ln):
            continue
        x1, y1n, x2, y2n = map(float, [ln["x1"], ln["y1"], ln["x2"], ln["y2"]])
        # normalize direction
        lx0, lx1 = (x1, x2) if x1 <= x2 else (x2, x1)
        ly = (y1n + y2n) / 2.0

        length = lx1 - lx0
        if length < min_len:
            continue
        # must be to the right (allow small overlap)
        if lx1 <= label_box.x1 + 5:
            continue
        # allow line slightly below the label (common in forms)
        if not (label_box.y0 <= ly <= label_box.y1 + 0.8 * label_box.h):
            continue


        candidates.append((length, lx0, lx1, ly, ln))

    if not candidates:
        return None

    # pick longest
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][4]

def infer_fields(layout: Dict[str, Any]) -> List[Dict[str, Any]]:
    page_w = float(layout["page"]["w"])
    texts = layout.get("texts", [])
    lines = layout.get("lines", [])

    fields = []
    for t in texts:
        text = t["text"]
        if not is_label_text(text):
            continue
        lb = bbox_from_list(t["bbox"])
        best_line = pick_value_line_for_label(lb, lines)
        if best_line is None:
            continue

        # value bbox from line x-range and label y-range (a simple but effective choice)
        x1, y1, x2, y2 = map(float, [best_line["x1"], best_line["y1"], best_line["x2"], best_line["y2"]])
        vx0, vx1 = (x1, x2) if x1 <= x2 else (x2, x1)

        value_bbox = [vx0, lb.y0, vx1, lb.y1]

        col = "left" if lb.cx < page_w / 2.0 else "right"

        fields.append({
            "label": normalize_label(text),
            "label_bbox": [lb.x0, lb.y0, lb.x1, lb.y1],
            "value_bbox": value_bbox,
            "col": col
        })

    # sort by reading order: y then x
    fields.sort(key=lambda f: (f["label_bbox"][1], f["label_bbox"][0]))
    return fields

def main():
    with open("layout.json", "r", encoding="utf-8") as f:
        layout = json.load(f)

    fields = infer_fields(layout)

    out = {
        "page": layout["page"],
        "fields": fields
    }

    with open("fields.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Generated fields.json with {len(fields)} fields.")

if __name__ == "__main__":
    main()
