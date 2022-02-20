from os import environ

from controllers import WSManClient, KVMController

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
    kvmctl = KVMController(client)
    
    vnc_password = environ.get("AMT_VNC_PASSWORD")
    if vnc_password is None:
        raise ValueError("Need VNC password in environ AMT_VNC_PASSWORD")
    kvmctl.enable_kvm_vnc(vnc_password)
