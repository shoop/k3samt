from os import environ

# import time

from controllers import WSManClient, PowerController, BootController

if __name__ == "__main__":
    host = "node1amt.svc.kzp.home.arpa"
    port = 623
    user = "admin"
    password = environ.get("AMT_PASSWORD")
    if password is None:
        raise ValueError("Need AMT password in environ AMT_PASSWORD")
    client = WSManClient(host, port, user, password)
    powerctl = PowerController(client)
    bootctl = BootController(client)
    
    print(powerctl.get_power_change_capabilities())

    # print(client.get_power_change_capabilities())
    # print(client.get_power_state())
    # print(client.set_power_state("Power Off - Soft"))
    # time.sleep(5)
    # print(client.get_power_state())
    # print(client.set_power_state("Power Off - Soft Graceful"))
    # time.sleep(5)
    # print(client.get_power_state())

    # Follow the steps here in order, or AMT will not do the right thing:
    # https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=WordDocuments%2Fsetsolstorageredirectionandotherbootoptions.htm
    # print(client.get_boot_capabilities())
    # print(client.clear_bootparams())
    # print(client.clear_bootorder())
    # print(client.set_bootorder_pxe())
    # print(client.set_bootconfig("IsNextSingleUse"))
    # print(client.set_power_state("On"))
    # time.sleep(5)
    # print(client.get_power_state())
    # print(client.set_power_state("Power Off - Soft"))
