# Phase 10 Linux Rollout Workflow

Phase 10 mirrors the Windows rollout flow for Ubuntu clones.

It uses:

- Ubuntu template: `tpl-ubuntu-24.04-server`
- Static IPv4 through NoCloud seed ISO
- OpenTofu lab environment: `opentofu/environments/lab`
- Ansible SSH inventory: `ansible/inventories/linux/hosts.ini`
- Linux baseline role: `ansible/roles/common`

## Approved Target Inventory

Current requested inventory:

```text
examples/linux-vms.phase10.toml
```

Requested IPs:

- `iac-linux-managed-10-01` / `10.1.0.131`
- `iac-linux-managed-10-02` / `10.1.0.132`

The runner has a ping-based IP conflict guard. It blocks clone/apply when a
requested IP already replies unless `--allow-used-ip` is explicitly supplied.

## Standard Commands

Plan only:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-linux-rollout.py --config examples/linux-vms.phase10.toml
```

Apply and validate:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-linux-rollout.py \
  --config examples/linux-vms.phase10.toml \
  --apply \
  --report
```

Validation/report only:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-linux-rollout.py \
  --config examples/linux-vms.phase10.toml \
  --validate-only \
  --report
```

## Baseline

The Linux baseline:

- installs `curl`, `ca-certificates`, `gnupg`, `qemu-guest-agent`, and
  `zabbix-agent2`
- adds the Zabbix 7.4 Ubuntu repository when needed
- writes `/var/lib/iac/baseline.txt`
- sets timezone to `Asia/Bangkok`
- starts `qemu-guest-agent`
- configures Zabbix Agent 2:
  - `Server=10.1.0.15`
  - `ServerActive=10.1.0.15`
  - `HostMetadata=Linux`
- writes per-host JSON reports when `--report` is supplied

## Safety Gates

1. Generate Ansible inventory from TOML.
2. Precheck requested IPs and VM names.
3. Generate and upload NoCloud seed ISOs.
4. Generate OpenTofu tfvars with `create_vm=true`.
5. Run `tofu fmt`, `init`, `validate`, and detailed plan.
6. Block destroy actions by default.
7. Apply only with `--apply`.
8. Validate SSH, cloud-init, marker, package baseline, and Zabbix Agent 2.
