# King Power IaC Platform

Local IaC repository for OpenTofu + Ansible on sysap (10.1.0.15).

Primary vCenter: 10.0.1.90

## Current phase

Phase 3 creates the repository skeleton and read-only vSphere discovery plan. It does not create, modify, or delete VMs by default.

## Layout

- opentofu/modules/vsphere-linux-vm: reusable Linux VM module
- opentofu/environments/lab: lab environment root module
- ansible/playbooks: baseline and smoke-test playbooks
- ansible/inventories/lab: lab inventory
- docs: design notes and runbooks
- scripts: helper commands

## Secrets

Do not commit vCenter passwords, SSH private keys, or vault passwords. Phase 3 uses root-only runtime credentials from /opt/appserver/config/iac/vcenter.env for read-only validation.
