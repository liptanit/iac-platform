#!/usr/bin/env python3
"""Generate Windows OpenTofu tfvars from a TOML VM inventory."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import Any


def hcl_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def hcl_bool(value: bool) -> str:
    return "true" if value else "false"


def hcl_key(value: str) -> str:
    return hcl_string(value)


def hcl_list(values: list[str]) -> str:
    return "[" + ", ".join(hcl_string(value) for value in values) + "]"


def require_keys(table: dict[str, Any], keys: list[str], name: str) -> None:
    missing = [key for key in keys if key not in table or table[key] in ("", None)]
    if missing:
        raise SystemExit(f"{name} missing required key(s): {', '.join(missing)}")


def as_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise SystemExit(f"{name} must be a boolean")


def as_int(value: Any, name: str) -> int:
    if isinstance(value, int):
        return value
    raise SystemExit(f"{name} must be an integer")


def as_str_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"{name} must be a list of strings")
    return value


def windows_computer_name(vm: dict[str, Any], name: str) -> str:
    computer_name = str(vm.get("computer_name") or name.upper().replace("_", "-"))
    if len(computer_name) > 15:
        raise SystemExit(f"{name}: computer_name {computer_name!r} exceeds Windows 15 character limit")
    if not re.fullmatch(r"[A-Za-z0-9-]+", computer_name):
        raise SystemExit(f"{name}: computer_name {computer_name!r} must contain only letters, numbers, and hyphen")
    if computer_name.startswith("-") or computer_name.endswith("-"):
        raise SystemExit(f"{name}: computer_name must not start or end with hyphen")
    return computer_name


def disk_lines(disks: list[dict[str, Any]]) -> list[str]:
    lines = ["    disks = ["]
    for disk in disks:
        require_keys(disk, ["label", "size_gb", "unit_number", "thin_provisioned"], "disk")
        lines.extend([
            "      {",
            f"        label            = {hcl_string(str(disk['label']))}",
            f"        size_gb          = {as_int(disk['size_gb'], 'disk.size_gb')}",
            f"        unit_number      = {as_int(disk['unit_number'], 'disk.unit_number')}",
            f"        thin_provisioned = {hcl_bool(as_bool(disk['thin_provisioned'], 'disk.thin_provisioned'))}",
            "      },",
        ])
    lines.append("    ]")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--create-vm", action="store_true", help="Set create_vm=true. Default is false.")
    parser.add_argument("--datacenter", default="Datacenter SVB")
    parser.add_argument("--cluster", default="GZ Cluster")
    parser.add_argument("--datastore", default="Web-Datastore")
    parser.add_argument("--network", default="SVB Server")
    parser.add_argument("--vm-folder", default="IaC-Lab")
    parser.add_argument("--source-vm", default="/Datacenter SVB/vm/IaC-Lab/tpl-windows-server-2025-kps-reatime")
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    defaults = config.get("defaults", {})
    vms = config.get("vm", [])
    if not vms:
        raise SystemExit("config has no [[vm]] entries")

    default_disks = defaults.get("disks", [
        {"label": "disk0", "size_gb": 300, "unit_number": 0, "thin_provisioned": False},
        {"label": "disk1", "size_gb": 200, "unit_number": 1, "thin_provisioned": False},
    ])
    dns_servers = as_str_list(defaults.get("dns_server_list", ["10.1.0.9", "10.1.0.254"]), "defaults.dns_server_list")
    dns_suffixes = as_str_list(defaults.get("dns_suffix_list", ["kingpower.local"]), "defaults.dns_suffix_list")

    lines = [
        f"datacenter = {hcl_string(str(defaults.get('datacenter', args.datacenter)))}",
        f"cluster    = {hcl_string(str(defaults.get('cluster', args.cluster)))}",
        f"datastore  = {hcl_string(str(defaults.get('datastore', args.datastore)))}",
        f"network    = {hcl_string(str(defaults.get('network', args.network)))}",
        f"vm_folder  = {hcl_string(str(defaults.get('vm_folder', args.vm_folder)))}",
        "",
        f"create_vm = {hcl_bool(args.create_vm)}",
        "",
        f"source_vm = {hcl_string(str(defaults.get('source_vm', args.source_vm)))}",
        "",
        "windows_vms = {",
    ]

    for vm in vms:
        require_keys(vm, ["name", "ipv4_address"], "vm")
        name = str(vm["name"])
        disks = vm.get("disks", default_disks)
        if not isinstance(disks, list) or not disks:
            raise SystemExit(f"{name}: disks must be a non-empty list")
        lines.extend([
            f"  {hcl_key(name)} = {{",
            f"    cpu                     = {as_int(vm.get('cpu', defaults.get('cpu', 4)), f'{name}.cpu')}",
            f"    memory_mb               = {as_int(vm.get('memory_mb', defaults.get('memory_mb', 32768)), f'{name}.memory_mb')}",
            f"    network                 = {hcl_string(str(vm.get('network', defaults.get('network', args.network))))}",
            f"    guest_id                = {hcl_string(str(vm.get('guest_id', defaults.get('guest_id', 'windows9Server64Guest'))))}",
            f"    firmware                = {hcl_string(str(vm.get('firmware', defaults.get('firmware', 'efi'))))}",
            f"    efi_secure_boot_enabled = {hcl_bool(as_bool(vm.get('efi_secure_boot_enabled', defaults.get('efi_secure_boot_enabled', True)), f'{name}.efi_secure_boot_enabled'))}",
            f"    cdrom_iso_datastore     = {hcl_string(str(vm.get('cdrom_iso_datastore', defaults.get('cdrom_iso_datastore', ''))))}",
            f"    cdrom_iso_path          = {hcl_string(str(vm.get('cdrom_iso_path', defaults.get('cdrom_iso_path', ''))))}",
        ])
        lines.extend(disk_lines(disks))
        lines.extend([
            "",
            f"    customize_windows = {hcl_bool(as_bool(vm.get('customize_windows', defaults.get('customize_windows', True)), f'{name}.customize_windows'))}",
            f"    computer_name     = {hcl_string(windows_computer_name(vm, name))}",
            f"    workgroup         = {hcl_string(str(vm.get('workgroup', defaults.get('workgroup', 'WORKGROUP'))))}",
            f"    ipv4_address      = {hcl_string(str(vm['ipv4_address']))}",
            f"    ipv4_netmask      = {as_int(vm.get('ipv4_netmask', defaults.get('ipv4_netmask', 24)), f'{name}.ipv4_netmask')}",
            f"    ipv4_gateway      = {hcl_string(str(vm.get('ipv4_gateway', defaults.get('ipv4_gateway', '10.1.0.254'))))}",
            f"    dns_server_list   = {hcl_list(as_str_list(vm.get('dns_server_list', dns_servers), f'{name}.dns_server_list'))}",
            f"    dns_suffix_list   = {hcl_list(as_str_list(vm.get('dns_suffix_list', dns_suffixes), f'{name}.dns_suffix_list'))}",
            "  }",
        ])

    lines.append("}")
    lines.append("")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
