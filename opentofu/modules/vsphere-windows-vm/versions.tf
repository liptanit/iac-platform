terraform {
  required_version = ">= 1.8.0"

  required_providers {
    vsphere = {
      source  = "hashicorp/vsphere"
      version = "~> 2.12"
    }
  }
}
