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

module "windows_vm" {
  for_each = var.create_vm ? var.windows_vms : {}
  source   = "../../modules/vsphere-windows-vm"

  datacenter_id           = data.vsphere_datacenter.selected.id
  datastore_id            = data.vsphere_datastore.selected.id
  resource_pool_id        = data.vsphere_compute_cluster.selected.resource_pool_id
  network_id              = data.vsphere_network.selected.id
  vm_folder               = var.vm_folder
  vm_name                 = each.key
  source_vm               = var.source_vm
  cpu                     = each.value.cpu
  memory_mb               = each.value.memory_mb
  guest_id                = each.value.guest_id
  disks                   = each.value.disks
  customize_windows       = each.value.customize_windows
  computer_name           = each.value.computer_name
  workgroup               = each.value.workgroup
  admin_password          = var.windows_admin_password
  ipv4_address            = each.value.ipv4_address
  ipv4_netmask            = each.value.ipv4_netmask
  ipv4_gateway            = each.value.ipv4_gateway
  dns_server_list         = each.value.dns_server_list
  dns_suffix_list         = each.value.dns_suffix_list
  firmware                = each.value.firmware
  efi_secure_boot_enabled = each.value.efi_secure_boot_enabled
}
