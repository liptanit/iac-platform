# Phase 5 Windows Template Workflow

Date: 2026-07-08
vCenter: 10.0.1.90
Source VM selected by owner: `/Datacenter SVB/vm/Discovered virtual machine/KPS-Reatime`

## Source Assessment

- VM name: `KPS-Reatime`
- Power state: `poweredOff`
- Guest ID: `windows2019srvNext_64Guest`
- CPU: 4
- Memory: 32768 MB
- Network: `KPS Server`
- Disks: approximately 300 GB and 638 GB
- Existing CD-ROM: Windows ISO is attached on the source VM
- VMware Tools status from vCenter while powered off: not running, expected for a powered-off VM

## Risk Notes

The source VM is large and likely carries machine-specific Windows identity, local accounts, installed software, and possibly static network/application configuration. A direct clone can be technically valid, but a reusable Windows template should be treated differently from the Ubuntu cloud-init template.

Before enabling `create_vm=true` for a real Windows clone, approve these points:

- Target datastore has enough free capacity for a 900 GB class clone.
- Source VM is clean enough to become a template, or a clone will be manually generalized with Sysprep first.
- Windows activation, hostname/domain identity, local admin policy, and application services are understood.
- Guest customization should be enabled only after VMware Tools and Sysprep readiness are confirmed.
- Any source ISO/CD-ROM should not be inherited by the clone workflow; the module sets a client-device CD-ROM.

## Implementation

Windows provisioning is isolated from the Linux NoCloud workflow:

- Module: `opentofu/modules/vsphere-windows-vm`
- Environment: `opentofu/environments/windows-lab`
- Example variables: `opentofu/environments/windows-lab/windows.auto.tfvars.example`

The default example keeps `create_vm=false`. With that setting, plans only resolve vCenter objects and create no VM resources.

## Controlled Test Path

1. Copy the example tfvars to `windows.auto.tfvars`.
2. Keep `create_vm=false` and run `tofu init`, `tofu validate`, and `tofu plan`.
3. For a real test, set one VM entry, confirm datastore capacity, then set `create_vm=true`.
4. Keep `customize_windows=false` for the first clone if Sysprep/customization readiness is unknown.
5. After successful clone validation, destroy the lab clone unless it is promoted intentionally.

## Next Phase Recommendation

Phase 5B should either:

- create one temporary Windows clone from `KPS-Reatime` and immediately validate power/network/vCenter identity before destroy, or
- create a separate `tpl-windows-kps-reatime` clone/template after confirming the 900 GB storage impact and Windows generalization approach.
