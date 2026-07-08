# Architecture

The initial platform runs on 10.1.0.15 and uses OpenTofu for vSphere infrastructure lifecycle and Ansible for guest configuration.

- OpenTofu CLI: /usr/bin/tofu
- Ansible venv: /opt/appserver/venv-iac-ansible
- Non-secret defaults: /opt/appserver/config/iac/iac.env
- Root-only vCenter runtime credential: /opt/appserver/config/iac/vcenter.env
- Plugin cache: /opt/appserver/data/iac/tofu-plugin-cache
- Local state path for lab: /opt/appserver/data/iac/state/lab

No CI/Git web UI is installed in Phase 3.
