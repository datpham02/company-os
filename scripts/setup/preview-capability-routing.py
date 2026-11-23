"""Offline, deterministic Task -> Capability Catalog preview. Not an Agent runtime or permission system.

python -I scripts/setup/preview-capability-routing.py --task-type sealwarden-doc-review
python -I scripts/setup/preview-capability-routing.py --task-type pixel-vfx --format markdown
"""
import argparse
import json
from pathlib import Path
import re
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


EXTERNAL_SKILLS_PATH = "config/paperclip/external-skill-candidates.json"


def external_skill_candidates(repo, task_type, role):
    """Curated offline discovery. All external entries remain unapproved references."""
    manifest = read_json(repo, EXTERNAL_SKILLS_PATH)
    if manifest.get("schema") != "external-skill-candidates.v1":
        raise ValueError("unsupported external skills manifest schema")
    sources = {}
    for source in manifest["sources"]:
        sid, sha, name = source["id"], source["commit"], source["repository"]
        if sid in sources or not re.fullmatch(r"[a-f0-9]{40}", sha):
            raise ValueError("duplicate source id or unpinned external source")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
            raise ValueError("external source must be a GitHub owner/repo")
        if source["integration"] != "candidate" or source["mode"] != "harvest_reference_only":
            raise ValueError("external source cannot be activated by preview")
        sources[sid] = source
    seen, results = set(), []
    for skill in manifest["skills"]:
        sid, name, path = skill["source_id"], skill["id"], skill["path"]
        if name in seen or sid not in sources:
            raise ValueError("duplicate skill or unknown source")
        seen.add(name)
        if not re.fullmatch(r"\.claude/skills/[a-z0-9-]+/SKILL\.md", path):
            raise ValueError("untrusted skill source path: " + path)
        if skill["review_state"] not in ("candidate", "deferred"):
            raise ValueError("external skill must remain candidate/deferred")
        if task_type not in skill["task_types"] or role != skill["role"]:
            continue
        source = sources[sid]
        results.append({
            "id": name,
            "status": "CANDIDATE_NOT_ACTIVE" if skill["review_state"] == "candidate" else "DEFERRED_NOT_ACTIVE",
            "proposal": skill["proposal"],
            "value": skill["value"],
            "source": "https://github.com/" + source["repository"] + "/blob/" + source["commit"] + "/" + path,
            "source_commit": source["commit"],
            "license": source["license"],
            "source_file_fetched_at_preview": False,
            "dependencies": skill["dependencies"],
            "blockers": skill["blockers"],
            "migration": skill["migration"],
            "execution_authorized": False,
            "knowledge_delivered": False,
        })
    return results


def block_reason(row, role_status):
    if role_status != "active":
        return "ROLE_NOT_ACTIVE: " + role_status
    reg = row["registered"]["value"].strip().lower()
    if not reg or reg == "no registry entry":
        return "UNREGISTERED_DEPENDENCY"
    if any(": " + s in reg for s in DENIED_REGISTRY_STATES):
        return "DEPENDENCY_NOT_APPROVED"
    installed = row["installed"]["value"].strip().lower()
    if not installed or installed.startswith(("no", "not installed", "unknown", "n/a")):
        return "NOT_INSTALLED: " + (installed or "missing evidence")
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
            "installed": row["installed"],
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
        "external_skill_candidates": external_skill_candidates(repo, task_type, role),
        "knowledge": knowledge,
        "restrictions": spec.get("restrictions", []),
        "execution_authorized": False,
        "notice": "Preview only. No commands run, permissions granted, skills delivered or effective use established.",
    }


def task_block(out):
    lines = ["## Required capabilities (preview — not a permission grant)",
             f"- Task type: `{out['task_type']}`; intended role: `{out['role']}`",
             f"- Catalog source commit: `{out['catalog_source_commit'] or 'unknown'}`",
             "- `execution_authorized: false` — DECLARED_ONLY is not ACCESSIBLE; this preview does not verify or grant runtime access"]
    for cap in out["capabilities"]:
        lines.append(f"- `capability: {cap['id']}` — **{cap['status']}**; {cap['reason']}")
        verified = cap.get("runtime_verified")
        value = verified.get("value") if isinstance(verified, dict) else "not recorded"
        lines.append(f"  - runtime_verified: `{value}`")
    for item in out["knowledge"]:
        state = "SOURCE PRESENT" if item["source_present"] else "SOURCE MISSING"
        lines.append(f"- `read-set: {item['path']}` — {state}, delivery UNVERIFIED")
    for skill in out.get("external_skill_candidates", []):
        lines.append(f"- `external-skill: {skill['id']}` — **{skill['status']}**; "
                     f"{skill['proposal']}; source pinned to {skill['source_commit'][:12]}; "
                     "no import, invocation or skill delivery")
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
