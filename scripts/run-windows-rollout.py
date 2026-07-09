#!/usr/bin/env python3
"""Run the controlled Windows VM rollout workflow.

The workflow is intentionally conservative:
- generates OpenTofu tfvars and Ansible inventory from one TOML file
- validates and plans before any apply
- blocks destroy actions unless explicitly allowed
- applies only when --apply is provided
- runs WinRM and baseline validation only after apply, unless --validate-only is used
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[1]
WINDOWS_ENV = REPO / "opentofu" / "environments" / "windows-lab"
DEFAULT_TFVARS = WINDOWS_ENV / "windows.auto.tfvars"
DEFAULT_INVENTORY = REPO / "ansible" / "inventories" / "windows" / "hosts.ini"
DEFAULT_REPORT_ROOT = Path("/opt/appserver/backups/iac")
ANSIBLE = Path("/opt/appserver/venv-iac-ansible/bin/ansible-playbook")


def now_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            env[key] = value
    return env


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


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"missing {label}: {path}")


def inventory_names(config: Path) -> list[str]:
    data = tomllib.loads(config.read_text(encoding="utf-8"))
    vms = data.get("vm", [])
    names: list[str] = []
    for item in vms:
        if "name" not in item:
            raise SystemExit("inventory entry missing name")
        names.append(str(item["name"]))
    if not names:
        raise SystemExit("inventory has no [[vm]] entries")
    return names


def plan_has_destroy(plan_text: str) -> bool:
    destroy_patterns = [
        r"Plan: \d+ to add, \d+ to change, [1-9]\d* to destroy",
        r"-/+",
        r"will be destroyed",
    ]
    return any(re.search(pattern, plan_text) for pattern in destroy_patterns)


def write_report(report: Path, lines: Iterable[str]) -> None:
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ansible_playbook(
    playbook: str,
    *,
    env: dict[str, str],
    log: Path,
    report_dir: Path,
    extra_args: list[str] | None = None,
) -> None:
    command = [
        str(ANSIBLE),
        "-i",
        str(DEFAULT_INVENTORY),
        str(REPO / "ansible" / "playbooks" / playbook),
        "-e",
        f"windows_report_dir={report_dir / 'host-reports'}",
    ]
    if extra_args:
        command.extend(extra_args)
    run(command, env=env, log=log)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="Windows VM TOML inventory.")
    parser.add_argument("--apply", action="store_true", help="Run tofu apply after an approved plan.")
    parser.add_argument("--validate-only", action="store_true", help="Skip OpenTofu and run WinRM/Ansible validation only.")
    parser.add_argument("--postclone", action="store_true", help="Run post-clone production baseline playbook after apply or with --validate-only.")
    parser.add_argument("--postclone-vars", type=Path, default=None, help="Optional Ansible vars YAML for post-clone policy.")
    parser.add_argument("--report", action="store_true", help="Write per-host JSON validation reports.")
    parser.add_argument("--allow-destroy", action="store_true", help="Allow plans that include destroy actions.")
    parser.add_argument("--skip-shell-validation", action="store_true", help="Skip Windows shell crash validation.")
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--iac-env", type=Path, default=Path("/opt/appserver/config/iac/iac.env"))
    parser.add_argument("--vcenter-env", type=Path, default=Path("/opt/appserver/config/iac/vcenter.env"))
    parser.add_argument("--ansible-env", type=Path, default=Path("/opt/appserver/config/iac/windows-ansible.env"))
    args = parser.parse_args()

    require_file(args.config, "Windows VM inventory")
    require_file(args.iac_env, "IaC env file")
    if args.postclone_vars:
        require_file(args.postclone_vars, "post-clone vars file")
    if (args.postclone or args.report) and not (args.apply or args.validate_only):
        raise SystemExit("--postclone and --report run only with --apply or --validate-only")
    if not args.validate_only:
        require_file(args.vcenter_env, "vCenter env file")
    require_file(args.ansible_env, "Windows Ansible env file")

    report_dir = args.report_dir or DEFAULT_REPORT_ROOT / f"phase9_windows_rollout_{now_stamp()}"
    report_dir.mkdir(parents=True, exist_ok=True)
    log = report_dir / "phase9-commands.log"
    report = report_dir / "phase9-summary.md"

    vm_names = inventory_names(args.config)
    env = os.environ.copy()
    env.update(load_env_file(args.iac_env))
    env.update(load_env_file(args.vcenter_env))
    env.update(load_env_file(args.ansible_env))

    run([
        str(REPO / "scripts" / "generate-windows-tfvars.py"),
        "--config",
        str(args.config),
        "--output",
        str(DEFAULT_TFVARS),
        "--create-vm",
    ], log=log)
    run([
        str(REPO / "scripts" / "generate-windows-ansible-inventory.py"),
        "--config",
        str(args.config),
        "--output",
        str(DEFAULT_INVENTORY),
    ], log=log)

    plan_exit = None
    if not args.validate_only:
        run(["tofu", "fmt", "-check", "-recursive"], cwd=REPO, log=log)
        run(["tofu", "init", "-input=false"], cwd=WINDOWS_ENV, env=env, log=log)
        run(["tofu", "validate"], cwd=WINDOWS_ENV, env=env, log=log)
        plan = run(
            ["tofu", "plan", "-input=false", "-detailed-exitcode", "-no-color", "-out", str(report_dir / "windows.tfplan")],
            cwd=WINDOWS_ENV,
            env=env,
            log=log,
            check=False,
        )
        plan_exit = plan.returncode
        if plan_exit not in (0, 2):
            raise SystemExit(f"tofu plan failed with exit {plan_exit}")
        if plan_has_destroy(plan.stdout) and not args.allow_destroy:
            raise SystemExit("plan includes destroy action; rerun with --allow-destroy only after explicit approval")
        if args.apply:
            run(["tofu", "apply", "-input=false", "-auto-approve", str(report_dir / "windows.tfplan")], cwd=WINDOWS_ENV, env=env, log=log)

    should_validate = args.apply or args.validate_only
    if should_validate:
        ansible_playbook("ping-windows.yml", env=env, log=log, report_dir=report_dir)
        ansible_playbook("baseline-windows.yml", env=env, log=log, report_dir=report_dir)
        if args.postclone:
            extra_args = ["-e", f"@{args.postclone_vars}"] if args.postclone_vars else None
            ansible_playbook("postclone-windows.yml", env=env, log=log, report_dir=report_dir, extra_args=extra_args)
        if not args.skip_shell_validation:
            ansible_playbook("validate-windows-shell.yml", env=env, log=log, report_dir=report_dir)
        if args.report:
            ansible_playbook("report-windows.yml", env=env, log=log, report_dir=report_dir)

    write_report(report, [
        "# Phase 9 Windows Rollout Summary",
        "",
        f"- Inventory: `{args.config}`",
        f"- VM names: {', '.join(vm_names)}",
        f"- Apply requested: `{args.apply}`",
        f"- Validate only: `{args.validate_only}`",
        f"- Post-clone baseline requested: `{args.postclone}`",
        f"- Per-host report requested: `{args.report}`",
        f"- Plan exit code: `{plan_exit}`",
        f"- Command log: `{log}`",
        "",
        "## Result",
        "",
        "- Generated Windows OpenTofu tfvars and Ansible WinRM inventory.",
        "- OpenTofu validation/plan ran unless validate-only mode was selected.",
        "- Destroy actions are blocked by default.",
        "- WinRM, baseline, post-clone baseline, shell validation, and per-host reports run only when requested after apply or in validate-only mode.",
    ])
    print(f"wrote {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
