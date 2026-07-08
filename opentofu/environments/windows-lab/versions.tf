terraform {
  required_version = ">= 1.8.0"

  required_providers {
    vsphere = {
      source  = "hashicorp/vsphere"
      version = "~> 2.12"
    }
  }

  backend "local" {
    path = "/opt/appserver/data/iac/state/windows-lab/terraform.tfstate"
  }
}
