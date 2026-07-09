# Phase 11 IaC Operations Layer

Phase 11 adds an operator-facing wrapper around the existing Windows and Linux
rollout runners. Operators should use `scripts/iac-ops.py` for normal
create/change/validation work instead of calling `tofu apply` directly.

## Environments

Environment profiles live under `ops/environments`:

- `prod.toml` is enabled and points to the current managed Windows and Linux inventories.
- `test.toml` and `dev.toml` are disabled templates until real VLAN/IP ranges are approved.

Each profile maps OS-specific inventories:

- `ops/inventories/<env>/windows.toml`
- `ops/inventories/<env>/linux.toml`

## Plan

Windows:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/iac-ops.py plan --env prod --platform windows --report
```

Linux:

```bash
cd /opt/appserver/apps/iac/repositories/iac-platform
scripts/iac-ops.py plan --env prod --platform linux --report
```

Every run creates:

- `/opt/appserver/backups/iac/phase11_<env>_<platform>_<action>_<timestamp>/`
- `prechange-backup.tgz`
- `phase11-commands.log`
- `phase11-operation-summary.md`
- a final `.tgz` archive of the whole operation folder

The plan output prints the apply approval token for the same environment,
platform, selected inventory, and git commit.

Linux plan-only runs skip NoCloud seed ISO upload so a read-only plan does not
write to the datastore. Apply runs still generate and upload seed media before
OpenTofu apply.

The wrapper accepts `--report` on plan commands for operator consistency, but
per-host Ansible reports are generated only during apply or validate runs.

## Apply

Apply is blocked unless both approval fields are present.

```bash
scripts/iac-ops.py apply \
  --env prod \
  --platform linux \
  --report \
  --approved-by "Payong" \
  --approval-token "APPROVE-PROD-LINUX-APPLY-XXXXXXXXXXXX"
```

For Windows post-clone policy:

```bash
scripts/iac-ops.py apply \
  --env prod \
  --platform windows \
  --postclone \
  --postclone-vars examples/windows-postclone-policy.production.yml \
  --report \
  --approved-by "Payong" \
  --approval-token "APPROVE-PROD-WINDOWS-APPLY-XXXXXXXXXXXX"
```

## Validate

Validation can run without approval because it is read-only/configuration
baseline validation through Ansible.

```bash
scripts/iac-ops.py validate --env prod --platform linux --report
scripts/iac-ops.py validate --env prod --platform windows --postclone --postclone-vars examples/windows-postclone-policy.production.yml --report
```

## Destroy

Destroy is intentionally not implemented in the Phase 9/10 rollout runners.
The Phase 11 wrapper reserves the action and keeps it blocked by default. Before
enabling destroy, add a dedicated destroy runner that:

1. Requires `--allow-destroy`.
2. Requires an approval token and approver name.
3. Writes a full state/config backup before planning.
4. Runs a `tofu plan -destroy` and archives the plan before apply.
5. Applies only the archived destroy plan.

## Web UI / Runner Recommendation

Use a staged approach:

1. Keep `scripts/iac-ops.py` as the only write path first.
2. Add Gitea for repository review and pull-request approval if Git review is needed.
3. Add Semaphore after the wrapper is stable, with job templates that call only
   `scripts/iac-ops.py plan`, `apply`, and `validate`.
4. Store Semaphore credentials in `/opt/appserver/config/iac`, not in the repo.

Semaphore is a better first UI for operations because it natively models
inventories, credentials, job templates, approvals, and Ansible output. Gitea
Runner is better later if the team wants CI from pull requests.

## Semaphore UI

Semaphore should call `ansible/playbooks/semaphore-iac-ops.yml`, not raw
OpenTofu commands. The playbook always changes directory back to the real repo
at `/opt/appserver/apps/iac/repositories/iac-platform` before running
`scripts/iac-ops.py`, so it uses the current local state and evidence paths.

Suggested Semaphore templates:

- `Linux Prod Plan`: `-e iac_action=plan -e iac_platform=linux`
- `Windows Prod Plan`: `-e iac_action=plan -e iac_platform=windows`
- `Linux Prod Validate`: `-e iac_action=validate -e iac_platform=linux`
- `Windows Prod Validate`: `-e iac_action=validate -e iac_platform=windows -e iac_postclone=true`
- `Linux Prod Apply`: add survey prompts for `iac_approved_by` and `iac_approval_token`.
- `Windows Prod Apply`: add survey prompts for `iac_approved_by` and `iac_approval_token`, plus `iac_postclone=true` when post-clone policy should run.
