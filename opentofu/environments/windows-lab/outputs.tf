output "windows_vms" {
  value = {
    for name, vm in module.windows_vm : name => {
      id                 = vm.id
      default_ip_address = vm.default_ip_address
    }
  }
}
