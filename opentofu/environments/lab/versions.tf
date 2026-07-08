terraform {
  required_version = ">= 1.8.0"

  required_providers {
    vsphere = {
      source  = "vmware/vsphere"
      version = "~> 2.16"
    }
  }

  backend "local" {
    path = "/opt/appserver/data/iac/state/lab/terraform.tfstate"
  }
}
