# Windows Multi-VM Tfvars Workflow

Phase 6 adds a shared inventory flow for Windows VM clones.

Use one TOML inventory to generate one OpenTofu `windows.auto.tfvars` file
containing a `windows_vms` map. The Windows environment then creates every VM in
that map only when `create_vm=true`.

## Inventory

Start from:

```text
examples/windows-vms.example.toml
```

Add one `[[vm]]` block per Windows VM. Each VM must set:

- `name`: vCenter VM name and OpenTofu map key
- `computer_name`: Windows hostname, 15 characters or fewer
- `ipv4_address`: static IPv4 address

Defaults define the shared vSphere placement and Windows customization settings:

- `network = "SVB Server"`
- `source_vm = "/Datacenter SVB/vm/IaC-Lab/tpl-windows-server-2025-kps-reatime"`
- `guest_id = "windows9Server64Guest"`
- `firmware = "efi"`
- `efi_secure_boot_enabled = true`
- static gateway/DNS/suffix values
- disk layout matching the Windows template clone behavior

## Generate Tfvars

Keep `create_vm=false` while reviewing the OpenTofu plan:

```bash
/opt/appserver/apps/iac/repositories/iac-platform/scripts/generate-windows-tfvars.py \
  --config /opt/appserver/apps/iac/repositories/iac-platform/examples/windows-vms.example.toml \
  --output /opt/appserver/apps/iac/repositories/iac-platform/opentofu/environments/windows-lab/windows.auto.tfvars
```

When ready for an approved controlled apply, regenerate with `--create-vm`:

```bash
/opt/appserver/apps/iac/repositories/iac-platform/scripts/generate-windows-tfvars.py \
  --config /opt/appserver/apps/iac/repositories/iac-platform/examples/windows-vms.example.toml \
  --output /opt/appserver/apps/iac/repositories/iac-platform/opentofu/environments/windows-lab/windows.auto.tfvars \
  --create-vm
```

## Validate and Plan

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform/opentofu/environments/windows-lab
tofu validate
tofu plan
```

The Windows lab environment uses `for_each` over `var.windows_vms` when
`create_vm=true`. With `create_vm=false`, plans are read-only and create no VMs.

For controlled applies that must support WinRM login, set the local
Administrator password through the sensitive environment variable:

```bash
set -a
. /opt/appserver/config/iac/windows-ansible.env
set +a
tofu plan
tofu apply
```

The env file should export `TF_VAR_windows_admin_password`. Do not place this
secret in generated tfvars or examples.

## Phase 6 Notes

Phase 5F proved that `SVB Server` is the correct network for the 10.1.0.0/24
Windows lab test path. ICMP may still be blocked by Windows Firewall, but WinRM
HTTP on TCP/5985 was reachable from sysap during validation.
