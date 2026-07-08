# Phase 8 Windows Controlled Rollout

Phase 8 extends the proven single Windows VM workflow into a controlled
multi-VM rollout while keeping the existing Phase 7B validation VM in state.

Inventory:

```text
examples/windows-vms.phase8.toml
```

The first VM is the existing `iac-win-managed-7b-01` at `10.1.0.115`. The
second VM, `iac-win-managed-8-02` at `10.1.0.116`, is added to prove that the
OpenTofu `windows_vms` map can safely grow from one managed Windows VM to
multiple managed Windows VMs.

Generate OpenTofu input:

```bash
scripts/generate-windows-tfvars.py \
  --config examples/windows-vms.phase8.toml \
  --output opentofu/environments/windows-lab/windows.auto.tfvars \
  --create-vm
```

Generate WinRM inventory:

```bash
scripts/generate-windows-ansible-inventory.py \
  --config examples/windows-vms.phase8.toml \
  --output ansible/inventories/windows/hosts.ini
```

Run order:

1. Precheck that the new IP and VM name are unused.
2. Run `tofu validate` and a detailed plan.
3. Apply only when the plan is an add-only change for the new VM.
4. Run `ansible/playbooks/ping-windows.yml`.
5. Run `ansible/playbooks/baseline-windows.yml`.
6. Run `ansible/playbooks/validate-windows-shell.yml`.
