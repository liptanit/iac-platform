# Phase 53: IIS/API Server Baseline

Windows inventory hosts with `role = "api-server"` now run an IIS/API Server
baseline during `postclone-windows.yml`. The role follows the PowerShell
baseline supplied by Payong on 2026-07-12.

The baseline installs the full IIS feature set for ASP.NET, Classic ASP, CGI,
WebSockets, FTP, SMTP, IIS management tools, .NET Framework/WCF activation, and
URL Rewrite. It enables the IIS Management Service, registers ASP.NET 4.x when
the legacy tool is present, enables 32-bit applications on DefaultAppPool, opens
HTTP/HTTPS firewall rules, restarts IIS, and writes an IaC marker.

The role is intentionally scoped:

- `role = "api-server"` runs IIS/API baseline.
- `role = "sql-server"` runs SQL baseline, not IIS baseline.
- Other Windows roles skip both role-specific baselines.

The API Server phase does not deploy application code, create sites/app pools,
join a domain, install EDR, or configure TLS certificates. Those remain explicit
post-provision policy steps.
