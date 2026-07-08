# Phase 5B Windows Powered-Off Clone Test

Date: 2026-07-08
Source VM: `/Datacenter SVB/vm/Discovered virtual machine/KPS-Reatime`
Test VM: `/Datacenter SVB/vm/IaC-Lab/iac-lab-win-5b-01`

## Source Recheck

- Power state: `poweredOff`
- Guest ID reported by vCenter: `windows2019srvNext_64Guest`
- CPU: 4
- Memory: 32768 MB
- Network: `KPS Server`
- Disk 1: 300 GB
- Disk 2: 200 GB
- CD-ROM: Windows ISO attached from `DB-Datastore`

The owner noted the guest is Windows Server 2025. vCenter still reports the guest ID as `windows2019srvNext_64Guest`, which may be VMware's closest guest family mapping for this VM.

## OpenTofu Check

The Windows module validated successfully and the `windows-lab` environment produced a safe plan with `create_vm=false`.

The vSphere provider version currently in use does not support a `power_on=false` argument on `vsphere_virtual_machine`. Because `KPS-Reatime` is not confirmed sysprepped/generalized, Phase 5B used `govc vm.clone -on=false` for the controlled powered-off clone test.

## Clone Attempts

1. Clone to `MSA2060-Datastore2` using `SVB Cluster` placement failed with `The operation is not allowed in the current state`.
2. Clone to `MSA2060-Datastore2` with explicit source host placement failed because the source host could not access `MSA2060-Datastore2`.
3. Clone to source-accessible `DB-Datastore` with `-on=false` succeeded.

Successful command shape:

```sh
govc vm.clone \
  -vm "/Datacenter SVB/vm/Discovered virtual machine/KPS-Reatime" \
  -folder "/Datacenter SVB/vm/IaC-Lab" \
  -host.ip=10.0.1.1 \
  -ds "DB-Datastore" \
  -net "KPS Server" \
  -net.adapter=e1000e \
  -on=false \
  "iac-lab-win-5b-01"
```

## Validation

The clone was created successfully and stayed powered off.

- Power state: `poweredOff`
- Guest ID: `windows2019srvNext_64Guest`
- CPU: 4
- Memory: 32768 MB
- Network: `KPS Server`
- Disk 1: 300 GB
- Disk 2: 200 GB
- CD-ROM ISO inherited from source

The clone disks were created as thick disks on `DB-Datastore`, even though the source VM had been reduced to 500 GB. Free space dropped sharply during the test, so Windows clone/template work should not continue on `DB-Datastore` without a storage decision.

## Cleanup

The test VM was destroyed immediately after validation.

- vCenter no longer finds `iac-lab-win-5b-01`
- Datastore folder `iac-lab-win-5b-01` was removed
- No datastore file path containing `iac-lab-win-5b-01` was found after cleanup
- Source VM `KPS-Reatime` remained powered off

## Recommendations

- Do not power on clones from `KPS-Reatime` until Windows identity, Sysprep, activation, hostname, domain/workgroup, and IP policy are confirmed.
- Remove or disconnect the source CD-ROM ISO before promoting a reusable template, or enforce a client-device CD-ROM in the final workflow.
- Avoid `DB-Datastore` for repeated Windows clone testing unless enough free space is guaranteed.
- If the final target must be `MSA2060-Datastore2`, move or clone the Windows source/template to a host/cluster that has access to that datastore first.
- For OpenTofu-managed Windows VMs, either use a sysprepped template where provider power-on is acceptable, or create a powered-off clone with `govc` and import it into OpenTofu state afterward.
