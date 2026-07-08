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
