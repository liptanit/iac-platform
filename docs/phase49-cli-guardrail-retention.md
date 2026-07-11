# Phase 49: CLI Runtime Guardrail and Backup Retention

## CLI Runtime Guardrail

Use IaC Control UI or Semaphore for production operations. They inject the
vCenter registry values, credential reference, placement, state key, approval,
audit, and evidence consistently.

Raw CLI is now guarded for scoped multi-vCenter inventories such as:

- `ops/inventories/prod/windows-svb-vc02.toml`
- `ops/inventories/prod/linux-svb-vc02.toml`

If a scoped inventory is selected, `scripts/iac-ops.py` requires the runtime
vCenter environment to be complete before it runs the rollout runner.

Required for scoped Windows and Linux:

- `IAC_VCENTER_ID`
- `IAC_VCENTER_ENDPOINT` or `IAC_VCENTER_HOST`
- `IAC_VCENTER_USERNAME`
- `IAC_VCENTER_PASSWORD`
- `IAC_VCENTER_DATACENTER`
- `IAC_VCENTER_CLUSTER`
- `IAC_VCENTER_NETWORK`

Additional Linux requirement:

- `IAC_VCENTER_DATASTORES`

Additional Windows requirement:

- `IAC_VCENTER_DATASTORE`

The guardrail also blocks mismatches such as selecting
`windows-svb-vc02.toml` while `IAC_VCENTER_ID=svb-vc01`.

## Backup Retention

Use `scripts/iac-backup-retention.py` to report or safely move old evidence.

Default mode is dry-run:

```bash
python3 scripts/iac-backup-retention.py --older-than-days 30 --keep-recent 80
```

Dry-run writes:

- `retention-report.md`
- `retention-report.json`

To apply, candidates are moved to a trash folder under the backup root instead
of being deleted:

```bash
python3 scripts/iac-backup-retention.py --older-than-days 30 --keep-recent 80 --apply
```

This keeps cleanup recoverable. Do not remove trash contents until the owner has
reviewed the report and confirmed retention policy.

## Recommended Policy

- Keep at least the latest 80 top-level evidence items.
- Keep all evidence newer than 30 days.
- Review retention dry-run weekly.
- Apply cleanup only after checking that no active deployment, approval, or
rollback investigation references the candidate folders.
