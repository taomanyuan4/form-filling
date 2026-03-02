import json
import os
from typing import Dict, Any, List

from providers.lmstudio_provider import LMStudioProvider


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_filled_values(
    fields: List[Dict[str, Any]],
    raw: Any
) -> Dict[str, Dict[str, Any]]:
    """
    Normalize/validate LLM output to:
      field_id -> {value, confidence, source, need_confirm, reason}
    If a field is missing or malformed, fill with empty + need_confirm=True.
    """
    field_ids = [f["field_id"] for f in fields]

    # LLM might return:
    # 1) direct dict: {field_id: {...}}
    # 2) wrapper: {"filled_values": {...}}  (some provider might do this)
    if isinstance(raw, dict) and "filled_values" in raw and isinstance(raw["filled_values"], dict):
        data = raw["filled_values"]
    elif isinstance(raw, dict):
        data = raw
    else:
        data = {}

    out: Dict[str, Dict[str, Any]] = {}

    for fid in field_ids:
        item = data.get(fid, None)

        if not isinstance(item, dict):
            out[fid] = {
                "value": "",
                "confidence": 0.0,
                "source": "missing_or_invalid",
                "need_confirm": True,
                "reason": "LLM output missing or invalid for this field."
            }
            continue

        value = item.get("value", "")
        # Basic type coercion
        if value is None:
            value = ""
        if not isinstance(value, str):
            value = str(value)

        need_confirm = bool(item.get("need_confirm", False))
        confidence = item.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0

        out[fid] = {
            "value": value,
            "confidence": max(0.0, min(1.0, confidence)),
            "source": item.get("source", "lmstudio"),
            "need_confirm": need_confirm,
            "reason": item.get("reason", "")
        }

    return out


def main():
    # 1) Load template meta (field definitions)
    meta = _load_json("template_meta.json")
    fields: List[Dict[str, Any]] = meta["fields"]

    # 2) Load candidate data (preferred) or fallback to master_record.json
    if os.path.exists("candidate_data.json"):
        candidate_data = _load_json("candidate_data.json")
        data_source = "candidate_data.json"
    else:
        candidate_data = _load_json("master_record.json")
        data_source = "master_record.json"

    # 3) LM Studio config (can override via environment variables)
    base_url = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    model = os.getenv("LMSTUDIO_MODEL", "qwen2.5-7b-instruct")

    llm = LMStudioProvider(base_url=base_url, model=model)

    # 4) Call local LLM
    raw_filled = llm.fill(fields, candidate_data)

    # 5) Normalize/validate output
    filled = _normalize_filled_values(fields, raw_filled)

    # 6) Persist results
    result = {
        "template_id": meta.get("template_id", "unknown"),
        "data_source": data_source,
        "llm_provider": "LMStudioProvider",
        "llm_base_url": base_url,
        "llm_model": model,
        "filled_values": filled
    }

    with open("filled_values.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 7) Quick report
    filled_cnt = sum(1 for v in filled.values() if v.get("value"))
    need_confirm_cnt = sum(1 for v in filled.values() if v.get("need_confirm"))
    print(f"Generated filled_values.json. Filled: {filled_cnt}/{len(fields)}, need_confirm: {need_confirm_cnt}")
    print(f"Data source: {data_source}")
    print(f"LM Studio: {base_url} | model: {model}")


if __name__ == "__main__":
    main()
