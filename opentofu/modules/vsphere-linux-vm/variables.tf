variable "datacenter_id" { type = string }
variable "datastore_id" { type = string }
variable "resource_pool_id" { type = string }
variable "network_id" { type = string }
variable "vm_folder" { type = string }
variable "vm_name" { type = string }
variable "vm_template" { type = string }
variable "cpu" { type = number }
variable "memory_mb" { type = number }
variable "disk_gb" { type = number }

variable "ssh_public_key" {
  description = "SSH public key injected through Ubuntu OVF/cloud-init properties."
  type        = string
  default     = ""
}

variable "cloud_init_user_data" {
  description = "Cloud-init user-data injected through Ubuntu OVF properties. Must be plain YAML; module base64-encodes it."
  type        = string
  default     = ""
}

variable "seed_iso_path" {
  description = "Datastore-relative path to a NoCloud seed ISO. Empty uses the template OVF/vApp cloud-init path."
  type        = string
  default     = ""
}

variable "seed_iso_datastore_id" {
  description = "Datastore ID containing the NoCloud seed ISO."
  type        = string
  default     = ""
}
