from os import environ
import sys

from controllers import WSManClient, PowerController

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
    
    current_state = powerctl.get_power_state()
    if "Master Bus Reset" not in current_state['AvailablePowerStates']:
        print(f"=== FAIL: the 'Master Bus Reset' state is not available currently, available: {','.join(current_state['AvailablePowerStates'])}")
        sys.exit(1)

    print(powerctl.set_power_state("Master Bus Reset"))
