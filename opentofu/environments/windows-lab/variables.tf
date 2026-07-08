variable "vsphere_allow_unverified_ssl" {
  description = "Allow self-signed vCenter certificate. Credentials are read from VSPHERE_* environment variables."
  type        = bool
  default     = true
}

variable "datacenter" {
  type = string
}

variable "cluster" {
  type = string
}

variable "datastore" {
  type = string
}

variable "network" {
  type = string
}

variable "vm_folder" {
  type    = string
  default = "IaC-Lab"
}

variable "create_vm" {
  description = "Set true only for an approved controlled Windows clone. False keeps plans read-only."
  type        = bool
  default     = false
}

variable "source_vm" {
  description = "Source Windows VM or template inventory path."
  type        = string
}

variable "windows_vms" {
  description = "Map of Windows VMs to create when create_vm is true. Keys are VM names."
  type = map(object({
    cpu                     = number
    memory_mb               = number
    disks                   = list(object({ label = string, size_gb = number, unit_number = number, thin_provisioned = bool }))
    customize_windows       = optional(bool, false)
    computer_name           = optional(string, "")
    workgroup               = optional(string, "WORKGROUP")
    ipv4_address            = optional(string, "")
    ipv4_netmask            = optional(number, 24)
    ipv4_gateway            = optional(string, "")
    dns_server_list         = optional(list(string), [])
    dns_suffix_list         = optional(list(string), [])
    firmware                = optional(string, "")
    efi_secure_boot_enabled = optional(bool)
  }))
  default = {}
}
