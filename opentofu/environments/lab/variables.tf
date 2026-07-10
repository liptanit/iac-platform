variable "vsphere_allow_unverified_ssl" {
  description = "Allow self-signed vCenter certificate. Credentials are read from VSPHERE_* environment variables."
  type        = bool
  default     = true
}

variable "datacenter" {
  description = "vSphere datacenter name."
  type        = string
}

variable "cluster" {
  description = "vSphere cluster name."
  type        = string
}

variable "datastore" {
  description = "vSphere datastore name for lab VM placement."
  type        = string
}

variable "network" {
  description = "vSphere network or port group name for lab VM placement."
  type        = string
}

variable "selected_vcenter" {
  description = "Runtime vCenter endpoint selected by IaC Control."
  type        = string
  default     = ""
}

variable "vm_folder" {
  description = "Destination VM folder. Must exist before provisioning."
  type        = string
  default     = "IaC-Lab"
}

variable "create_vm" {
  description = "Set true only after template/network/datastore are confirmed. False keeps plans read-only."
  type        = bool
  default     = false
}

variable "vm_name" {
  description = "Lab VM name."
  type        = string
  default     = "iac-lab-linux-001"
}

variable "vm_template" {
  description = "Source VM template name. Required only when create_vm is true."
  type        = string
  default     = ""
}

variable "vm_cpu" {
  type    = number
  default = 2
}

variable "vm_memory_mb" {
  type    = number
  default = 4096
}

variable "vm_disk_gb" {
  type    = number
  default = 40
}

variable "ssh_public_key" {
  description = "SSH public key for Ubuntu cloud-init."
  type        = string
  default     = ""
}

variable "seed_iso_path" {
  description = "Datastore-relative path to a pre-uploaded NoCloud seed ISO."
  type        = string
  default     = ""
}

variable "vms" {
  description = "Map of Linux VMs to create when create_vm is true. Keys are VM names."
  type = map(object({
    template      = string
    cpu           = number
    memory_mb     = number
    disk_gb       = number
    datacenter    = optional(string, "")
    cluster       = optional(string, "")
    datastore     = optional(string, "")
    network       = optional(string, "")
    seed_iso_path = string
  }))
  default = {}
}
