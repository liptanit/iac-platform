data "vsphere_virtual_machine" "source" {
  name          = var.source_vm
  datacenter_id = var.datacenter_id
}

locals {
  effective_computer_name = var.computer_name == "" ? var.vm_name : var.computer_name
}

resource "vsphere_virtual_machine" "this" {
  name             = var.vm_name
  folder           = var.vm_folder
  resource_pool_id = var.resource_pool_id
  datastore_id     = var.datastore_id
  annotation       = var.annotation

  num_cpus = var.cpu
  memory   = var.memory_mb
  guest_id = var.guest_id == "" ? data.vsphere_virtual_machine.source.guest_id : var.guest_id

  wait_for_guest_ip_timeout  = var.wait_for_guest_ip_timeout
  wait_for_guest_net_timeout = var.wait_for_guest_net_timeout

  scsi_type = data.vsphere_virtual_machine.source.scsi_type
  firmware  = var.firmware == "" ? null : var.firmware

  efi_secure_boot_enabled = var.efi_secure_boot_enabled

  network_interface {
    network_id   = var.network_id
    adapter_type = data.vsphere_virtual_machine.source.network_interface_types[0]
  }

  dynamic "cdrom" {
    for_each = var.cdrom_iso_path == "" ? [1] : []

    content {
      client_device = true
    }
  }

  dynamic "cdrom" {
    for_each = var.cdrom_iso_path != "" ? [1] : []

    content {
      datastore_id = var.cdrom_iso_datastore_id
      path         = var.cdrom_iso_path
    }
  }

  dynamic "disk" {
    for_each = var.disks

    content {
      label            = disk.value.label
      size             = disk.value.size_gb
      unit_number      = disk.value.unit_number
      thin_provisioned = disk.value.thin_provisioned
    }
  }

  clone {
    template_uuid = data.vsphere_virtual_machine.source.id

    dynamic "customize" {
      for_each = var.customize_windows ? [1] : []

      content {
        windows_options {
          computer_name  = local.effective_computer_name
          workgroup      = var.workgroup
          admin_password = var.admin_password == "" ? null : var.admin_password
        }

        network_interface {
          ipv4_address = var.ipv4_address == "" ? null : var.ipv4_address
          ipv4_netmask = var.ipv4_address == "" ? null : var.ipv4_netmask
        }

        ipv4_gateway    = var.ipv4_gateway == "" ? null : var.ipv4_gateway
        dns_server_list = var.dns_server_list
        dns_suffix_list = var.dns_suffix_list
      }
    }
  }

  lifecycle {
    # VMware guest customization is a first-boot operation. Later inventory
    # corrections should be applied in-guest, not by replacing the VM.
    ignore_changes = [
      clone[0].customize[0],
    ]
  }
}
