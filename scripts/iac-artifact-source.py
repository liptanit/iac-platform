#!/usr/bin/env python3
"""Validate and plan vCenter datastore artifact sources.

Phase 52 intentionally keeps datastore binary movement as a planned operation.
Validation is live and read-only; copy planning writes evidence without moving
large ISO or installer files.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = REPO / "examples" / "artifact-sources.example.toml"
DEFAULT_EVIDENCE_ROOT = Path("/opt/appserver/backups/iac/phase52_artifact_sources")


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def load_catalog(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"catalog not found: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    artifacts = data.get("artifact", [])
    if isinstance(artifacts, dict):
        artifacts = [artifacts]
    if not isinstance(artifacts, list):
        raise SystemExit("catalog must contain [[artifact]] entries")
    rows: list[dict[str, Any]] = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        row = {
            "id": str(item.get("id", "")).strip(),
            "name": str(item.get("name", "")).strip(),
            "kind": str(item.get("kind", "iso")).strip(),
            "source_vcenter_id": str(item.get("source_vcenter_id", "")).strip(),
            "datastore": str(item.get("datastore", "")).strip(),
            "path": str(item.get("path", "")).strip().lstrip("/"),
            "allowed_roles": [str(role).strip() for role in item.get("allowed_roles", []) if str(role).strip()],
            "sha256": str(item.get("sha256", "")).strip(),
            "active": bool(item.get("active", True)),
        }
        validate_artifact_shape(row)
        rows.append(row)
    return rows


def validate_artifact_shape(row: dict[str, Any]) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{1,62}[a-z0-9]", row["id"]):
        raise SystemExit(f"invalid artifact id: {row['id']}")
    missing = [key for key in ("source_vcenter_id", "datastore", "path") if not row.get(key)]
    if missing:
        raise SystemExit(f"artifact {row['id']} is missing: {', '.join(missing)}")
    if ".." in Path(str(row["path"])).parts:
        raise SystemExit(f"artifact {row['id']} path must not contain parent traversal")


def artifact_by_id(catalog: list[dict[str, Any]], artifact_id: str) -> dict[str, Any]:
    for row in catalog:
        if row["id"] == artifact_id:
            return row
    raise SystemExit(f"artifact not found: {artifact_id}")


def env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name) or os.environ.get(name.lower())
        if value and value.strip():
            return value.strip()
    return ""


def govc_env(prefix: str = "IAC_VCENTER") -> tuple[dict[str, str], dict[str, Any]]:
    host = env_value(f"{prefix}_HOST", f"{prefix}_ENDPOINT")
    endpoint = env_value(f"{prefix}_ENDPOINT")
    if endpoint and "://" in endpoint:
        host = endpoint.split("://", 1)[1].split("/", 1)[0]
    host = host.split(":", 1)[0]
    port = env_value(f"{prefix}_PORT") or "443"
    username = env_value(f"{prefix}_USERNAME")
    password = env_value(f"{prefix}_PASSWORD")
    datacenter = env_value(f"{prefix}_DATACENTER")
    vcenter_id = env_value(f"{prefix}_ID")
    missing = []
    for key, value in {
        f"{prefix}_ID": vcenter_id,
        f"{prefix}_HOST or {prefix}_ENDPOINT": host,
        f"{prefix}_USERNAME": username,
        f"{prefix}_PASSWORD": password,
        f"{prefix}_DATACENTER": datacenter,
    }.items():
        if not value:
            missing.append(key)
    if missing:
        raise SystemExit("missing vCenter runtime environment:\n" + "\n".join(f"- {item}" for item in missing))
    env = os.environ.copy()
    env.update(
        {
            "GOVC_URL": f"https://{host}:{port}",
            "GOVC_USERNAME": username,
            "GOVC_PASSWORD": password,
            "GOVC_INSECURE": "1",
            "GOVC_DATACENTER": datacenter,
        }
    )
    redacted = {
        "prefix": prefix,
        "vcenter_id": vcenter_id,
        "host": host,
        "port": port,
        "username": username,
        "password": "***",
        "datacenter": datacenter,
    }
    return env, redacted


def run(command: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        env=env,
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def require_govc() -> str:
    govc = shutil.which("govc")
    if not govc:
        raise SystemExit("govc was not found")
    return govc


def evidence_dir(root: Path, name: str) -> Path:
    path = root / f"{now_stamp()}_{name}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_evidence(path: Path, name: str, record: dict[str, Any]) -> None:
    (path / f"{name}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# Phase 52 Artifact Source: {record.get('artifact_id', record.get('id', ''))}",
        "",
        f"- Status: `{record.get('status', record.get('overall', 'unknown'))}`",
        f"- Source vCenter: `{record.get('source_vcenter_id', '')}`",
        f"- Source: `[{record.get('datastore', record.get('source_datastore', ''))}] {record.get('path', record.get('source_path', ''))}`",
    ]
    if record.get("destination_vcenter_id"):
        lines.append(f"- Destination: `{record['destination_vcenter_id']}` / `[{record['destination_datastore']}] {record['destination_path']}`")
    if record.get("checks"):
        lines.extend(["", "## Checks", ""])
        lines.extend(f"- `{item['status']}` {item['name']}: {item['detail']}" for item in record["checks"])
    (path / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_list(args: argparse.Namespace) -> int:
    for row in load_catalog(args.catalog):
        print(f"{row['id']}\t{row['kind']}\t{row['source_vcenter_id']}\t[{row['datastore']}] {row['path']}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    artifact = artifact_by_id(load_catalog(args.catalog), args.artifact_id)
    env, redacted = govc_env("IAC_VCENTER")
    runtime_id = redacted["vcenter_id"]
    checks = []
    if runtime_id != artifact["source_vcenter_id"]:
        checks.append(
            {
                "name": "Runtime vCenter",
                "status": "fail",
                "detail": f"runtime {runtime_id} does not match artifact source {artifact['source_vcenter_id']}",
            }
        )
        overall = "failed"
        output = ""
        rc = 2
    else:
        govc = require_govc()
        result = run([govc, "datastore.ls", "-ds", artifact["datastore"], artifact["path"]], env=env)
        output = result.stdout.strip()
        rc = result.returncode
        exists = result.returncode == 0 and bool(output)
        checks.append({"name": "Datastore file", "status": "ok" if exists else "fail", "detail": output or "not found"})
        overall = "ready" if exists else "failed"
    record = {
        **artifact,
        "artifact_id": artifact["id"],
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "overall": overall,
        "runtime": redacted,
        "command_rc": rc,
        "command_output": output,
        "checks": checks,
    }
    out_dir = evidence_dir(args.evidence_root, f"{artifact['id']}_validation")
    write_evidence(out_dir, "validation", record)
    print(json.dumps({"overall": overall, "evidence_dir": str(out_dir)}, indent=2))
    return 0 if overall == "ready" else 2


def cmd_plan_copy(args: argparse.Namespace) -> int:
    artifact = artifact_by_id(load_catalog(args.catalog), args.artifact_id)
    destination_path = (args.destination_path or artifact["path"]).strip().lstrip("/")
    if not args.destination_vcenter_id or not args.destination_datastore:
        raise SystemExit("--destination-vcenter-id and --destination-datastore are required")
    same_location = (
        artifact["source_vcenter_id"] == args.destination_vcenter_id
        and artifact["datastore"] == args.destination_datastore
        and artifact["path"] == destination_path
    )
    checks = [
        {"name": "Source catalog", "status": "ok", "detail": artifact["id"]},
        {"name": "Destination", "status": "fail" if same_location else "ok", "detail": "destination is identical to source" if same_location else args.destination_vcenter_id},
        {"name": "Guardrail", "status": "info", "detail": "dry-run plan only; no datastore file is copied"},
    ]
    record = {
        "artifact_id": artifact["id"],
        "artifact_name": artifact["name"],
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "status": "blocked" if same_location else "planned",
        "source_vcenter_id": artifact["source_vcenter_id"],
        "source_datastore": artifact["datastore"],
        "source_path": artifact["path"],
        "destination_vcenter_id": args.destination_vcenter_id,
        "destination_datastore": args.destination_datastore,
        "destination_path": destination_path,
        "copy_strategy": "cross-vcenter-download-upload" if artifact["source_vcenter_id"] != args.destination_vcenter_id else "same-vcenter-datastore-copy",
        "checks": checks,
    }
    out_dir = evidence_dir(args.evidence_root, f"{artifact['id']}_copy_plan")
    write_evidence(out_dir, "copy-plan", record)
    print(json.dumps({"status": record["status"], "evidence_dir": str(out_dir)}, indent=2))
    return 0 if record["status"] == "planned" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list").set_defaults(func=cmd_list)
    validate = sub.add_parser("validate")
    validate.add_argument("artifact_id")
    validate.set_defaults(func=cmd_validate)
    plan = sub.add_parser("plan-copy")
    plan.add_argument("artifact_id")
    plan.add_argument("--destination-vcenter-id", required=True)
    plan.add_argument("--destination-datastore", required=True)
    plan.add_argument("--destination-path", default="")
    plan.set_defaults(func=cmd_plan_copy)
    args = parser.parse_args()
    print("+ " + " ".join(shlex.quote(item) for item in sys.argv), file=sys.stderr)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
