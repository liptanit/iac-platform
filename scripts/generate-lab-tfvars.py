#!/usr/bin/env python3
"""Generate OpenTofu lab tfvars from the NoCloud seed TOML inventory."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path


def hcl_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def hcl_key(value: str) -> str:
    return hcl_string(value)


def require_keys(table: dict, keys: list[str], name: str) -> None:
    missing = [key for key in keys if key not in table or table[key] in ("", None)]
    if missing:
        raise SystemExit(f"{name} missing required key(s): {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--create-vm", action="store_true", help="Set create_vm=true. Default is false.")
    parser.add_argument("--datacenter", default="Datacenter SVB")
    parser.add_argument("--cluster", default="SVB Cluster")
    parser.add_argument("--datastore", default="MSA2060-Datastore2")
    parser.add_argument("--network", default="SVB Server")
    parser.add_argument("--vm-folder", default="IaC-Lab")
    parser.add_argument("--template", default="tpl-ubuntu-24.04-server")
    parser.add_argument("--cpu", type=int, default=2)
    parser.add_argument("--memory-mb", type=int, default=4096)
    parser.add_argument("--disk-gb", type=int, default=40)
    parser.add_argument("--datastore-seed-dir", default="iac/seed")
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    defaults = config.get("defaults", {})
    vms = config.get("vm", [])
    if not vms:
        raise SystemExit("config has no [[vm]] entries")

    if defaults.get("ssh_public_key"):
        public_key = defaults["ssh_public_key"].strip()
    elif defaults.get("ssh_public_key_file"):
        public_key = Path(defaults["ssh_public_key_file"]).read_text(encoding="utf-8").strip()
    else:
        raise SystemExit("defaults must set ssh_public_key or ssh_public_key_file")

    lines = [
        f"datacenter = {hcl_string(args.datacenter)}",
        f"cluster    = {hcl_string(args.cluster)}",
        f"datastore  = {hcl_string(args.datastore)}",
        f"network    = {hcl_string(args.network)}",
        f"vm_folder  = {hcl_string(args.vm_folder)}",
        "",
        f"create_vm = {str(args.create_vm).lower()}",
        "",
        f"ssh_public_key = {hcl_string(public_key)}",
        "",
        "vms = {",
    ]

    for vm in vms:
        require_keys(vm, ["name"], "vm")
        name = vm["name"]
        template = vm.get("template", defaults.get("template", args.template))
        cpu = vm.get("cpu", defaults.get("cpu", args.cpu))
        memory_mb = vm.get("memory_mb", defaults.get("memory_mb", args.memory_mb))
        disk_gb = vm.get("disk_gb", defaults.get("disk_gb", args.disk_gb))
        datacenter = vm.get("datacenter", defaults.get("datacenter", args.datacenter))
        cluster = vm.get("cluster", defaults.get("cluster", args.cluster))
        datastore = vm.get("datastore", defaults.get("datastore", args.datastore))
        network = vm.get("network", defaults.get("network", args.network))
        seed_iso_path = vm.get(
            "seed_iso_path",
            f"{args.datastore_seed_dir.rstrip('/')}/{name}-seed.iso",
        )

        lines.extend(
            [
                f"  {hcl_key(name)} = {{",
                f"    template      = {hcl_string(template)}",
                f"    cpu           = {cpu}",
                f"    memory_mb     = {memory_mb}",
                f"    disk_gb       = {disk_gb}",
                f"    datacenter    = {hcl_string(datacenter)}",
                f"    cluster       = {hcl_string(cluster)}",
                f"    datastore     = {hcl_string(datastore)}",
                f"    network       = {hcl_string(network)}",
                f"    seed_iso_path = {hcl_string(seed_iso_path)}",
                "  }",
            ]
        )

    lines.append("}")
    lines.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
