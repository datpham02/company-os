"""Offline, deterministic Task -> Capability Catalog preview. Not an Agent runtime or permission system.

python -I scripts/setup/preview-capability-routing.py --task-type sealwarden-doc-review
python -I scripts/setup/preview-capability-routing.py --task-type pixel-vfx --format markdown
"""
import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
ROUTING_PATH = "config/paperclip/capability-routing.json"
CATALOG_PATH = "config/paperclip/generated/catalog/capability-catalog.json"
DENIED_REGISTRY_STATES = ("candidate", "evaluating", "rejected")


def safe_file(repo, name):
    """Only relative, in-repository paths supplied by the trusted routing manifest."""
    p = Path(name)
    if p.is_absolute() or ".." in p.parts or not name or "\\" in name:
        raise ValueError("routing path must be repository-relative: " + name)
    result = (repo / p).resolve()
    if not result.is_relative_to(repo.resolve()):
        raise ValueError("routing path escapes repository: " + name)
    return result


def read_json(repo, path):
    return json.loads(safe_file(repo, path).read_text(encoding="utf-8-sig"))


def block_reason(row, role_status):
    if role_status != "active":
        return "ROLE_NOT_ACTIVE: " + role_status
    reg = row["registered"]["value"].lower()
    if any(": " + s in reg for s in DENIED_REGISTRY_STATES):
        return "DEPENDENCY_NOT_APPROVED"
    appr = row["approved"]["value"].strip().lower()
    if not appr or appr.startswith(("no ", "no (", "unknown", "open:", "n/a")):
        return "OPERATION_NOT_APPROVED"
    perm = row["permitted"]["value"]
    if perm != "declared match (not runtime authorization)":
        return "NO_ENFORCED_PERMISSION: " + perm
    if row["kind"] != "bash":
        return "NON_BASH_OPERATION_REQUIRES_SEPARATE_REVIEW"
    return None


def resolve(repo, task_type):
    """Never issues commands or asserts that the Agent received knowledge."""
    routing = read_json(repo, ROUTING_PATH)
    catalog = read_json(repo, CATALOG_PATH)
    if routing.get("schema") != "capability-routing.v1" or catalog.get("schema") != "capability-catalog.v1":
        raise ValueError("unsupported routing/catalog schema")
    if task_type not in routing["task_types"]:
        raise ValueError("unknown task type: " + task_type)
    spec = routing["task_types"][task_type]
    role = spec["role"]
    if role not in catalog["roles"]:
        raise ValueError("role not in catalog: " + role)
    info = catalog["roles"][role]
    rows = {x["operation"]: x for x in info["operations"]}
    caps = []
    for operation in spec["operations"]:
        if operation not in rows:
            caps.append({"id": operation, "status": "BLOCKED", "reason": "NOT_IN_ROLE_CATALOG"})
            continue
        row = rows[operation]
        reason = block_reason(row, info["status"])
        caps.append({
            "id": operation,
            "status": "BLOCKED" if reason else "DECLARED_ONLY",
            "reason": reason or "Approval and allow rule are declared only; runtime access and task authorization NOT verified",
            "source": "config/paperclip/generated/catalog/capability-catalog.json#roles/" + role + "/operations/" + operation,
            "sample": row.get("sample"),
            "approved": row["approved"],
            "permitted": row["permitted"],
            "registered": row["registered"],
            "runtime_verified": row["runtime_verified"],
            "production_validated": row["production_validated"],
        })
    knowledge = [{"path": name, "source_present": safe_file(repo, name).is_file(),
                  "agent_delivery": "UNVERIFIED (no KD deployment or Agent read evidence)"}
                 for name in spec["knowledge"]]
    return {
        "schema": "capability-routing-preview.v1",
        "task_type": task_type,
        "role": role,
        "role_status": info["status"],
        "catalog_source_commit": catalog.get("source_commit"),
        "capabilities": caps,
        "knowledge": knowledge,
        "restrictions": spec.get("restrictions", []),
        "execution_authorized": False,
        "notice": "Preview only. No commands run, permissions granted, skills delivered or effective use established.",
    }


def task_block(out):
    lines = ["## Required capabilities (preview — not a permission grant)",
             f"- Task type: `{out['task_type']}`; intended role: `{out['role']}`",
             f"- Catalog source commit: `{out['catalog_source_commit'] or 'unknown'}`"]
    for cap in out["capabilities"]:
        lines.append(f"- `capability: {cap['id']}` — **{cap['status']}**; {cap['reason']}")
    for item in out["knowledge"]:
        state = "SOURCE PRESENT" if item["source_present"] else "SOURCE MISSING"
        lines.append(f"- `read-set: {item['path']}` — {state}, delivery UNVERIFIED")
    if out["restrictions"]:
        lines.append("- Restrictions: " + ", ".join(out["restrictions"]))
    lines += ["- Agent must independently verify access and permission before use; log actual read/invoke/application evidence.",
              "- If blocked/unavailable, report the exact blocker; never improvise another tool."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", type=Path, default=REPO, help="checkout root")
    p.add_argument("--task-type", required=True)
    p.add_argument("--format", choices=("json", "markdown"), default="json")
    args = p.parse_args(argv)
    try:
        out = resolve(args.repo.resolve(), args.task_type)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("capability-routing: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2) if args.format == "json" else task_block(out), end="\n" if args.format == "json" else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
