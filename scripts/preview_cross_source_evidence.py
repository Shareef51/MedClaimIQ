from __future__ import annotations
import json
from pathlib import Path

seed = json.loads(Path("sample-data/cross_source_evidence_seed.json").read_text())
print("Cross-source evidence query:", seed["query"])
for item in seed["expected_sources"]:
    print(f"- {item['retriever']}: {item['source_type']} -> {item.get('source_id', item.get('relationship'))}")
print("Safety:", seed["expected_behavior"])
