#!/usr/bin/env python3
"""Generate an Ansible WinRM inventory from the Windows VM TOML inventory."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any


def require_keys(table: dict[str, Any], keys: list[str], name: str) -> None:
    missing = [key for key in keys if key not in table or table[key] in ("", None)]
    if missing:
        raise SystemExit(f"{name} missing required key(s): {', '.join(missing)}")


def ansible_scalar(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def host_var_pairs(vm: dict[str, Any]) -> list[str]:
    pairs: list[str] = []
    role = str(vm.get("role", "") or "").strip()
    role_profile = str(vm.get("role_profile", "") or "").strip()
    if role:
        pairs.append(f"iac_role={ansible_scalar(role)}")
    if role_profile:
        pairs.append(f"iac_role_profile={ansible_scalar(role_profile)}")
    if "disks" in vm:
        pairs.append(f"iac_disks={ansible_scalar(vm.get('disks') or [])}")
    if "cpu" in vm:
        pairs.append(f"iac_cpu={ansible_scalar(vm.get('cpu'))}")
    if "memory_mb" in vm:
        pairs.append(f"iac_memory_mb={ansible_scalar(vm.get('memory_mb'))}")
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--group", default="windows")
    parser.add_argument("--port", type=int, default=5985)
    parser.add_argument("--transport", default="ntlm")
    parser.add_argument("--scheme", default="http", choices=["http", "https"])
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    vms = config.get("vm", [])
    if not vms:
        raise SystemExit("config has no [[vm]] entries")

    lines = [
        f"[{args.group}]",
    ]
    for vm in vms:
        require_keys(vm, ["name", "ipv4_address"], "vm")
        host_vars = " ".join(host_var_pairs(vm))
        suffix = f" {host_vars}" if host_vars else ""
        lines.append(f"{vm['name']} ansible_host={vm['ipv4_address']}{suffix}")

    lines.extend([
        "",
        f"[{args.group}:vars]",
        "ansible_connection=winrm",
        f"ansible_port={args.port}",
        f"ansible_winrm_scheme={args.scheme}",
        f"ansible_winrm_transport={args.transport}",
        "ansible_winrm_server_cert_validation=ignore",
        "ansible_user={{ lookup('env', 'ANSIBLE_WINDOWS_USER') }}",
        "ansible_password={{ lookup('env', 'ANSIBLE_WINDOWS_PASSWORD') }}",
        "",
    ])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
