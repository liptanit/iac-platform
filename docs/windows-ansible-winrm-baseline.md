# Windows Ansible WinRM Baseline

Phase 7 adds the first Windows Ansible baseline workflow for OpenTofu-created
Windows VMs.

## Files

- `ansible/inventories/windows/hosts.ini.example`
- `ansible/playbooks/ping-windows.yml`
- `ansible/playbooks/baseline-windows.yml`
- `scripts/generate-windows-ansible-inventory.py`

## Credentials

Do not commit Windows credentials to the repo.

Export credentials only in the shell that runs Ansible, or store them in a
root-only file outside the repo such as `/opt/appserver/config/iac/windows-ansible.env`.

Example environment file:

```sh
export ANSIBLE_WINDOWS_USER='Administrator'
export ANSIBLE_WINDOWS_PASSWORD='REDACTED'
```

Then load it:

```sh
set -a
. /opt/appserver/config/iac/windows-ansible.env
set +a
```

## Inventory

Generate an inventory from the same TOML file used for Windows OpenTofu tfvars:

```sh
/opt/appserver/apps/iac/repositories/iac-platform/scripts/generate-windows-ansible-inventory.py \
  --config /opt/appserver/apps/iac/repositories/iac-platform/examples/windows-vms.example.toml \
  --output /opt/appserver/apps/iac/repositories/iac-platform/ansible/inventories/windows/hosts.ini
```

The generated inventory maps each `[[vm]]` name to its `ipv4_address`. Keep the
real `hosts.ini` uncommitted if it contains environment-specific targets. The
checked-in `hosts.ini.example` is only a template.

## Smoke Test

```sh
cd /opt/appserver/apps/iac/repositories/iac-platform
ansible -i ansible/inventories/windows/hosts.ini windows -m ansible.windows.win_ping
```

or:

```sh
ansible-playbook -i ansible/inventories/windows/hosts.ini ansible/playbooks/ping-windows.yml
```

## Baseline

```sh
ansible-playbook -i ansible/inventories/windows/hosts.ini ansible/playbooks/baseline-windows.yml
```

The baseline currently:

- creates `C:\ProgramData\IaC`
- writes a baseline marker file
- sets timezone to `SE Asia Standard Time`
- enables ICMPv4 echo for later ping validation
- ensures WinRM service is running

## Phase 7 Notes

Phase 5F confirmed TCP/5985 was reachable from sysap to a Windows clone on the
SVB Server network. If WinRM auth fails, verify the local Administrator password
or configure a dedicated local automation account in the Windows template before
running Sysprep.
