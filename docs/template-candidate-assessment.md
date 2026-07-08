# Phase 4A Template Candidate Assessment

Date: 2026-07-08
vCenter: 10.0.1.90
Scope: read-only VM inventory analysis. No VM was modified.

## Inventory Summary

- Total VMs: 68
- Powered on: 33
- Powered off: 35
- Existing templates: 0
- Linux VMs: 6
- Windows VMs: 62

## Recommended Linux Candidate

### Ubuntu20.4

- Guest OS: Ubuntu Linux (64-bit)
- Power state: poweredOff
- CPU: 4
- Memory: 32768 MB
- Disk: 200 GB
- Cluster: SVB Cluster
- Datastore: MSA2060-Datastore2
- Networks: IT, SVB Server
- IP: none reported
- Risk flags: none from heuristic scan

Assessment: best available Linux candidate. It is powered off, has no active IP, and has a template-like OS/name. It is not ideal as a clean standard template because memory and disk are larger than a normal baseline template, so confirm whether it is safe to convert/clone and whether it has app/data/custom config before using it.

## Recommended Windows Candidate

### Win-2019

- Guest OS: Microsoft Windows Server 2019 (64-bit)
- Power state: poweredOff
- CPU: 4
- Memory: 8192 MB
- Disk: 200 GB
- Cluster: SVB Cluster
- Datastore: MSA2060-Datastore1
- Networks: SVB Server
- IP: none reported
- Risk flags: none from heuristic scan

Assessment: best available Windows Server candidate. It is powered off, has no active IP, and is a modern server OS compared with Windows7/Windows 2003 candidates.

## Candidates To Avoid Initially

- Powered-on production-like Linux VMs: `SVB-WebPortal`, `s4kpposapip3`, `s4kpposapid3`, `SVB-KPSTMSVC`.
- `PFSense`: detected as Linux/CentOS by VMware but name/function indicates network appliance, not an OS template.
- `Windows7`, `Windows XP`, Windows Server 2003 VMs: old OS, not suitable as modern standard templates.
- Large application/data clones such as `SERVERKPS1_N_Clone2`: large disk/resource profile and likely app/data-specific.

## Recommendation

Use `Ubuntu20.4` only after owner confirms it is not production and is safe to clone or convert. For a cleaner long-term IaC platform, create new golden templates instead:

- `tpl-ubuntu-24.04-server`
- `tpl-windows-server-2019` or `tpl-windows-server-2022`

Minimum template requirements:

- VMware Tools installed and healthy
- cloud-init or VMware guest customization ready
- No static production IP, no app data, no machine-specific secrets
- Patched OS baseline
- Local admin/SSH setup according to policy
- Zabbix agent either absent or configured to re-register safely after clone
