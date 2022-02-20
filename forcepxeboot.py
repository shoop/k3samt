from os import environ
import time

from controllers import WSManClient, PowerController, BootController

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
    
    # Follow the steps here in order, or AMT will not do the right thing:
    # https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=WordDocuments%2Fsetsolstorageredirectionandotherbootoptions.htm
    print("==== Clearing Boot Configuration")
    print(bootctl.clear_bootparams())
    print(bootctl.clear_bootorder())
    print("==== Set PXE Boot for next boot")
    print(bootctl.set_bootorder_pxe())
    print(bootctl.set_bootconfig("IsNextSingleUse"))
    print("==== Turn on machine")
    print(powerctl.set_power_state("On"))
    time.sleep(1)
    print(powerctl.get_power_state())
