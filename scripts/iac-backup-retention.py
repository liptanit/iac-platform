#!/usr/bin/env python3
"""IaC backup retention reporter and safe cleanup helper.

Default mode is dry-run. With --apply, candidates are moved into a trash
folder under the backup root instead of being deleted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any


DEFAULT_BACKUP_ROOT = Path("/opt/appserver/backups/iac")


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def item_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def classify(path: Path) -> str:
    name = path.name
    if name.startswith("phase11_"):
        return "operations"
    if name.startswith("phase13_prechecks"):
        return "prechecks"
    if name.startswith("phase14_"):
        return "approvals-launches"
    if name.startswith("phase43_monitoring_validation"):
        return "monitoring"
    if name.startswith("phase47_evidence_bundles"):
        return "evidence-bundles"
    if name.endswith(".tgz"):
        return "archive"
    return "phase-evidence"


def collect_candidates(backup_root: Path, older_than_days: int, keep_recent: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cutoff = now() - dt.timedelta(days=older_than_days)
    rows: list[dict[str, Any]] = []
    for path in backup_root.iterdir():
        if path.name.startswith("phase49_retention_"):
            continue
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        modified = dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.timezone.utc)
        rows.append(
            {
                "path": path,
                "name": path.name,
                "kind": "file" if path.is_file() else "dir",
                "class": classify(path),
                "modified": modified,
                "age_days": max(0, (now() - modified).days),
                "size_bytes": item_size(path),
            }
        )
    rows.sort(key=lambda item: item["modified"], reverse=True)
    protected = rows[:keep_recent]
    protected_paths = {item["path"] for item in protected}
    candidates = [item for item in rows if item["path"] not in protected_paths and item["modified"] < cutoff]
    return candidates, protected


def write_report(report_dir: Path, candidates: list[dict[str, Any]], protected: list[dict[str, Any]], applied: bool, trash_dir: Path | None) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": now().isoformat(timespec="seconds"),
        "applied": applied,
        "trash_dir": str(trash_dir) if trash_dir else "",
        "candidate_count": len(candidates),
        "candidate_bytes": sum(item["size_bytes"] for item in candidates),
        "protected_recent_count": len(protected),
        "candidates": [
            {
                "path": str(item["path"]),
                "kind": item["kind"],
                "class": item["class"],
                "modified": item["modified"].isoformat(timespec="seconds"),
                "age_days": item["age_days"],
                "size_bytes": item["size_bytes"],
            }
            for item in candidates
        ],
        "protected_recent": [
            {
                "path": str(item["path"]),
                "kind": item["kind"],
                "class": item["class"],
                "modified": item["modified"].isoformat(timespec="seconds"),
                "age_days": item["age_days"],
                "size_bytes": item["size_bytes"],
            }
            for item in protected
        ],
    }
    (report_dir / "retention-report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# IaC Backup Retention Report",
        "",
        f"- Applied: `{applied}`",
        f"- Trash dir: `{trash_dir or '-'}`",
        f"- Candidate count: `{len(candidates)}`",
        f"- Candidate bytes: `{sum(item['size_bytes'] for item in candidates)}`",
        f"- Protected recent count: `{len(protected)}`",
        "",
        "## Candidates",
        "",
    ]
    if candidates:
        for item in candidates:
            lines.append(f"- `{item['path']}` ({item['class']}, {item['age_days']}d, {item['size_bytes']} bytes)")
    else:
        lines.append("- none")
    (report_dir / "retention-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def move_to_trash(candidates: list[dict[str, Any]], trash_dir: Path) -> None:
    trash_dir.mkdir(parents=True, exist_ok=True)
    for item in candidates:
        source = item["path"]
        target = trash_dir / source.name
        if target.exists():
            suffix = dt.datetime.now(dt.timezone.utc).strftime("%H%M%S")
            target = trash_dir / f"{source.name}.{suffix}"
        shutil.move(str(source), str(target))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    parser.add_argument("--older-than-days", type=int, default=30)
    parser.add_argument("--keep-recent", type=int, default=80)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--apply", action="store_true", help="Move candidates to a trash folder. Default is dry-run.")
    args = parser.parse_args()

    if args.older_than_days < 1:
        raise SystemExit("--older-than-days must be at least 1")
    if args.keep_recent < 0:
        raise SystemExit("--keep-recent must be 0 or greater")
    if not args.backup_root.exists():
        raise SystemExit(f"backup root not found: {args.backup_root}")

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_dir = args.report_dir or args.backup_root / f"phase49_retention_report_{stamp}"
    candidates, protected = collect_candidates(args.backup_root, args.older_than_days, args.keep_recent)
    trash_dir = args.backup_root / f"phase49_retention_trash_{stamp}" if args.apply else None
    if args.apply and trash_dir:
        move_to_trash(candidates, trash_dir)
    write_report(report_dir, candidates, protected, args.apply, trash_dir)
    print(f"report_dir={report_dir}")
    print(f"applied={args.apply}")
    print(f"candidate_count={len(candidates)}")
    print(f"candidate_bytes={sum(item['size_bytes'] for item in candidates)}")
    if trash_dir:
        print(f"trash_dir={trash_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
