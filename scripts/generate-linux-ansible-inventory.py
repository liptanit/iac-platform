#!/usr/bin/env python3
"""Generate an Ansible SSH inventory from the Linux VM TOML inventory."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any


def require_keys(table: dict[str, Any], keys: list[str], name: str) -> None:
    missing = [key for key in keys if key not in table or table[key] in ("", None)]
    if missing:
        raise SystemExit(f"{name} missing required key(s): {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--group", default="linux")
    parser.add_argument("--user", default="iacadmin")
    parser.add_argument("--private-key", default="/opt/appserver/config/iac/keys/iac_template_ed25519")
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    defaults = config.get("defaults", {})
    vms = config.get("vm", [])
    if not vms:
        raise SystemExit("config has no [[vm]] entries")

    lines = [f"[{args.group}]"]
    for vm in vms:
        require_keys(vm, ["name", "ipv4"], "vm")
        user = vm.get("username", defaults.get("username", args.user))
        lines.append(f"{vm['name']} ansible_host={vm['ipv4']} ansible_user={user}")

    lines.extend([
        "",
        f"[{args.group}:vars]",
        "ansible_connection=ssh",
        f"ansible_ssh_private_key_file={args.private_key}",
        "ansible_python_interpreter=/usr/bin/python3",
        "",
    ])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
