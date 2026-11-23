"""Offline A2/A5 Task capability contract + evidence-ledger preview; never grants access.

python scripts/setup/preview-task-evidence.py --task tests/fixtures/capability-evidence/ui-review.json
python scripts/setup/preview-task-evidence.py --task tests/fixtures/capability-evidence/pixel-vfx.json --evidence tests/fixtures/capability-evidence/pixel-vfx-receipts.json
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ROUTING = "config/paperclip/capability-routing.json"
CATALOG = "config/paperclip/generated/catalog/capability-catalog.json"
STAGES = ("DISCOVERED", "ACCESSED", "READ", "INVOKED", "APPLIED", "REVIEWED")


def safe_path(root, path):
    p = Path(path)
    if not path or p.is_absolute() or ".." in p.parts or "\\" in path:
        raise ValueError("unsafe repository-relative path: " + path)
    absolute = (root / p).resolve()
    if not absolute.is_relative_to(root.resolve()):
        raise ValueError("path escapes checkout: " + path)
    return absolute


def load(root, path):
    return json.loads(safe_path(root, path).read_text(encoding="utf-8-sig"))


def catalog_gate(root):
    # Import policy from THIS checked-out implementation, never the --repo fixture path.
    # User-supplied fixture roots are data only and may contain untrusted Python files.
    module = ROOT / "scripts/setup/preview-capability-routing.py"
    if not module.is_file():
        raise ValueError("canonical router policy missing")
    spec = importlib.util.spec_from_file_location("company_capability_preview", module)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    return policy.block_reason


def validate_task(task, routing):
    if task.get("schema") != "task-capability-input.v1":
        raise ValueError("unsupported task schema")
    if not isinstance(task.get("task_id"), str) or not task["task_id"].strip():
        raise ValueError("task_id required")
    key = task.get("task_type")
    if key not in routing["task_types"]:
        raise ValueError("unknown task type (blocked): " + str(key))
    spec = routing["task_types"][key]
    if task.get("role") != spec["role"]:
        raise ValueError("task role mismatch (blocked)")
    ops = task.get("operations")
    docs = task.get("knowledge")
    for name, items, expected, field in (
        ("operations", ops, spec["operations"], "id"),
        ("knowledge", docs, spec["knowledge"], "path"),
    ):
        if not isinstance(items, list):
            raise ValueError(name + " must be an explicit required/optional list")
        if any(not isinstance(x, dict) or type(x.get("required")) is not bool or
               not isinstance(x.get(field), str) or not x[field] for x in items):
            raise ValueError("invalid " + name + " requirement")
        ids = [x[field] for x in items]
        if len(ids) != len(set(ids)) or set(ids) != set(expected):
            raise ValueError(name + " must list every mapped item exactly once")
    return spec


def parse_evidence(task, evidence):
    if evidence is None:
        return {}
    if evidence.get("schema") != "capability-evidence-reports.v1" or evidence.get("task_id") != task["task_id"]:
        raise ValueError("evidence schema or task ID mismatch")
    known = {"operation:" + x["id"] for x in task["operations"]}
    known.update("knowledge:" + x["path"] for x in task["knowledge"])
    by_key = {}
    for rec in evidence.get("receipts", []):
        if not isinstance(rec, dict):
            raise ValueError("evidence receipt must be a record")
        key = rec.get("item")
        stage = rec.get("stage")
        if key not in known or stage not in STAGES:
            raise ValueError("unknown capability or event stage")
        if not isinstance(rec.get("evidence_ref"), str) or not rec["evidence_ref"].strip():
            raise ValueError("event needs a reference to an observed log / artifact")
        if stage in ("APPLIED", "REVIEWED"):
            if not rec.get("artifact_ref") or not rec.get("criterion"):
                raise ValueError("APPLIED/REVIEWED needs artifact_ref and criterion")
        if (stage == "READ" and not key.startswith("knowledge:")) or (
            stage == "INVOKED" and not key.startswith("operation:")
        ):
            raise ValueError("READ is for knowledge, INVOKED is for operations")
        bucket = by_key.setdefault(key, {})
        if stage in bucket:
            raise ValueError("duplicate stage receipt for " + key)
        bucket[stage] = rec
    return by_key


def review_reports(reports, kind):
    """Records a proposed chain; never attests that an Agent actually performed an action."""
    required = ("DISCOVERED", "ACCESSED", "READ" if kind == "knowledge" else "INVOKED", "APPLIED")
    reported = sorted(reports, key=STAGES.index)
    missing = [s for s in required if s not in reports]
    if "REVIEWED" in reports and "APPLIED" not in reports:
        missing.append("APPLIED_BEFORE_REVIEWED")
    if "APPLIED" in reports and ("READ" if kind == "knowledge" else "INVOKED") not in reports:
        missing.append("READ_OR_INVOKE_BEFORE_APPLIED")
    return {"suggested": True,
            "reported_stages": reported,
            "missing_chain_stages": sorted(set(missing)),
            "references": {s: {"evidence_ref": r["evidence_ref"],
                              "artifact_ref": r.get("artifact_ref"),
                              "criterion": r.get("criterion")}
                           for s, r in reports.items()},
            "report_verification": "UNVERIFIED (references are assertions, not validated reads/logs)",
            "effective_use": "UNVERIFIED (requires independent outcome review)",
            "claim_complete": not missing,
            }


def resolve(root, task, evidence=None):
    routing, catalog = load(root, ROUTING), load(root, CATALOG)
    if routing.get("schema") != "capability-routing.v1" or catalog.get("schema") != "capability-catalog.v1":
        raise ValueError("unsupported routing or catalog")
    spec = validate_task(task, routing)
    receipt_map = parse_evidence(task, evidence)
    role_info = catalog["roles"].get(spec["role"])
    if role_info is None:
        raise ValueError("role not in catalog")
    gate = catalog_gate(root)
    operations = {x["operation"]: x for x in role_info["operations"]}
    results, required_blockers = [], []
    for declared in task["operations"]:
        item = declared["id"]
        row = operations.get(item)
        reason = "NOT_IN_ROLE_CATALOG" if row is None else gate(row, role_info["status"])
        state = "BLOCKED" if reason else "DECLARED_ONLY"
        # Static records are a catalog snapshot, never a live Agent session.
        stages = {
            "REGISTERED": {"status": "CATALOG_DECLARED" if row and row["registered"]["value"].strip().lower() != "no registry entry" else "NOT_REGISTERED",
                           "evidence": row.get("registered") if row else None},
            "INSTALLED": {"status": "CATALOG_DECLARED" if row and row["installed"]["value"].strip().lower().startswith(("yes", "verified version:")) else "NOT_VERIFIED",
                          "evidence": row.get("installed") if row else None},
            "DISCOVERABLE": "UNVERIFIED", "ACCESSIBLE": "UNVERIFIED",
            "INVOKED": "UNVERIFIED", "EFFECTIVELY_USED": "UNVERIFIED",
        }
        ref = "operation:" + item
        results.append({"kind": "operation", "id": item, "required": declared["required"],
                        "catalog_status": state, "blocker": reason,
                        "stages": stages, "agent_delivery": "UNVERIFIED",
                        "usage": review_reports(receipt_map.get(ref, {}), "operation")})
        if reason and declared["required"]:
            required_blockers.append(ref + ": " + reason)
    for declared in task["knowledge"]:
        path = declared["path"]
        exists = safe_path(root, path).is_file()
        reason = None if exists else "SOURCE_MISSING"
        ref = "knowledge:" + path
        results.append({"kind": "knowledge", "id": path, "required": declared["required"],
                        "catalog_status": "SOURCE_PRESENT_ONLY" if exists else "BLOCKED",
                        "blocker": reason, "stages": {
                            "REGISTERED": "NOT_APPLICABLE (knowledge file, not a tool registry entry)",
                            "INSTALLED": "NOT_APPLICABLE (file presence is not an installation)",
                            "DISCOVERABLE": "UNVERIFIED", "ACCESSIBLE": "UNVERIFIED",
                            "INVOKED": "NOT_APPLICABLE (knowledge requires a read receipt)",
                            "READ": "UNVERIFIED", "EFFECTIVELY_USED": "UNVERIFIED",
                        }, "source_present": exists, "agent_delivery": "UNVERIFIED",
                        "usage": review_reports(receipt_map.get(ref, {}), "knowledge")})
        if reason and declared["required"]:
            required_blockers.append(ref + ": " + reason)
    return {"schema": "capability-task-evidence-preview.v1", "task_id": task["task_id"],
            "task_type": task["task_type"], "role": task["role"],
            "requirements": results, "required_blockers": required_blockers,
            "readiness": "BLOCKED" if required_blockers else "PREVIEW_ONLY",
            "catalog_source_commit": catalog.get("source_commit"),
            "execution_authorized": False, "agent_invocation_verified": False,
            "effectiveness_verified": False,
            "notice": "Offline contract only; reports are NOT verified. No Agent run, access, read, invocation or effective use is inferred."}


def markdown(result):
    lines = ["## Required capabilities (offline A2/A5 preview)",
             f"- Task: `{result['task_id']}`; role: `{result['role']}`; readiness: `{result['readiness']}`"]
    for x in result["requirements"]:
        label = "REQUIRED" if x["required"] else "OPTIONAL"
        lines.append(f"- `{x['kind']}: {x['id']}` — {label}, **{x['catalog_status']}**, "
                     f"reason: {x['blocker'] or 'no static blocker'}; delivery UNVERIFIED")
        lines.append("  - Usage receipts: " + (", ".join(x["usage"]["reported_stages"]) or "none") +
                     "; **unverified**, effective use UNVERIFIED")
    lines.append("- Required blockers: " + (", ".join(result["required_blockers"]) or "none; runtime still NOT authorized"))
    lines.append("- Agent must independently validate access, record read/invocation and applied criteria; no auto-promotion.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--task", required=True, help="repo-relative Task Contract fixture JSON")
    p.add_argument("--evidence", help="repo-relative unverified evidence receipt file")
    p.add_argument("--format", choices=("json", "markdown"), default="json")
    args = p.parse_args(argv)
    try:
        root = args.repo.resolve()
        result = resolve(root, load(root, args.task), load(root, args.evidence) if args.evidence else None)
    except (OSError, ValueError, KeyError, TypeError) as err:
        print("capability-evidence: " + str(err), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.format == "json" else markdown(result),
          end="\n" if args.format == "json" else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())