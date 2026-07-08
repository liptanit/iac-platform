#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Create a powered-off Windows clone for manual Sysprep/generalize preparation.

Required environment:
  VSPHERE_SERVER, VSPHERE_USER, VSPHERE_PASSWORD

Example:
  scripts/create-windows-sysprep-clone.sh \
    --source "/Datacenter SVB/vm/Discovered virtual machine/KPS-Reatime" \
    --name "win2025-kps-reatime-sysprep" \
    --folder "/Datacenter SVB/vm/IaC-Lab" \
    --host-ip "10.0.1.1" \
    --datastore "DB-Datastore" \
    --network "KPS Server"
USAGE
}

source_vm=""
name=""
folder="/Datacenter SVB/vm/IaC-Lab"
host_ip=""
datastore=""
network="KPS Server"
adapter="e1000e"
annotation="Phase 5C Windows Sysprep preparation clone. Generalize, shutdown, then promote intentionally."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) source_vm="$2"; shift 2 ;;
    --name) name="$2"; shift 2 ;;
    --folder) folder="$2"; shift 2 ;;
    --host-ip) host_ip="$2"; shift 2 ;;
    --datastore) datastore="$2"; shift 2 ;;
    --network) network="$2"; shift 2 ;;
    --adapter) adapter="$2"; shift 2 ;;
    --annotation) annotation="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$source_vm" || -z "$name" || -z "$host_ip" || -z "$datastore" ]]; then
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

existing="$(govc find '/Datacenter SVB/vm' -type m -name "$name" 2>/dev/null || true)"
if [[ -n "$existing" ]]; then
  echo "target VM already exists: $existing" >&2
  exit 1
fi

govc vm.clone \
  -vm "$source_vm" \
  -folder "$folder" \
  -host.ip="$host_ip" \
  -ds "$datastore" \
  -net "$network" \
  -net.adapter="$adapter" \
  -on=false \
  -annotation "$annotation" \
  "$name"

govc vm.info "$folder/$name"
