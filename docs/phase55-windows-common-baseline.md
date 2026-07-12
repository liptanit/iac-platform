# Phase 55: Windows Common Baseline Matrix

All Windows VM roles share the same common baseline before role-specific
configuration. Role-specific automation such as IIS/API Server and SQL Server
runs after the common baseline.

## Applies To

- General Windows Server VMs
- API Server role VMs
- SQL Server role VMs

## Current Common Baseline

| Area | Status | Implementation |
| --- | --- | --- |
| VMware Tools | Template/runtime required | Inherited from the Windows template and validated through vCenter/guest checks. |
| Timezone | Automated | `windows_postclone` sets `SE Asia Standard Time`. |
| Windows Firewall | Automated | Firewall profiles are enabled. ICMP validation, RDP, IIS, and SQL rules are managed by IaC. |
| RDP policy | Production-enabled | Production post-clone policy enables RDP and the managed `IaC RDP 3389` rule. |
| WinRM | Required | Used for post-clone automation and validation. |
| Zabbix Agent 2 | Production-enabled | Installed by SYSAP bootstrap script and configured for server `10.1.0.15`. |
| Windows shell black-screen repair | Production-enabled | Runs Winlogon Shell/Userinit normalization, DISM, SFC, AppX shell re-registration, and reboot before role-specific automation. |
| Audit policy | Automated | Logon/logoff/account/audit-policy subcategories are configured. |
| Automation local admin / PAM user | Hook available | `windows_automation_admin_name` and `ANSIBLE_AUTOMATION_ADMIN_PASSWORD` can create a controlled local admin when approved. |
| XDR / EDR | Hook available | `windows_edr_install_command` and `windows_edr_service_name` are placeholders until the approved installer/token/service name are supplied. |
| Deep Security / Vision One | Pending | Needs approved installer source, activation/token policy, service name, and reboot behavior before enabling. |

## Role-Specific Layers

- `api-server`: IIS, ASP.NET Core Hosting Bundle, IIS firewall rules, service
  checks, and API app path permissions.
- `sql-server`: SQL disk layout, SQL ISO attachment, SQL install/baseline,
  SQL firewall rule, and SQL marker/reporting.

## Open Items

1. Confirm the final local admin/PAM account name and password source.
2. Supply approved XDR/EDR installer command, token handling method, and service
   name.
3. Supply approved Deep Security or Vision One installer source, activation
   policy, service name, and validation checks.
4. Decide whether any common baseline item should fail the rollout hard or only
   produce evidence when missing.
