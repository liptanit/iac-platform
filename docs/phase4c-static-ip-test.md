# Phase 4C Static IP Clone Test

Date: 2026-07-08

## Result

Phase 4C validated Ubuntu template cloning with a static IPv4 address.

- Template: `tpl-ubuntu-24.04-server`
- Test VM: `iac-lab-ubuntu-4c`
- Static IPv4: `10.1.0.25/24`
- Gateway: `10.1.0.254`
- DNS: `10.1.0.9`, `10.1.0.254`
- Network: `SVB Server`
- Datastore: `MSA2060-Datastore2`
- Provisioning method: OpenTofu clone plus NoCloud seed ISO

## Findings

The Ubuntu cloud image template did not accept a `network-config` vApp property.
VMware Guest Customization also failed while setting guest network properties.

The working approach is to attach a NoCloud seed ISO that contains:

- `user-data`
- `meta-data`
- `network-config`

The vSphere template still requires a client CDROM for OVF/vApp transport, so the
OpenTofu module attaches both:

- a client CDROM for the template requirement
- a datastore ISO CDROM for the NoCloud seed

## Verification

The final test VM passed:

- ping to `10.1.0.25`
- SSH as `iacadmin` using the IaC key
- passwordless sudo
- cloud-init status `done` with no errors
- Ansible `ping`
- Ansible baseline playbook

The test VM was destroyed after validation to release `10.1.0.25`.
