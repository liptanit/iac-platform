# King Power IaC Platform

Local IaC repository for OpenTofu + Ansible on sysap (10.1.0.15).

Primary vCenter: 10.0.1.90

## Current phase

Phase 9 provides a repeatable Windows rollout workflow around the proven
OpenTofu + Ansible path. The current managed Windows VMs are
`iac-win-managed-7b-01` (`10.1.0.115`) and `iac-win-managed-8-02`
(`10.1.0.116`).

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

## Secrets

Do not commit vCenter passwords, Windows Administrator passwords, SSH private
keys, or vault passwords. Runtime credentials live under
`/opt/appserver/config/iac/`, especially `vcenter.env` and
`windows-ansible.env`.

## Windows rollout

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
