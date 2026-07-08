data "vsphere_virtual_machine" "template" {
  name          = var.vm_template
  datacenter_id = var.datacenter_id
}

resource "vsphere_virtual_machine" "this" {
  name             = var.vm_name
  folder           = var.vm_folder
  resource_pool_id = var.resource_pool_id
  datastore_id     = var.datastore_id

  num_cpus = var.cpu
  memory   = var.memory_mb
  guest_id = data.vsphere_virtual_machine.template.guest_id

  scsi_type = data.vsphere_virtual_machine.template.scsi_type

  network_interface {
    network_id   = var.network_id
    adapter_type = data.vsphere_virtual_machine.template.network_interface_types[0]
  }

  cdrom {
    client_device = true
  }

  disk {
    label            = "disk0"
    size             = var.disk_gb
    thin_provisioned = true
  }

  vapp {
    properties = {
      "instance-id" = var.vm_name
      "hostname"    = var.vm_name
      "public-keys" = var.ssh_public_key
      "user-data"   = var.cloud_init_user_data == "" ? "" : base64encode(var.cloud_init_user_data)
      "password"    = ""
      "seedfrom"    = ""
    }
  }

  clone {
    template_uuid = data.vsphere_virtual_machine.template.id
  }
}
