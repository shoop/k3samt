import json
from os import environ

from controllers import WSManClient, PowerController, BootController, KVMController

if __name__ == "__main__":
    host = environ.get("AMT_HOST")
    if host is None:
        raise ValueError("Need AMT host in environ AMT_HOST")
    port = 623
    user = "admin"
    password = environ.get("AMT_PASSWORD")
    if password is None:
        raise ValueError("Need AMT password in environ AMT_PASSWORD")
    client = WSManClient(host, port, user, password)
    powerctl = PowerController(client)
    bootctl = BootController(client)
    kvmctl = KVMController(client)
    
    print("==== POWER CHANGE CAPABILITIES")
    print(json.dumps(powerctl.get_power_change_capabilities(), sort_keys=True, indent=4))

    print("\n==== CURRENT POWER STATE")
    print(powerctl.get_power_state())

    print("\n==== BOOT CAPABILITIES")
    print(json.dumps(bootctl.get_boot_capabilities(), sort_keys=True, indent=4))

    print("\n==== KVM STATE")
    print(kvmctl.get_kvm_state())