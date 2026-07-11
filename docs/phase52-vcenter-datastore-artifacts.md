# Phase 52: vCenter Datastore Artifact Source

Phase 52 defines a reusable source catalog for ISO, installer, script, and package files stored in vCenter datastores.

The first consumer is SQL Server media for the `sql-server` Windows role, but the design is intentionally generic so future roles can use Windows ISOs, application installers, offline agents, or scripts without hard-coding file paths into Ansible roles.

## Catalog

Artifact catalog entries live in TOML and use `[[artifact]]` records.

Example:

```toml
[[artifact]]
id = "sql-server-2022-standard-en"
name = "SQL Server 2022 Standard English ISO"
kind = "iso"
source_vcenter_id = "svb-vc02"
datastore = "Volume_Backup_DS01"
path = "ISO/SW_DVD9_NTRL_SQL_Svr_Standard_Edtn_2022_64Bit_English_OEM_VL_X23-28393.iso"
allowed_roles = ["sql-server"]
sha256 = ""
active = true
```

The sample catalog is `examples/artifact-sources.example.toml`.

## CLI

`scripts/iac-artifact-source.py` provides read-only validation and dry-run copy planning.

List sources:

```bash
scripts/iac-artifact-source.py --catalog examples/artifact-sources.example.toml list
```

Validate that the source file exists in the current runtime vCenter:

```bash
export IAC_VCENTER_ID=svb-vc02
export IAC_VCENTER_ENDPOINT=https://10.0.1.9
export IAC_VCENTER_USERNAME='...'
export IAC_VCENTER_PASSWORD='...'
export IAC_VCENTER_DATACENTER='Datacenter'

scripts/iac-artifact-source.py validate sql-server-2022-standard-en
```

Plan a cross-vCenter copy without moving bytes:

```bash
scripts/iac-artifact-source.py plan-copy sql-server-2022-standard-en \
  --destination-vcenter-id svb-vc01 \
  --destination-datastore Web-Datastore \
  --destination-path ISO/SW_DVD9_NTRL_SQL_Svr_Standard_Edtn_2022_64Bit_English_OEM_VL_X23-28393.iso
```

Evidence is written under `/opt/appserver/backups/iac/phase52_artifact_sources` by default.

## IaC Control UI

IaC Control adds `/artifacts` as **Artifact Sources**.

It supports:

- register artifact source metadata
- validate source datastore path with the saved vCenter credential
- create a dry-run copy plan from one vCenter/datastore to another
- record evidence under `/opt/appserver/backups/iac/phase52_artifacts`

The UI does not copy large ISO files in Phase 52.

## Cross-vCenter Copy Design

Same-vCenter copies can use a datastore-side copy if the source and destination differ.

Cross-vCenter copies should use a controlled staging workflow:

1. Validate source file exists in the source datastore.
2. Validate destination path is empty.
3. Download the source datastore file to a controlled staging directory on the IaC runner.
4. Verify `sha256` when configured.
5. Upload to the destination vCenter/datastore/path.
6. Validate the destination file exists.
7. Remove staging data.
8. Record source, destination, checksum, transfer timings, and validation evidence.

This mirrors the template transfer pattern but treats the file as a datastore artifact instead of a VM template.

## Guardrails

- Artifact IDs are stable and role-facing. Roles should refer to `artifact_id`, not a raw path.
- `allowed_roles` restricts which VM roles may consume a source.
- Validation requires matching vCenter runtime context.
- Copy planning blocks identical source/destination locations.
- Phase 52 does not attach ISO media to VMs and does not run installers.
- Phase 52 does not perform binary transfer automatically; it creates evidence-backed plans for a later approved worker.

## Phase 53 Handoff

Phase 53 can connect `windows_sql_server` to this catalog:

- resolve `sql_server_2022_standard_iso` or another configured artifact ID
- ensure the artifact is validated for the target vCenter
- if missing on the target vCenter, require an approved copy plan
- attach the datastore ISO to the SQL VM CD/DVD or stage it locally
- mount ISO in Windows, discover `setup.exe`, run unattended install, unmount/disconnect ISO, and record SQL evidence

