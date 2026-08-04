from pathlib import Path
import json, re, sys
root=Path(__file__).resolve().parents[1]
required=["README.md","TASKS.md","STATUS.md","SESSION_STATE.md","pyproject.toml","docker-compose.yml","prompts/WORKSPACE_AUDIT.md","prompts/GlobalEngineeringContract.md"]
missing=[p for p in required if not (root/p).exists()]
if missing: raise SystemExit(f"missing: {missing}")
json.loads((root/"data/fixtures/sample_observation.json").read_text())
prompts=[p for p in (root/"prompts").glob("*.md") if p.name[:3] in ({f"E{i:02d}" for i in range(1,3)}|{f"S{i:02d}" for i in range(1,21)}|{f"C{i:02d}" for i in range(1,3)})]
ids={p.name.split("_")[0] for p in prompts}
expected={f"E{i:02d}" for i in range(1,3)}|{f"S{i:02d}" for i in range(1,21)}|{f"C{i:02d}" for i in range(1,3)}
if ids != expected: raise SystemExit(f"prompt id mismatch: {sorted(expected-ids)} {sorted(ids-expected)}")
print("structure validation passed")
