variable "datacenter_id" { type = string }
variable "datastore_id" { type = string }
variable "resource_pool_id" { type = string }
variable "network_id" { type = string }
variable "vm_folder" { type = string }
variable "vm_name" { type = string }
variable "source_vm" { type = string }
variable "cpu" { type = number }
variable "memory_mb" { type = number }

variable "firmware" {
  description = "Optional firmware override. Empty preserves provider default from source clone."
  type        = string
  default     = ""
}

variable "efi_secure_boot_enabled" {
  description = "Optional EFI secure boot setting. Leave null to omit from VM configuration."
  type        = bool
  default     = null
}

variable "annotation" {
  type    = string
  default = "Managed by OpenTofu IaC."
}

variable "disks" {
  description = "Windows disks to keep/create during clone. Sizes must be >= source disk sizes."
  type = list(object({
    label            = string
    size_gb          = number
    unit_number      = number
    thin_provisioned = bool
  }))
}

variable "customize_windows" {
  description = "Enable VMware Guest OS Customization for Windows. Requires VMware Tools and a customization-safe source."
  type        = bool
  default     = false
}

variable "computer_name" {
  description = "Windows computer name for guest customization. Defaults to vm_name if empty."
  type        = string
  default     = ""
}

variable "workgroup" {
  type    = string
  default = "WORKGROUP"
}

variable "ipv4_address" {
  type    = string
  default = ""
}

variable "ipv4_netmask" {
  description = "IPv4 netmask length, for example 24."
  type        = number
  default     = 24
}

variable "ipv4_gateway" {
  type    = string
  default = ""
}

variable "dns_server_list" {
  type    = list(string)
  default = []
}

variable "dns_suffix_list" {
  type    = list(string)
  default = []
}

variable "wait_for_guest_ip_timeout" {
  type    = number
  default = 0
}

variable "wait_for_guest_net_timeout" {
  type    = number
  default = 0
}
