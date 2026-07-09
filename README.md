# King Power IaC Platform

Local IaC repository for OpenTofu + Ansible on sysap (10.1.0.15).

Primary vCenter: 10.0.1.90

## Current phase

Phase 11 adds an operations layer around the proven OpenTofu + Ansible path.
Use `scripts/iac-ops.py` for normal plan/apply/validate work so state/config
backups, reports, and approval gates are captured consistently.

## Layout

- opentofu/modules/vsphere-linux-vm: reusable Linux VM module
- opentofu/modules/vsphere-windows-vm: reusable Windows VM module
- opentofu/environments/lab: lab environment root module
- opentofu/environments/windows-lab: Windows VM rollout environment
- ansible/playbooks: baseline and smoke-test playbooks
- ansible/inventories/lab: lab inventory
- requirements/ansible-python.txt: Python packages expected in the IaC Ansible venv
- docs: design notes and runbooks
- scripts: helper commands
- ops/environments: dev/test/prod operations profiles
- ops/inventories: environment-specific Windows/Linux inventories

## Secrets

Do not commit vCenter passwords, Windows Administrator passwords, SSH private
keys, or vault passwords. Runtime credentials live under
`/opt/appserver/config/iac/`, especially `vcenter.env` and
`windows-ansible.env`.

## Windows rollout

Preferred Phase 11 entry point:

```bash
scripts/iac-ops.py plan --env prod --platform windows --report
```

Plan only:

```bash
scripts/run-windows-rollout.py --config examples/windows-vms.phase8.toml
```

Apply and validate:

```bash
scripts/run-windows-rollout.py --config examples/windows-vms.phase8.toml --apply
```

Run post-clone baseline and per-host reports for managed VMs:

```bash
scripts/run-windows-rollout.py \
  --config examples/windows-vms.phase8.toml \
  --validate-only \
  --postclone \
  --postclone-vars examples/windows-postclone-policy.production.yml \
  --report
```

See `docs/phase9-windows-production-rollout.md` for the complete gate sequence.

## Linux rollout

Preferred Phase 11 entry point:

```bash
scripts/iac-ops.py plan --env prod --platform linux --report
```

Plan only:

```bash
scripts/run-linux-rollout.py --config examples/linux-vms.phase10.toml
```

Apply and validate:

```bash
scripts/run-linux-rollout.py --config examples/linux-vms.phase10.toml --apply --report
```

See `docs/phase10-linux-rollout.md` for the Linux rollout flow.

See `docs/ops/phase11-operations-layer.md` for create/change/destroy runbooks,
automatic backup/report behavior, approval tokens, environment profiles, and the
Semaphore/Gitea runner recommendation.
