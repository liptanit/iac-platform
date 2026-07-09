# Runbook

## Read-only lab plan

Run as root while Phase 3 credentials are root-only:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform/opentofu/environments/lab
set -a
. /opt/appserver/config/iac/iac.env
. /opt/appserver/config/iac/vcenter.env
set +a
tofu init -input=false
tofu validate
tofu plan -input=false -var-file=lab.auto.tfvars.example
```

The default create_vm=false makes this a read-only data-source plan.

## Ansible local smoke test

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
set -a
. /opt/appserver/config/iac/iac.env
set +a
/opt/appserver/venv-iac-ansible/bin/ansible-playbook -i ansible/inventories/lab/hosts.ini ansible/playbooks/ping.yml
```

## Phase 9 Windows rollout

Use the Phase 9 runner for repeatable Windows VM changes. It generates
OpenTofu and Ansible files from one TOML inventory, blocks destroy actions by
default, and writes a report under `/opt/appserver/backups/iac`.

Plan only:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-windows-rollout.py --config examples/windows-vms.phase8.toml
```

Apply and validate:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-windows-rollout.py --config examples/windows-vms.phase8.toml --apply
```

Validation only:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-windows-rollout.py --config examples/windows-vms.phase8.toml --validate-only
```

Post-clone production baseline and report:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/run-windows-rollout.py \
  --config examples/windows-vms.phase8.toml \
  --validate-only \
  --postclone \
  --postclone-vars examples/windows-postclone-policy.example.yml \
  --report
```
