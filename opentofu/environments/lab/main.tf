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

locals {
  raw_vms = length(var.vms) > 0 ? var.vms : (
    var.vm_name == "" ? {} : {
      (var.vm_name) = {
        template      = var.vm_template
        cpu           = var.vm_cpu
        memory_mb     = var.vm_memory_mb
        disk_gb       = var.vm_disk_gb
        datacenter    = var.datacenter
        cluster       = var.cluster
        datastore     = var.datastore
        network       = var.network
        seed_iso_path = var.seed_iso_path
      }
    }
  )

  effective_vms = {
    for name, vm in local.raw_vms : name => merge(vm, {
      datacenter = coalesce(vm.datacenter, "") == "" ? var.datacenter : vm.datacenter
      cluster    = coalesce(vm.cluster, "") == "" ? var.cluster : vm.cluster
      datastore  = coalesce(vm.datastore, "") == "" ? var.datastore : vm.datastore
      network    = coalesce(vm.network, "") == "" ? var.network : vm.network
    })
  }
}

data "vsphere_datacenter" "vm" {
  for_each = local.effective_vms
  name     = each.value.datacenter
}

data "vsphere_compute_cluster" "vm" {
  for_each      = local.effective_vms
  name          = each.value.cluster
  datacenter_id = data.vsphere_datacenter.vm[each.key].id
}

data "vsphere_datastore" "vm" {
  for_each      = local.effective_vms
  name          = each.value.datastore
  datacenter_id = data.vsphere_datacenter.vm[each.key].id
}

data "vsphere_network" "vm" {
  for_each      = local.effective_vms
  name          = each.value.network
  datacenter_id = data.vsphere_datacenter.vm[each.key].id
}

module "linux_vm" {
  for_each = var.create_vm ? local.effective_vms : {}
  source   = "../../modules/vsphere-linux-vm"

  datacenter_id         = data.vsphere_datacenter.vm[each.key].id
  datastore_id          = data.vsphere_datastore.vm[each.key].id
  resource_pool_id      = data.vsphere_compute_cluster.vm[each.key].resource_pool_id
  network_id            = data.vsphere_network.vm[each.key].id
  vm_folder             = var.vm_folder
  vm_name               = each.key
  vm_template           = each.value.template
  cpu                   = each.value.cpu
  memory_mb             = each.value.memory_mb
  disk_gb               = each.value.disk_gb
  ssh_public_key        = var.ssh_public_key
  cloud_init_user_data  = file("${path.module}/cloud-init-user-data.yaml")
  seed_iso_path         = each.value.seed_iso_path
  seed_iso_datastore_id = data.vsphere_datastore.vm[each.key].id
}
