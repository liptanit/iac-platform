output "selected_vcenter" {
  value = var.selected_vcenter
}

output "selected_datacenter" {
  value = data.vsphere_datacenter.selected.name
}

output "selected_cluster" {
  value = data.vsphere_compute_cluster.selected.name
}

output "selected_datastore" {
  value = data.vsphere_datastore.selected.name
}

output "selected_network" {
  value = data.vsphere_network.selected.name
}

output "create_vm" {
  value = var.create_vm
}

output "planned_vm_names" {
  value = keys(local.effective_vms)
}
