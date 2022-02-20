from typing import Any, cast
from lxml import etree
from .wsmanclient import WSManClient

# ElementMaker is not typed yet, workaround from
#   https://github.com/python/mypy/issues/6948#issuecomment-654371424
from lxml.builder import ElementMaker as ElementMaker_untyped

ElementMaker = cast(Any, ElementMaker_untyped)


class KVMController:
    # RFB password can't accept the characters: '"' ',' ':'
    # The rest taken from
    #    https://en.wikipedia.org/wiki/List_of_Special_Characters_for_Passwords#Table_of_Special_Characters
    ACCEPTABLE_VNC_PASSWORD_SPECIAL = "!#$%&'()*+-./;<=>?@[\\]^_`{|}~"

    KVMSTATES = {
        # https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=HTMLDocuments%2FWS-Management_Class_Reference%2FCIM_KVMRedirectionSAP.htm
        "2" : "Enabled",
        "3" : "Disabled",
        "6" : "Enabled but Offline",
    }

    def __init__(self, client: WSManClient):
        self.client = client

    def get_kvm_state(self) -> dict[str, str]:
        kvm_state: dict[str, str] = {}

        xmlns = f"{WSManClient.CIM}/CIM_KVMRedirectionSAP"
        raw_xml = self.client.retrieve("get", xmlns)
        tree = etree.fromstring(bytes(raw_xml, encoding="utf-8"))
        enabled_state = tree.find(f".//{{{xmlns}}}EnabledState")
        if enabled_state is None or enabled_state.text is None:
            raise ValueError("Could not retrieve KVM enabled state")
        if enabled_state.text not in KVMController.KVMSTATES:
            raise ValueError(f"Invalid state {enabled_state.text} for KVM enabled state")
        kvm_state["EnabledState"] = KVMController.KVMSTATES[enabled_state.text]
       
        xmlns = f"{WSManClient.IPS}/IPS_KVMRedirectionSettingData"
        raw_xml = self.client.retrieve("get", xmlns)
        tree = etree.fromstring(bytes(raw_xml, encoding="utf-8"))
        enabled_mebx = tree.find(f".//{{{xmlns}}}EnabledByMEBx")
        if enabled_mebx is None or enabled_mebx.text is None:
            raise ValueError(
                "Could not determine whether KVM was enabled by Intel ME settings"
            )
        kvm_state["EnabledByMEBx"] = enabled_mebx.text
        port5900_enabled = tree.find(f".//{{{xmlns}}}Is5900PortEnabled")
        if port5900_enabled is None or port5900_enabled.text is None:
            raise ValueError("Could not determine whether port 5900 was enabled")
        kvm_state["Is5900PortEnabled"] = port5900_enabled.text
        optin_policy = tree.find(f".//{{{xmlns}}}OptInPolicy")
        if optin_policy is None or optin_policy.text is None:
            raise ValueError("Could not determine whether user opt-in is required")
        kvm_state["OptInPolicy"] = optin_policy.text
        session_timeout = tree.find(f".//{{{xmlns}}}SessionTimeout")
        if session_timeout is None or session_timeout.text is None:
            raise ValueError("Could not determine session time out")
        kvm_state["SessionTimeout"] = session_timeout.text
        return kvm_state

    def check_vnc_password(self, password: str):
        if len(password) != 8:
            raise ValueError("VNC password must be 8 characters exactly")

        lower = False
        upper = False
        digit = False
        special = False
        for ch in password:
            if ch.islower():
                lower = True
            elif ch.isupper():
                upper = True
            elif ch.isdigit():
                digit = True
            elif ch in KVMController.ACCEPTABLE_VNC_PASSWORD_SPECIAL:
                special = True
            else:
                raise ValueError(
                    f"Invalid character in VNC password, acceptable: {KVMController.ACCEPTABLE_VNC_PASSWORD_SPECIAL}"
                )
        if not lower or not upper or not digit or not special:
            raise ValueError(
                "VNC password must include at least 1 capital letter, 1 lowercase letter, 1 digit and 1 special character"
            )

    def enable_kvm_vnc(self, password: str):
        xmlns = f"{WSManClient.IPS}/IPS_KVMRedirectionSettingData"

        state = self.get_kvm_state()
        if state["EnabledByMEBx"] != "true":
            raise ValueError("Cannot enable KVM as it is disabled by Intel ME")

        # Always set the password as we cannot retrieve whether it is set or not
        self.check_vnc_password(password)
        raw_xml = self.client.retrieve("put", xmlns, "-k", f"RFBPassword={password}")
        print(raw_xml)

        # Enable VNC port 5900 if not yet enabled
        if state["Is5900PortEnabled"] != "true":
            raw_xml = self.client.retrieve("put", xmlns, "-k", "Is5900PortEnabled=true")
            print(raw_xml)
        
        # Disable opt-in policy if enabled
        if state["OptInPolicy"] == "true":
            raw_xml = self.client.retrieve("put", xmlns, "-k", "OptInPolicy=false")
            print(raw_xml)

        # Enable KVM if not yet enabled
        if state["EnabledState"] == "Disabled":
            raw_xml = self.client.retrieve("invoke", "-a", "RequestStateChange",
                f"{WSManClient.CIM}/CIM_KVMRedirectionSAP", "-k", "RequestedState=2")
            print(raw_xml)

    def disable_kvm_vnc(self):
        xmlns = f"{WSManClient.IPS}/IPS_KVMRedirectionSettingData"

        state = self.get_kvm_state()

        # Disable VNC port 5900 if enabled
        if state["Is5900PortEnabled"] == "true":
            raw_xml = self.client.retrieve("put", xmlns, "-k", "Is5900PortEnabled=false")
            print(raw_xml)
        
        # Disable KVM if enabled
        if state["EnabledState"] != "Disabled":
            raw_xml = self.client.retrieve("invoke", "-a", "RequestStateChange",
                f"{WSManClient.CIM}/CIM_KVMRedirectionSAP", "-k", "RequestedState=3")
            print(raw_xml)
