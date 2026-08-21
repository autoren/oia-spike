from __future__ import annotations

import json
from pathlib import Path

from ontology_auditor.io import audit_payload, load_payload


HERE = Path(__file__).resolve().parent


for filename in (
    "pilot_instance.json",
    "alias_impossibility.json",
    "delayed_separator.json",
    "task_loss_tradeoff.json",
):
    report = audit_payload(load_payload(HERE / filename))
    output = HERE / filename.replace(".json", ".report.json")
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output.name}")
