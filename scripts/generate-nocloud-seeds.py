#!/usr/bin/env python3
"""Generate Ubuntu NoCloud seed ISOs for vSphere/OpenTofu clones."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


def q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def require_keys(table: dict, keys: list[str], name: str) -> None:
    missing = [key for key in keys if key not in table or table[key] in ("", None)]
    if missing:
        raise SystemExit(f"{name} missing required key(s): {', '.join(missing)}")


def render_user_data(vm: dict, defaults: dict, public_key: str) -> str:
    username = vm.get("username", defaults.get("username", "iacadmin"))
    groups = vm.get("groups", defaults.get("groups", ["adm", "sudo"]))
    shell = vm.get("shell", defaults.get("shell", "/bin/bash"))
    sudo_rule = vm.get("sudo", defaults.get("sudo", "ALL=(ALL) NOPASSWD:ALL"))
    runcmd = vm.get("runcmd", defaults.get("runcmd", ['systemctl enable --now open-vm-tools || true']))

    lines = [
        "#cloud-config",
        "preserve_hostname: false",
        f"hostname: {vm['name']}",
        "manage_etc_hosts: true",
        "users:",
        "  - default",
        f"  - name: {username}",
        f"    groups: [{', '.join(groups)}]",
        f"    shell: {shell}",
        f"    sudo: [{q(sudo_rule)}]",
        "    lock_passwd: true",
        "    ssh_authorized_keys:",
        f"      - {public_key}",
        "ssh_pwauth: false",
    ]

    if runcmd:
        lines.append("runcmd:")
        for command in runcmd:
            lines.append(f"  - [ sh, -c, {q(command)} ]")

    lines.append(f"final_message: {q('IaC Ubuntu NoCloud clone is ready.')}")
    return "\n".join(lines) + "\n"


def render_meta_data(vm: dict) -> str:
    instance_id = vm.get("instance_id", f"{vm['name']}-nocloud")
    return f"instance-id: {instance_id}\nlocal-hostname: {vm['name']}\n"


def render_network_config(vm: dict, defaults: dict) -> str:
    dns_servers = vm.get("dns_servers", defaults.get("dns_servers", []))
    if not dns_servers:
        raise SystemExit(f"{vm['name']} missing DNS servers")

    lines = [
        "version: 2",
        "ethernets:",
        "  labnic:",
        "    match:",
        f"      name: {q(vm.get('interface_match', defaults.get('interface_match', 'en*')))}",
        "    dhcp4: false",
        "    dhcp6: false",
        "    addresses:",
        f"      - {vm['ipv4']}/{vm.get('prefix', defaults.get('prefix', 24))}",
        "    routes:",
        "      - to: default",
        f"        via: {vm.get('gateway', defaults['gateway'])}",
        "    nameservers:",
        "      addresses:",
    ]
    lines.extend(f"        - {server}" for server in dns_servers)
    return "\n".join(lines) + "\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, dry_run: bool, allow_fail: bool = False) -> None:
    print("+ " + " ".join(command))
    if not dry_run:
        if allow_fail:
            subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(command, check=True)


def upload_iso(iso_path: Path, datastore: str, datastore_dir: str, dry_run: bool) -> str:
    govc = shutil.which("govc")
    if not govc:
        raise SystemExit("govc not found in PATH")

    target = f"{datastore_dir.rstrip('/')}/{iso_path.name}"
    run([govc, "datastore.mkdir", "-ds", datastore, datastore_dir], dry_run=dry_run, allow_fail=True)
    run([govc, "datastore.rm", "-ds", datastore, target], dry_run=dry_run, allow_fail=True)
    run([govc, "datastore.upload", "-ds", datastore, str(iso_path), target], dry_run=dry_run)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("/opt/appserver/data/iac/seed"))
    parser.add_argument("--only", action="append", default=[], help="Generate only the named VM. Can be repeated.")
    parser.add_argument("--upload", action="store_true", help="Upload generated ISOs to vSphere datastore with govc.")
    parser.add_argument("--datastore", help="Datastore name for --upload.")
    parser.add_argument("--datastore-dir", default="iac/seed", help="Destination datastore directory for --upload.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    defaults = config.get("defaults", {})
    require_keys(defaults, ["gateway", "dns_servers"], "defaults")

    if defaults.get("ssh_public_key"):
        public_key = defaults["ssh_public_key"].strip()
    elif defaults.get("ssh_public_key_file"):
        public_key_path = Path(defaults["ssh_public_key_file"])
        public_key = public_key_path.read_text(encoding="utf-8").strip()
    else:
        raise SystemExit("defaults must set ssh_public_key or ssh_public_key_file")

    if not public_key.startswith("ssh-"):
        raise SystemExit("invalid SSH public key")

    vms = config.get("vm", [])
    if not vms:
        raise SystemExit("config has no [[vm]] entries")

    only = set(args.only)
    if args.upload and not args.datastore:
        raise SystemExit("--upload requires --datastore")

    cloud_localds = shutil.which("cloud-localds")
    if not cloud_localds:
        raise SystemExit("cloud-localds not found in PATH")

    generated: list[tuple[str, Path, str, str | None]] = []
    for vm in vms:
        require_keys(vm, ["name", "ipv4"], "vm")
        if only and vm["name"] not in only:
            continue

        vm_dir = args.output_dir / vm["name"]
        iso_path = vm_dir / f"{vm['name']}-seed.iso"
        if not args.dry_run:
            vm_dir.mkdir(parents=True, exist_ok=True)
            (vm_dir / "user-data").write_text(render_user_data(vm, defaults, public_key), encoding="utf-8")
            (vm_dir / "meta-data").write_text(render_meta_data(vm), encoding="utf-8")
            (vm_dir / "network-config").write_text(render_network_config(vm, defaults), encoding="utf-8")

        run(
            [
                cloud_localds,
                "-N",
                str(vm_dir / "network-config"),
                str(iso_path),
                str(vm_dir / "user-data"),
                str(vm_dir / "meta-data"),
            ],
            dry_run=args.dry_run,
        )

        digest = "dry-run"
        if not args.dry_run:
            digest = sha256(iso_path)
            (vm_dir / "SHA256SUMS").write_text(f"{digest}  {iso_path.name}\n", encoding="utf-8")

        datastore_path = None
        if args.upload:
            datastore_path = upload_iso(iso_path, args.datastore, args.datastore_dir, args.dry_run)

        generated.append((vm["name"], iso_path, digest, datastore_path))

    if only and not generated:
        raise SystemExit(f"no matching VM entries for: {', '.join(sorted(only))}")

    print("\nGenerated seed ISOs:")
    for name, iso_path, digest, datastore_path in generated:
        suffix = f" datastore_path={datastore_path}" if datastore_path else ""
        print(f"- {name}: iso={iso_path} sha256={digest}{suffix}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
