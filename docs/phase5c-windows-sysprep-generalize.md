# Phase 5C Windows Sysprep / Generalize Workflow

Date: 2026-07-08
Source VM: `/Datacenter SVB/vm/Discovered virtual machine/KPS-Reatime`
Target template name: `tpl-windows-server-2025-kps-reatime`

## Goal

Prepare a reusable Windows template safely, then allow OpenTofu to manage new Windows VMs from that template.

The original `KPS-Reatime` VM must not be sysprepped directly. Sysprep/generalize changes machine identity and is not a reversible normal configuration step.

## Safe Workflow

1. Create a powered-off preparation clone from `KPS-Reatime`.
2. Power on only the preparation clone.
3. Log in to Windows on the preparation clone.
4. Remove or disconnect source-specific items:
   - static production IPs
   - source-specific application services
   - monitoring identity if it is not clone-safe
   - mounted Windows ISO if not needed
5. Run `scripts/windows/Prepare-IaCTemplate.ps1` inside the preparation clone.
6. Wait for Sysprep to shut down the VM.
7. Confirm the VM is powered off in vCenter.
8. Convert the powered-off preparation VM to a template.
9. Point OpenTofu `source_vm` to the new template path.
10. Use `windows-template.auto.tfvars.example` as the starting point for OpenTofu-managed Windows VMs.

## Clone Preparation Command

Use `DB-Datastore` for this source unless the template is first moved to a host/cluster with access to `MSA2060-Datastore2`.

```sh
source /opt/appserver/config/iac/vcenter.env
scripts/create-windows-sysprep-clone.sh \
  --source "/Datacenter SVB/vm/Discovered virtual machine/KPS-Reatime" \
  --name "tpl-windows-server-2025-kps-reatime" \
  --folder "/Datacenter SVB/vm/IaC-Lab" \
  --host-ip "10.0.1.1" \
  --datastore "DB-Datastore" \
  --network "KPS Server"
```

## Sysprep Command Inside Windows

Copy or type the content of `scripts/windows/Prepare-IaCTemplate.ps1` inside the preparation clone and run it from an elevated PowerShell session.

The core command is:

```powershell
C:\Windows\System32\Sysprep\Sysprep.exe /generalize /oobe /shutdown
```

## Template Promotion

After Sysprep shuts the preparation clone down:

```sh
source /opt/appserver/config/iac/vcenter.env
scripts/promote-windows-sysprep-template.sh \
  --vm "/Datacenter SVB/vm/IaC-Lab/tpl-windows-server-2025-kps-reatime"
```

## OpenTofu Management

After the template exists:

1. Copy `opentofu/environments/windows-lab/windows-template.auto.tfvars.example` to `windows.auto.tfvars`.
2. Keep `create_vm=false`.
3. Run `tofu validate` and `tofu plan`.
4. Set `create_vm=true` only for the approved managed VM test.
5. Prefer one VM first.

## Current Constraints

- vCenter reports the source guest ID as `windows2019srvNext_64Guest`, even though the intended guest is Windows Server 2025.
- `KPS-Reatime` currently lives on a host/cluster path that can clone to `DB-Datastore`; clone to `MSA2060-Datastore2` failed in Phase 5B because the selected source host cannot access that datastore.
- Phase 5B showed the clone disks were thick on `DB-Datastore`, so free space must be watched closely.
- The source VM still has a Windows ISO attached; remove/disconnect it before final template promotion if the template should not inherit it.

## Stop Conditions

Stop and do not convert to template if:

- Sysprep fails.
- The VM does not shut down cleanly after Sysprep.
- The preparation clone still has production IP/application identity.
- `DB-Datastore` free space is too low for another 500 GB clone.
- The wrong VM path is selected.
