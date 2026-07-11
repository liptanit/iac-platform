#!/usr/bin/env python3
"""Phase 11 IaC operations wrapper.

This command is the operator-facing entry point for create/change/destroy work.
It adds an evidence folder, state/config backup, and an explicit approval gate
before delegating to the proven Windows/Linux rollout runners.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
DEFAULT_BACKUP_ROOT = Path("/opt/appserver/backups/iac")
STATE_GLOBS = [
    "opentofu/environments/*/terraform.tfstate",
    "opentofu/environments/*/terraform.tfstate.backup",
    "opentofu/environments/*/.terraform/terraform.tfstate",
    "opentofu/environments/*/*.tfvars",
    "opentofu/environments/*/*.tfvars.example",
    "ansible/inventories/**/*.ini",
    "examples/*.toml",
    "examples/*.yml",
    "ops/**/*.toml",
]


def now_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


def run(
    command: list[str],
    *,
    cwd: Path = REPO,
    env: dict[str, str] | None = None,
    log: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    rendered = " ".join(shlex.quote(part) for part in command)
    print(f"+ {rendered}", flush=True)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if log:
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n$ {rendered}\n")
            handle.write(completed.stdout)
            if completed.stdout and not completed.stdout.endswith("\n"):
                handle.write("\n")
            handle.write(f"[exit={completed.returncode}]\n")
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if check and completed.returncode != 0:
        raise SystemExit(f"command failed with exit {completed.returncode}: {rendered}")
    return completed


def load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing file: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def rel_path(path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else REPO / value


def runtime_vcenter_id() -> str:
    return (os.environ.get("iac_vcenter_id") or os.environ.get("IAC_VCENTER_ID") or "").strip()


def scoped_inventory_path(env_name: str, platform: str, vcenter_id: str) -> Path | None:
    if not vcenter_id:
        return None
    candidate = REPO / "ops" / "inventories" / env_name / f"{platform}-{vcenter_id}.toml"
    return candidate if candidate.exists() else None


def scoped_state_key(env_name: str, platform: str, vcenter_id: str, config_path: Path) -> str:
    scoped = scoped_inventory_path(env_name, platform, vcenter_id)
    if scoped and scoped.resolve() == config_path.resolve():
        return f"{env_name}_{platform}_{vcenter_id}"
    return ""


def scoped_state_path(platform: str, state_key: str) -> Path | None:
    if not state_key:
        return None
    state_root = "windows-lab" if platform == "windows" else "lab"
    return Path("/opt/appserver/data/iac/state") / state_root / state_key / "terraform.tfstate"


def git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short=12", "HEAD"],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.stdout.strip() or "unknown"


def approval_token(*, env_name: str, platform: str, action: str, config_path: Path, head: str) -> str:
    material = f"{env_name}|{platform}|{action}|{config_path}|{head}|iac-phase11"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12].upper()
    return f"APPROVE-{env_name.upper()}-{platform.upper()}-{action.upper()}-{digest}"


def require_approval(args: argparse.Namespace, profile: dict[str, Any], config_path: Path, head: str) -> None:
    if args.action not in {"apply", "destroy"}:
        return
    expected = approval_token(
        env_name=args.env,
        platform=args.platform,
        action=args.action,
        config_path=config_path,
        head=head,
    )
    if args.approval_token != expected or not args.approved_by:
        raise SystemExit(
            "\n".join(
                [
                    f"{args.action} requires explicit approval.",
                    f"Expected token: {expected}",
                    "Rerun with:",
                    f"  --approved-by <name> --approval-token {expected}",
                ]
            )
        )
    allowed_actions = set(profile.get("allowed_actions", []))
    if args.action not in allowed_actions:
        raise SystemExit(f"profile {args.env} does not allow action {args.action}")


def backup_state_and_config(operation_dir: Path, config_path: Path) -> Path:
    backup_dir = operation_dir / "prechange-backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for pattern in STATE_GLOBS:
        for source in REPO.glob(pattern):
            if source.is_file():
                target = backup_dir / source.relative_to(REPO)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied.append(str(source.relative_to(REPO)))
    if config_path.exists() and config_path.is_file():
        target = backup_dir / "selected-inventory" / config_path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_path, target)
    manifest = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repo": str(REPO),
        "selected_inventory": str(config_path),
        "files": copied,
    }
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    archive = operation_dir / "prechange-backup.tgz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(backup_dir, arcname="prechange-backup")
    return archive


def write_operation_summary(
    *,
    operation_dir: Path,
    args: argparse.Namespace,
    profile_path: Path,
    config_path: Path,
    backup_archive: Path,
    head: str,
    token: str,
    command: list[str],
    exit_code: int,
    vcenter_id: str = "",
    state_key: str = "",
) -> Path:
    apply_token = approval_token(
        env_name=args.env,
        platform=args.platform,
        action="apply",
        config_path=config_path,
        head=head,
    )
    destroy_token = approval_token(
        env_name=args.env,
        platform=args.platform,
        action="destroy",
        config_path=config_path,
        head=head,
    )
    summary = operation_dir / "phase11-operation-summary.md"
    summary.write_text(
        "\n".join(
            [
                "# Phase 11 IaC Operation Summary",
                "",
                f"- Environment: `{args.env}`",
                f"- Platform: `{args.platform}`",
                f"- Action: `{args.action}`",
                f"- Git HEAD: `{head}`",
                f"- Profile: `{profile_path}`",
                f"- Inventory: `{config_path}`",
                f"- vCenter ID: `{vcenter_id or ''}`",
                f"- State key: `{state_key or 'default'}`",
                f"- Approved by: `{args.approved_by or ''}`",
                f"- Approval token: `{args.approval_token or ''}`",
                f"- Approval token for this action: `{token}`",
                f"- Apply approval token for this commit/config: `{apply_token}`",
                f"- Destroy approval token for this commit/config: `{destroy_token}`",
                f"- Pre-change backup: `{backup_archive}`",
                f"- Command log: `{operation_dir / 'phase11-commands.log'}`",
                f"- Runner command: `{' '.join(shlex.quote(part) for part in command)}`",
                f"- Exit code: `{exit_code}`",
                "",
                "## Notes",
                "",
                "- State, generated tfvars, inventories, environment profiles, and selected inventory were backed up before the runner started.",
                "- Apply and destroy require both `--approved-by` and the exact approval token printed by a plan or by the failed approval gate.",
                "- Destroy remains blocked unless the environment profile allows it and `--allow-destroy` is also supplied.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return summary


def archive_operation(operation_dir: Path) -> Path:
    archive = operation_dir.with_suffix(".tgz")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(operation_dir, arcname=operation_dir.name)
    return archive


def build_runner_command(args: argparse.Namespace, profile: dict[str, Any], config_path: Path, operation_dir: Path) -> list[str]:
    if args.platform == "windows":
        command = [str(REPO / "scripts" / "run-windows-rollout.py"), "--config", str(config_path)]
        if args.action == "apply":
            command.append("--apply")
        elif args.action == "validate":
            command.append("--validate-only")
        elif args.action == "destroy":
            raise SystemExit("destroy is not implemented for Windows through the rollout runner yet")
        if args.report and args.action != "plan":
            command.append("--report")
        if args.postclone:
            command.append("--postclone")
        if args.postclone_vars:
            command.extend(["--postclone-vars", str(args.postclone_vars)])
        command.extend(["--report-dir", str(operation_dir / "runner-report")])
        state_key = getattr(args, "state_key", "")
        if state_key:
            command.extend(["--state-key", state_key])
        return command

    if args.platform == "linux":
        command = [str(REPO / "scripts" / "run-linux-rollout.py"), "--config", str(config_path)]
        if args.action == "apply":
            command.append("--apply")
        elif args.action == "validate":
            command.append("--validate-only")
        elif args.action == "destroy":
            raise SystemExit("destroy is not implemented for Linux through the rollout runner yet")
        if args.report and args.action != "plan":
            command.append("--report")
        state_key = getattr(args, "state_key", "")
        state_path = scoped_state_path(args.platform, state_key)
        scoped_state_exists = bool(state_path and state_path.exists())
        if args.skip_precheck or scoped_state_exists or (profile.get("linux_skip_precheck", False) and not state_key):
            command.append("--skip-precheck")
        if args.action == "plan":
            command.append("--skip-seed-upload")
        command.extend(["--report-dir", str(operation_dir / "runner-report")])
        if state_key:
            command.extend(["--state-key", state_key])
        return command

    raise SystemExit(f"unsupported platform: {args.platform}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply", "validate", "destroy"])
    parser.add_argument("--env", default="prod", help="Operations profile name under ops/environments.")
    parser.add_argument("--platform", choices=["windows", "linux"], required=True)
    parser.add_argument("--config", type=Path, default=None, help="Override inventory path from the environment profile.")
    parser.add_argument("--approved-by", default="")
    parser.add_argument("--approval-token", default="")
    parser.add_argument("--allow-destroy", action="store_true")
    parser.add_argument("--allow-disabled-profile", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--postclone", action="store_true")
    parser.add_argument("--postclone-vars", type=Path, default=None)
    parser.add_argument("--skip-precheck", action="store_true", help="Skip rollout prechecks for already-managed inventories.")
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    args = parser.parse_args()

    profile_path = REPO / "ops" / "environments" / f"{args.env}.toml"
    profile = load_toml(profile_path)
    if not profile.get("enabled", False) and not args.allow_disabled_profile:
        raise SystemExit(f"profile {args.env} is disabled; pass --allow-disabled-profile only for dry lab testing")

    default_config_key = f"{args.platform}_inventory"
    vcenter_id = runtime_vcenter_id()
    scoped_config = scoped_inventory_path(args.env, args.platform, vcenter_id)
    if args.config:
        config_path = args.config if args.config.is_absolute() else REPO / args.config
    elif scoped_config:
        config_path = scoped_config
    elif default_config_key in profile:
        config_path = rel_path(str(profile[default_config_key]))
    else:
        raise SystemExit(f"profile {args.env} has no {default_config_key}")

    head = git_head()
    args.vcenter_id = vcenter_id
    args.state_key = scoped_state_key(args.env, args.platform, vcenter_id, config_path)
    token = approval_token(
        env_name=args.env,
        platform=args.platform,
        action=args.action,
        config_path=config_path,
        head=head,
    )
    require_approval(args, profile, config_path, head)
    if args.action == "destroy" and not args.allow_destroy:
        raise SystemExit("destroy requires --allow-destroy in addition to the approval token")

    operation_dir = args.backup_root / f"phase11_{args.env}_{args.platform}_{args.action}_{now_stamp()}"
    operation_dir.mkdir(parents=True, exist_ok=True)
    log = operation_dir / "phase11-commands.log"
    backup_archive = backup_state_and_config(operation_dir, config_path)

    if args.action == "plan":
        runner_action = argparse.Namespace(**vars(args))
        runner_action.action = "plan"
        command = build_runner_command(runner_action, profile, config_path, operation_dir)
    else:
        command = build_runner_command(args, profile, config_path, operation_dir)

    result = run(command, log=log, check=False)
    summary = write_operation_summary(
        operation_dir=operation_dir,
        args=args,
        profile_path=profile_path,
        config_path=config_path,
        backup_archive=backup_archive,
        head=head,
        token=token,
        command=command,
        exit_code=result.returncode,
        vcenter_id=vcenter_id,
        state_key=args.state_key,
    )
    archive = archive_operation(operation_dir)
    print(f"wrote {summary}")
    print(f"archived {archive}")
    if args.action == "plan":
        print(f"approval token for apply: {approval_token(env_name=args.env, platform=args.platform, action='apply', config_path=config_path, head=head)}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
