#!/usr/bin/env python3
"""Run the controlled Ubuntu/Linux VM rollout workflow."""

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
LINUX_ENV = REPO / "opentofu" / "environments" / "lab"
DEFAULT_TFVARS = LINUX_ENV / "lab.auto.tfvars"
DEFAULT_INVENTORY = REPO / "ansible" / "inventories" / "linux" / "hosts.ini"
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


def load_inventory(config: Path) -> list[dict[str, str]]:
    data = tomllib.loads(config.read_text(encoding="utf-8"))
    vms = data.get("vm", [])
    result: list[dict[str, str]] = []
    for item in vms:
        name = str(item.get("name", "")).strip()
        ipv4 = str(item.get("ipv4", "")).strip()
        if not name or not ipv4:
            raise SystemExit("each [[vm]] entry must have name and ipv4")
        result.append({"name": name, "ipv4": ipv4})
    if not result:
        raise SystemExit("inventory has no [[vm]] entries")
    return result


def plan_has_destroy(plan_text: str) -> bool:
    destroy_patterns = [
        r"Plan: \d+ to add, \d+ to change, [1-9]\d* to destroy",
        r"-/+",
        r"will be destroyed",
    ]
    return any(re.search(pattern, plan_text) for pattern in destroy_patterns)


def govc_env(env: dict[str, str]) -> dict[str, str]:
    result = env.copy()
    if "VSPHERE_SERVER" in result:
        result.setdefault("GOVC_URL", f"https://{result['VSPHERE_SERVER']}/sdk")
    if "VSPHERE_USER" in result:
        result.setdefault("GOVC_USERNAME", result["VSPHERE_USER"])
    if "VSPHERE_PASSWORD" in result:
        result.setdefault("GOVC_PASSWORD", result["VSPHERE_PASSWORD"])
    result.setdefault("GOVC_INSECURE", "1")
    result.setdefault("GOVC_DATACENTER", "Datacenter SVB")
    return result


def precheck(vms: list[dict[str, str]], env: dict[str, str], log: Path, allow_used_ip: bool) -> None:
    failures: list[str] = []
    for vm in vms:
        ping = run(["ping", "-c", "2", "-W", "1", vm["ipv4"]], env=env, log=log, check=False)
        if ping.returncode == 0 and not allow_used_ip:
            failures.append(f"{vm['ipv4']} already replies to ping")

        info = run(["govc", "vm.info", f"vm/IaC-Lab/{vm['name']}"], env=govc_env(env), log=log, check=False)
        if info.stdout.strip():
            failures.append(f"{vm['name']} already exists in vCenter")

    if failures:
        raise SystemExit("precheck failed:\n- " + "\n- ".join(failures))


def ansible_playbook(playbook: str, *, env: dict[str, str], log: Path, report_dir: Path) -> None:
    run([
        str(ANSIBLE),
        "-i",
        str(DEFAULT_INVENTORY),
        str(REPO / "ansible" / "playbooks" / playbook),
        "-e",
        f"linux_report_dir={report_dir / 'host-reports'}",
    ], env=env, log=log)


def write_report(report: Path, lines: Iterable[str]) -> None:
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--allow-destroy", action="store_true")
    parser.add_argument("--allow-used-ip", action="store_true", help="Bypass ping-based IP conflict guard.")
    parser.add_argument("--skip-precheck", action="store_true")
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--iac-env", type=Path, default=Path("/opt/appserver/config/iac/iac.env"))
    parser.add_argument("--vcenter-env", type=Path, default=Path("/opt/appserver/config/iac/vcenter.env"))
    parser.add_argument("--seed-output-dir", type=Path, default=Path("/opt/appserver/data/iac/seed"))
    parser.add_argument("--seed-datastore", default="MSA2060-Datastore2")
    parser.add_argument("--seed-datastore-dir", default="iac/seed")
    args = parser.parse_args()

    require_file(args.config, "Linux VM inventory")
    require_file(args.iac_env, "IaC env file")
    require_file(args.vcenter_env, "vCenter env file")

    report_dir = args.report_dir or DEFAULT_REPORT_ROOT / f"phase10_linux_rollout_{now_stamp()}"
    report_dir.mkdir(parents=True, exist_ok=True)
    log = report_dir / "phase10-commands.log"
    report = report_dir / "phase10-summary.md"

    vms = load_inventory(args.config)
    env = os.environ.copy()
    env.update(load_env_file(args.iac_env))
    env.update(load_env_file(args.vcenter_env))

    run([
        str(REPO / "scripts" / "generate-linux-ansible-inventory.py"),
        "--config",
        str(args.config),
        "--output",
        str(DEFAULT_INVENTORY),
    ], env=env, log=log)

    if not args.validate_only:
        if not args.skip_precheck:
            precheck(vms, env, log, args.allow_used_ip)

        run([
            str(REPO / "scripts" / "generate-nocloud-seeds.py"),
            "--config",
            str(args.config),
            "--output-dir",
            str(args.seed_output_dir),
            "--upload",
            "--datastore",
            args.seed_datastore,
            "--datastore-dir",
            args.seed_datastore_dir,
        ], env=govc_env(env), log=log)
        run([
            str(REPO / "scripts" / "generate-lab-tfvars.py"),
            "--config",
            str(args.config),
            "--output",
            str(DEFAULT_TFVARS),
            "--create-vm",
        ], env=env, log=log)
        run(["tofu", "fmt", "-check", "-recursive"], cwd=REPO, env=env, log=log)
        run(["tofu", "init", "-input=false"], cwd=LINUX_ENV, env=env, log=log)
        run(["tofu", "validate"], cwd=LINUX_ENV, env=env, log=log)
        plan = run([
            "tofu",
            "plan",
            "-input=false",
            "-detailed-exitcode",
            "-no-color",
            "-out",
            str(report_dir / "linux.tfplan"),
        ], cwd=LINUX_ENV, env=env, log=log, check=False)
        if plan.returncode not in (0, 2):
            raise SystemExit(f"tofu plan failed with exit {plan.returncode}")
        if plan_has_destroy(plan.stdout) and not args.allow_destroy:
            raise SystemExit("plan includes destroy action; rerun with --allow-destroy only after explicit approval")
        if args.apply:
            run(["tofu", "apply", "-input=false", "-auto-approve", str(report_dir / "linux.tfplan")], cwd=LINUX_ENV, env=env, log=log)

    if args.apply or args.validate_only:
        ansible_playbook("ping.yml", env=env, log=log, report_dir=report_dir)
        ansible_playbook("baseline-linux.yml", env=env, log=log, report_dir=report_dir)
        if args.report:
            ansible_playbook("report-linux.yml", env=env, log=log, report_dir=report_dir)

    write_report(report, [
        "# Phase 10 Linux Rollout Summary",
        "",
        f"- Inventory: `{args.config}`",
        f"- VM names: {', '.join(vm['name'] for vm in vms)}",
        f"- IPs: {', '.join(vm['ipv4'] for vm in vms)}",
        f"- Apply requested: `{args.apply}`",
        f"- Validate only: `{args.validate_only}`",
        f"- Per-host report requested: `{args.report}`",
        f"- Command log: `{log}`",
    ])
    print(f"wrote {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
