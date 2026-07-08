# NoCloud Seed ISO Workflow

Use this workflow for Ubuntu cloud-image templates that need a static IP on
first boot.

## Why

Phase 4C showed that this environment should use NoCloud seed ISOs for Ubuntu
static IP clones.

- vApp `network-config` was rejected by vCenter/template properties.
- VMware Guest Customization failed while setting Ubuntu guest networking.
- NoCloud seed ISO worked and was verified with SSH, cloud-init, and Ansible.

## Generate Seeds

Create or edit a TOML config based on:

```text
examples/nocloud-seeds.example.toml
```

The public SSH key can be provided directly as `ssh_public_key` or read from
`ssh_public_key_file`. Use a direct public key when running as `iacsvc` and the
key directory is root-only.

Generate seed files and ISOs:

```bash
/opt/appserver/apps/iac/repositories/iac-platform/scripts/generate-nocloud-seeds.py \
  --config /opt/appserver/apps/iac/repositories/iac-platform/examples/nocloud-seeds.example.toml \
  --output-dir /opt/appserver/data/iac/seed
```

Upload the generated ISOs to a vSphere datastore:

```bash
set -a
. /opt/appserver/config/iac/vcenter.env
set +a
export GOVC_URL="https://${VSPHERE_SERVER}/sdk"
export GOVC_USERNAME="${VSPHERE_USER}"
export GOVC_PASSWORD="${VSPHERE_PASSWORD}"
export GOVC_INSECURE=1
export GOVC_DATACENTER="Datacenter SVB"

/opt/appserver/apps/iac/repositories/iac-platform/scripts/generate-nocloud-seeds.py \
  --config /opt/appserver/apps/iac/repositories/iac-platform/examples/nocloud-seeds.example.toml \
  --output-dir /opt/appserver/data/iac/seed \
  --upload \
  --datastore MSA2060-Datastore2 \
  --datastore-dir iac/seed
```

## OpenTofu Use

Set the datastore-relative ISO path in the VM tfvars:

```hcl
seed_iso_path = "iac/seed/iac-lab-ubuntu-4c-seed.iso"
```

The `vsphere-linux-vm` module attaches:

- one client CDROM required by the Ubuntu cloud-image OVF/vApp transport
- one datastore ISO CDROM for the NoCloud seed

## Validation

After clone:

```bash
ping 10.1.0.25
ssh -i /opt/appserver/config/iac/keys/iac_template_ed25519 iacadmin@10.1.0.25
cloud-init status --long
```

Expected cloud-init detail:

```text
DataSourceNoCloud [seed=/dev/sr0]
```
