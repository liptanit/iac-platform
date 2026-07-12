# Phase 51: SQL Server Install and Baseline Automation

Phase 51 adds opt-in SQL Server automation for Windows VMs created with the
`sql-server` role blueprint.

## Activation Model

- Inventory host must include `role = "sql-server"`.
- `scripts/generate-windows-ansible-inventory.py` emits host variables:
  - `iac_role`
  - `iac_role_profile`
  - `iac_cpu`
  - `iac_memory_mb`
  - `iac_disks`
- `ansible/playbooks/postclone-windows.yml` runs the existing
  `windows_postclone` role first, then `windows_sql_server`.
- Non-SQL roles skip the SQL role without failing the play.

## SQL Role Behavior

The `windows_sql_server` role:

- Creates SQL data/log/tempdb/backup directories.
- Opens the managed SQL firewall rule `IaC SQL Server 1433` when enabled.
- Installs SQL Server when `windows_sql_install_source` points to a path
  containing `setup.exe`, or when a controller-cached SQL ISO is available and
  can be copied to the guest and mounted.
- Configures max server memory, ad hoc workload optimization, backup
  compression default, and remote DAC after installation when `sqlcmd.exe` is
  available.
- Writes `C:\ProgramData\IaC\sql-baseline.txt`.

## Required Runtime Input for Install

Preferred production flow is Windows template plus SQL ISO automation:

1. Select the normal Windows template in Create VM.
2. Select role `sql-server`.
3. Adjust CPU, RAM, and total disk size in the Create VM form if the blueprint
   defaults are not desired.
4. Ensure the SQL ISO is cached on the Ansible controller:

```bash
ANSIBLE_SQL_ISO_CONTROLLER_PATH=/opt/appserver/cache/iac/installers/sql-server-2022-standard-en.iso
```

The role copies that ISO to `C:\Temp\SQLInstall`, mounts it, and uses the
mounted `setup.exe` automatically.

Alternatively, set this in a root-only Ansible environment file or Semaphore
secret before requesting install:

```bash
ANSIBLE_SQL_INSTALL_SOURCE='D:\SQL2022'
```

The source may be a mounted ISO path, local folder, or approved UNC path. If the
source and cached ISO are both missing, the default production policy does not
fail the rollout; it records SQL as missing and leaves evidence for the
operator.

## Production Defaults

The production postclone policy uses conservative defaults:

- Instance: `MSSQLSERVER`
- Collation: `Thai_CI_AS`
- Port: `1433`
- Max server memory: `53248` MB for the 64 GB SQL blueprint
- Install source missing: warn/evidence only, no hard failure

## Out of Scope

- Database creation
- Application login/user provisioning
- Always On / clustering
- Domain join
- EDR enablement
- Backup restore validation beyond baseline evidence
