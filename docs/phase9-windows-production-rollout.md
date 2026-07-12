# Phase 9 Windows Production Rollout Workflow

Phase 9 turns the proven Windows lab workflow into a repeatable operational
runbook. It keeps the same safety model used in Phase 8: inventory first,
generate files from inventory, plan before apply, and validate every managed VM
after changes.

## Scope

- Source inventory: `examples/windows-vms.phase8.toml` or a copied inventory for
  a new rollout batch.
- OpenTofu environment: `opentofu/environments/windows-lab`.
- Ansible inventory: `ansible/inventories/windows/hosts.ini`.
- Runtime secrets:
  - `/opt/appserver/config/iac/vcenter.env`
  - `/opt/appserver/config/iac/windows-ansible.env`

Secrets stay outside Git.

Python tooling for the Ansible venv is tracked in
`requirements/ansible-python.txt`. WinRM validation requires `pywinrm` and
`requests-ntlm` inside `/opt/appserver/venv-iac-ansible`, not only installed at
the OS package level.

## Standard Command

Plan only:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-windows-rollout.py \
  --config examples/windows-vms.phase8.toml
```

Apply and validate:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-windows-rollout.py \
  --config examples/windows-vms.phase8.toml \
  --apply
```

Validation only for already managed VMs:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-windows-rollout.py \
  --config examples/windows-vms.phase8.toml \
  --validate-only
```

Post-clone production baseline and per-host report for already managed VMs:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-windows-rollout.py \
  --config examples/windows-vms.phase8.toml \
  --validate-only \
  --postclone \
  --postclone-vars examples/windows-postclone-policy.production.yml \
  --report
```

## Safety Gates

The runner:

1. Generates `windows.auto.tfvars` with `create_vm=true` only from the approved
   TOML inventory.
2. Generates the WinRM inventory from the same TOML file.
3. Runs `tofu fmt -check`, `tofu init`, `tofu validate`, and a detailed plan.
4. Blocks destroy actions unless `--allow-destroy` is deliberately supplied.
5. Runs `tofu apply` only when `--apply` is supplied.
6. Runs WinRM ping, Windows baseline, and Windows shell validation after apply
   or in validation-only mode.
7. Optionally runs the post-clone production baseline when `--postclone` is
   supplied.
8. Optionally writes per-host JSON validation reports when `--report` is
   supplied.
9. Writes a timestamped workflow report under `/opt/appserver/backups/iac`.

## Post-Clone Production Baseline

The post-clone baseline is implemented in:

- `ansible/roles/windows_postclone`
- `ansible/playbooks/postclone-windows.yml`
- `ansible/playbooks/report-windows.yml`
- `examples/windows-postclone-policy.example.yml`
- `examples/windows-postclone-policy.production.yml`

Supported policy areas:

- RDP enabled/disabled and firewall rule management.
- Optional domain join with credentials supplied from environment variables.
- Optional automation/local admin account with password supplied from
  `ANSIBLE_AUTOMATION_ADMIN_PASSWORD`.
- Optional Windows shell repair for Windows Server 2025 console/remote black
  desktop cases caused by ShellHost/Explorer/ControlCenter crashes.
- Optional Zabbix Agent 2 install/start.
- Optional EDR install/start through a configured command and service name.
- Windows Update policy, timezone, firewall, ICMP, and audit policy.
- Per-host JSON report with OS, domain, WinRM, RDP, ICMP, Zabbix, hotfix, and
  shell crash signals.

The example policy keeps RDP disabled and does not join a domain or install
agents until the required site-specific values are set.

The current production policy approved on 2026-07-09:

- Enables RDP.
- Does not join a domain.
- Runs the Windows shell repair hook before role-specific IIS/SQL automation to
  avoid the known Windows Server 2025 ShellHost/ControlCenter black desktop
  condition.
- Installs Zabbix Agent 2 through the SYSAP bootstrap script:
  `http://10.1.0.15/agent/windows/Install-ZabbixWindowsAgent.ps1`.
- Points Zabbix `Server` and `ServerActive` to `10.1.0.15`.
- Leaves Trend AI Deep Security / Vision One Endpoint Security disabled until
  the approved installer command, token, and service name are supplied.

## Adding More Windows VMs

1. Copy `examples/windows-vms.phase8.toml` to a new phase/batch inventory.
2. Add one VM at a time unless a larger batch has been reviewed.
3. Use a unique vSphere VM name, Windows computer name, and static IP.
4. Precheck that the VM name is absent and the IP is not already assigned.
5. Run the Phase 9 runner without `--apply`.
6. Confirm the plan is only the intended add/change.
7. Run again with `--apply`.
8. Keep the generated report path in the daily memory or change record.

## Rollback

Do not destroy a VM casually after it has been handed to users. If a rollout
fails before handover:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform/opentofu/environments/windows-lab
set -a
. /opt/appserver/config/iac/vcenter.env
set +a
tofu plan -destroy -target='module.windows_vm["VM_NAME"]'
```

Review the destroy target carefully before applying. The Phase 9 runner blocks
destroy by default because a wrong destroy can remove working servers.

## Current Managed Windows VMs

As of the Phase 8 handoff:

- `iac-win-managed-7b-01` / `10.1.0.115`
- `iac-win-managed-8-02` / `10.1.0.116`

Both passed WinRM ping, baseline, ICMP, and shell validation.
