data "vsphere_datacenter" "selected" {
  name = var.datacenter
}

data "vsphere_compute_cluster" "selected" {
  name          = var.cluster
  datacenter_id = data.vsphere_datacenter.selected.id
}

data "vsphere_datastore" "selected" {
  name          = var.datastore
  datacenter_id = data.vsphere_datacenter.selected.id
}

data "vsphere_network" "selected" {
  name          = var.network
  datacenter_id = data.vsphere_datacenter.selected.id
}

module "linux_vm" {
  count  = var.create_vm ? 1 : 0
  source = "../../modules/vsphere-linux-vm"

  datacenter_id         = data.vsphere_datacenter.selected.id
  datastore_id          = data.vsphere_datastore.selected.id
  resource_pool_id      = data.vsphere_compute_cluster.selected.resource_pool_id
  network_id            = data.vsphere_network.selected.id
  vm_folder             = var.vm_folder
  vm_name               = var.vm_name
  vm_template           = var.vm_template
  cpu                   = var.vm_cpu
  memory_mb             = var.vm_memory_mb
  disk_gb               = var.vm_disk_gb
  ssh_public_key        = var.ssh_public_key
  cloud_init_user_data  = file("${path.module}/cloud-init-user-data.yaml")
  seed_iso_path         = var.seed_iso_path
  seed_iso_datastore_id = data.vsphere_datastore.selected.id
}
