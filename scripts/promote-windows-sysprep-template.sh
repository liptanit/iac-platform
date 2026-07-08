#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Promote a powered-off, sysprepped Windows preparation VM into a vSphere template.

This script refuses to run unless the VM is powered off. Run Sysprep inside
Windows first with:
  sysprep.exe /generalize /oobe /shutdown

Required environment:
  VSPHERE_SERVER, VSPHERE_USER, VSPHERE_PASSWORD

Example:
  scripts/promote-windows-sysprep-template.sh \
    --vm "/Datacenter SVB/vm/IaC-Lab/win2025-kps-reatime-sysprep"
USAGE
}

vm_path=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --vm) vm_path="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$vm_path" ]]; then
  usage >&2
  exit 2
fi

: "${VSPHERE_SERVER:?missing VSPHERE_SERVER}"
: "${VSPHERE_USER:?missing VSPHERE_USER}"
: "${VSPHERE_PASSWORD:?missing VSPHERE_PASSWORD}"

export GOVC_URL="$VSPHERE_SERVER"
export GOVC_USERNAME="$VSPHERE_USER"
export GOVC_PASSWORD="$VSPHERE_PASSWORD"
export GOVC_INSECURE="${GOVC_INSECURE:-1}"

power_state="$(govc vm.info -json "$vm_path" | python3 -c 'import json,sys; print(json.load(sys.stdin)["virtualMachines"][0]["runtime"]["powerState"])')"
if [[ "$power_state" != "poweredOff" ]]; then
  echo "refusing to convert VM that is not poweredOff: $power_state" >&2
  exit 1
fi

govc vm.markastemplate "$vm_path"
govc vm.info "$vm_path"
