# Run inside the Windows preparation clone, not on the original source VM.
# This clears machine-specific Windows identity and shuts the VM down for template promotion.

$ErrorActionPreference = "Stop"

Write-Host "Phase 5C IaC template preparation starting..."

$sysprep = Join-Path $env:SystemRoot "System32\Sysprep\Sysprep.exe"
if (-not (Test-Path $sysprep)) {
    throw "Sysprep.exe not found at $sysprep"
}

Write-Host "Current computer name: $env:COMPUTERNAME"
Write-Host "VM will generalize, enter OOBE on next boot, and shut down."
Write-Host "Do not run this on the original production/source VM."

Start-Process -FilePath $sysprep -ArgumentList "/generalize", "/oobe", "/shutdown" -Wait
