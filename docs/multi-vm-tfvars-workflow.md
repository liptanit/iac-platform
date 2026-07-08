# Multi-VM Tfvars Workflow

Phase 4E adds a shared inventory flow for Ubuntu VM clones.

Use one TOML inventory to generate:

- one NoCloud seed ISO per VM
- one OpenTofu tfvars file containing a `vms` map

## Inventory

Start from:

```text
examples/nocloud-seeds.example.toml
```

Add one `[[vm]]` block per VM. Each VM can override default CPU, memory, disk,
template, and seed ISO path.

## Generate Seed ISOs

```bash
/opt/appserver/apps/iac/repositories/iac-platform/scripts/generate-nocloud-seeds.py \
  --config /opt/appserver/apps/iac/repositories/iac-platform/examples/nocloud-seeds.example.toml \
  --output-dir /opt/appserver/data/iac/seed \
  --upload \
  --datastore MSA2060-Datastore2 \
  --datastore-dir iac/seed
```

## Generate Tfvars

Keep `create_vm=false` while reviewing the OpenTofu plan:

```bash
/opt/appserver/apps/iac/repositories/iac-platform/scripts/generate-lab-tfvars.py \
  --config /opt/appserver/apps/iac/repositories/iac-platform/examples/nocloud-seeds.example.toml \
  --output /opt/appserver/apps/iac/repositories/iac-platform/opentofu/environments/lab/lab.auto.tfvars
```

When ready to create real VMs, regenerate with `--create-vm` after confirming
names, IPs, datastore, and seed ISO uploads:

```bash
/opt/appserver/apps/iac/repositories/iac-platform/scripts/generate-lab-tfvars.py \
  --config /opt/appserver/apps/iac/repositories/iac-platform/examples/nocloud-seeds.example.toml \
  --output /opt/appserver/apps/iac/repositories/iac-platform/opentofu/environments/lab/lab.auto.tfvars \
  --create-vm
```

## Validate and Plan

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform/opentofu/environments/lab
tofu validate
tofu plan
```

The lab environment uses `for_each` over `var.vms` when `create_vm=true`.
With `create_vm=false`, plans are read-only and create no VMs.
