from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = ROOT / "models" / "model_metadata.json"
    t = ROOT / "models" / "text_metrics.json"
    if not p.exists():
        print("Run train_burnout_model.py first")
        return
    meta = json.loads(p.read_text())
    tm = json.loads(t.read_text()) if t.exists() else {}
    print("Burnout RF test", meta.get("test_metrics", {}).get("accuracy"), meta.get("test_metrics", {}).get("f1_macro"))
    print("HIGH recall", meta.get("test_metrics", {}).get("recall_high"))
    print("Text F1", tm.get("f1_macro"))
    print("Semantic", meta.get("semantic_backend"))


if __name__ == "__main__":
    main()
