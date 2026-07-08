# Ubuntu 24.04 Template

Template name: `tpl-ubuntu-24.04-server`

Source: official Canonical Ubuntu 24.04 cloud image OVA from `cloud-images.ubuntu.com/releases/24.04/release/`.

Created on: 2026-07-08

Placement:

- vCenter: `10.0.1.90`
- Datacenter: `Datacenter SVB`
- Folder: `IaC-Lab`
- Cluster/resource pool: `SVB Cluster / Resources`
- Datastore: `MSA2060-Datastore2`
- Network: `SVB Server`

Hardware:

- CPU: 2
- RAM: 4096 MB
- Disk: 40 GB
- Guest OS: Ubuntu Linux (64-bit)

Notes:

- The template was imported from a cloud-init-ready OVA and was not booted before marking as a template. This keeps first-boot cloud-init behavior clean for clones.
- `Web-Datastore` rejected the OVA import with `The virtual machine is not supported on the target datastore`; import succeeded on `MSA2060-Datastore2`.
- OpenTofu can look up the template and produce a clone plan with `create_vm=true`; no clone has been applied yet.
