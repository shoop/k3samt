from itertools import chain
from os import environ
import subprocess

# import time
from typing import Dict, Any, cast

from lxml import etree

# ElementMaker is not typed yet, workaround from
#   https://github.com/python/mypy/issues/6948#issuecomment-654371424
from lxml.builder import ElementMaker as ElementMaker_untyped

ElementMaker = cast(Any, ElementMaker_untyped)


class WSManClient:
    IPS = "http://intel.com/wbem/wscim/1/ips-schema/1"
    CIM = "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2"
    AMT = "http://intel.com/wbem/wscim/1/amt-schema/1"

    XSD = "http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd"
    ADR = "http://schemas.xmlsoap.org/ws/2004/08/addressing"
    SOAPENV = "http://www.w3.org/2003/05/soap-envelope"

    BOOTCAPABILITIES = [
        # https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=HTMLDocuments%2FWS-Management_Class_Reference%2FAMT_BootCapabilities.htm
        "IDER",
        "SOL",
        "BIOSReflash",
        "BIOSSetup",
        "BIOSPause",
        "ForcePXEBoot",
        "ForceHardDriveBoot",
        "ForceHardDriveSafeModeBoot",
        "ForceDiagnosticBoot",
        "ForceCDorDVDBoot",
        "VerbosityScreenBlank",
        "PowerButtonLock",
        "ResetButtonLock",
        "KeyboardLock",
        "SleepButtonLock",
        "UserPasswordBypass",
        "ForcedProgressEvents",
        "VerbosityVerbose",
        "VerbosityQuiet",
        "ConfigurationDataReset",
        "BIOSSecureBoot",
        "SecureErase",
        "ForceWinREBoot",
        "ForceUEFILocalPBABoot",
        "ForceUEFIHTTPSBoot",
        "AMTSecureBootControl",
        "UEFIWiFiCoExistenceAndProfileShare",
    ]

    BOOTSETTINGDATA = {
        "BIOSPause": "false",
        "BIOSSetup": "false",
        "BootMediaIndex": "0",
        "ConfigurationDataReset": "false",
        "EnforceSecureBoot": "false",
        "FirmwareVerbosity": "0",
        "ForcedProgressEvents": "false",
        "IDERBootDevice": "0",
        "LockKeyboard": "false",
        "LockPowerButton": "false",
        "LockResetButton": "false",
        "LockSleepButton": "false",
        "ReflashBIOS": "false",
        "SecureErase": "false",
        "UseIDER": "false",
        "UseSOL": "false",
        "UseSafeMode": "false",
        "UserPasswordBypass": "false",
    }

    BOOTCHANGERESULTS = {
        # https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=HTMLDocuments%2FWS-Management_Class_Reference%2FCIM_BootConfigSetting.htm%23ChangeBootOrder
        "0": "Completed with No Error",
        "1": "Not Supported",
        "2": "Unknown/Unspecified Error",
        "3": "Busy",
        "4": "Invalid Reference",
        "5": "Invalid Parameter",
        "6": "Access Denied",
        # 7..32767 -> Method Reserved
        # 32768..65535 -> Vendor Specified
    }

    BOOTCONFIGROLE = {
        # https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=WordDocuments%2Fsetordisablebootconfigurationsettingsforthenextboot.htm
        "1": "IsNextSingleUse",
        "32768": "IsNotNext",
    }

    POWERSTATES = {
        # https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=WordDocuments%2Fchangesystempowerstate.htm
        "2": "On",
        "3": "Sleep - Light",
        "4": "Sleep - Deep",
        "5": "Power Cycle (Off Soft)",
        "6": "Power Off - Hard",
        "7": "Hibernate",
        "8": "Power Off - Soft",
        "9": "Power Cycle (Off Hard)",
        "10": "Master Bus Reset",
        "11": "Diagnostic Interrupt (NMI)",
        "12": "Power Off - Soft Graceful",
        "13": "Power Off - Hard Graceful",
        "14": "Master Bus Reset Graceful",
        "15": "Power Cycle (off - Soft Graceful)",
        "16": "Power Cycle (Off - Hard Graceful)",
        # For RequestedPowerStatesSupported
        "17": "Diagnostic Interrupt (INIT)",
    }

    POWERCHANGECAPABILITIES = {
        # https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/HTMLDocuments/WS-Management_Class_Reference/CIM_PowerManagementCapabilities.htm#PowerChangeCapabilities
        "0": "Unknown",
        "1": "Other",
        "2": "Power Saving Modes Entered Automatically",
        "3": "Power State Settable",
        "4": "Power Cycling Supported",
        "5": "Timed Power On Supported",
        "6": "Off Hard Power Cycling Supported",
        "7": "HW Reset Supported",
        "8": "Graceful Shutdown Supported",
    }

    POWERCHANGERESULTS = {
        # https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/HTMLDocuments/WS-Management_Class_Reference/CIM_PowerManagementService.htm#RequestPowerStateChange
        "0": "Completed with No Error",
        "1": "Not Supported",
        "2": "Unknown or Unspecified Error",
        "3": "Cannot complete within Timeout Period",
        "4": "Failed",
        "5": "Invalid Parameter",
        "6": "In Use",
        "4096": "DTMF Reserved",
        "4097": "Method Parameters Checked - Job Started",
        "4098": "Invalid State Transition",
        "4099": "Use of Timeout Parameter Not Supported",
        "4100": "Busy",
        # 4101..32767 -> Method Reserved
        # 32768..65535 -> Vendor Specific
    }

    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def wsman_retrieval(self, *args: str) -> str:
        result = subprocess.run(
            [
                "wsman",
                "-h",
                self.host,
                "-P",
                str(self.port),
                "-u",
                self.user,
                "-p",
                self.password,
                *args,
            ],
            capture_output=True,
            text=True,
        )
        return result.stdout

    def wsman_input(self, input: str, *args: str) -> str:
        result = subprocess.run(
            [
                "wsman",
                "-h",
                self.host,
                "-P",
                str(self.port),
                "-u",
                self.user,
                "-p",
                self.password,
                "-J",
                "-",
                *args,
            ],
            input=input,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def list_all(self):
        print(
            self.wsman_retrieval("enumerate", "http://schemas.dmtf.org/wbem/wscim/1/*")
        )

    def get_boot_capabilities(self) -> list[str]:
        xmlns = f"{self.AMT}/AMT_BootCapabilities"
        raw_xml = self.wsman_retrieval("get", xmlns)
        tree = etree.fromstring(bytes(raw_xml, encoding="utf-8"))
        capabilities: list[str] = []
        for cap in self.BOOTCAPABILITIES:
            cap_element = tree.find(f".//{{{xmlns}}}{cap}")
            if cap_element is None:
                continue
            if cap_element.text is None:
                raise ValueError(f"Invalid capability value {cap}")
            if cap_element.text == "true":
                capabilities.append(cap)
            elif cap_element.text != "false":
                capabilities.append(cap)
        return capabilities

    def _parse_bootparams(self, xmlns: str, raw_xml: str) -> dict[str, str]:
        tree = etree.fromstring(bytes(raw_xml, encoding="utf-8"))
        fault = tree.find(f".//{{{self.SOAPENV}}}Fault")
        if fault is not None:
            text = tree.find(f".//{{{self.SOAPENV}}}Reason//{{{self.SOAPENV}}}Text")
            if text is None or text.text is None:
                raise ValueError("Unknown error")
            raise ValueError(text.text)

        params: dict[str, str] = {}
        for par in self.BOOTSETTINGDATA.keys():
            par_element = tree.find(f".//{{{xmlns}}}{par}")
            if par_element is None:
                continue
            if par_element.text is None:
                raise ValueError(f"Invalid boot setting data for {par}")
            params[par] = par_element.text
        instance_id_element = tree.find(f".//{{{xmlns}}}InstanceID")
        if instance_id_element is None or instance_id_element.text is None:
            raise ValueError("Missing InstanceID")
        params["InstanceID"] = instance_id_element.text
        elementname_element = tree.find(f".//{{{xmlns}}}ElementName")
        if elementname_element is None or elementname_element.text is None:
            raise ValueError("Missing ElementName")
        params["ElementName"] = elementname_element.text
        return params

    def get_bootparams(self) -> dict[str, str]:
        selector = "InstanceID=Intel(r)%20AMT:BootSettingData%200"
        xmlns = f"{self.AMT}/AMT_BootSettingData"
        raw_xml = self.wsman_retrieval("get", f"{xmlns}?{selector}")
        return self._parse_bootparams(xmlns, raw_xml)

    def clear_bootparams(self) -> dict[str, str]:
        return self.set_bootparams({})

    def set_bootparams(self, params: dict[str, str]) -> dict[str, str]:
        # See step 3 of
        #   https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=WordDocuments%2Fsetsolstorageredirectionandotherbootoptions.htm
        selector = "InstanceID=Intel(r)%20AMT:BootSettingData%200"
        xmlns = f"{self.AMT}/AMT_BootSettingData"
        wsman_args = chain.from_iterable([["-k", f"{key}={val}"] for key, val in (self.BOOTSETTINGDATA | params).items()])
        raw_xml = self.wsman_retrieval(
            "put",
            f"{xmlns}?{selector}",
            *wsman_args,
        )
        return self._parse_bootparams(xmlns, raw_xml)

    def _check_bootorder_result(self, xmlns: str, raw_xml: str) -> str:
        tree = etree.fromstring(bytes(raw_xml, encoding="utf-8"))
        returnvalue = tree.find(f".//{{{xmlns}}}ReturnValue")
        if (
            returnvalue is None
            or returnvalue.text is None
            or self.BOOTCHANGERESULTS.get(returnvalue.text) is None
        ):
            raise ValueError("Could not determine boot change result")
        return self.BOOTCHANGERESULTS[returnvalue.text]

    def clear_bootorder(self) -> str:
        selector = "InstanceID=Intel(r)%20AMT:%20Boot%20Configuration%200"
        xmlns = f"{self.CIM}/CIM_BootConfigSetting"
        raw_xml = self.wsman_retrieval(
            "invoke", "-a", "ChangeBootOrder", "-d", "6", f"{xmlns}?{selector}"
        )
        return self._check_bootorder_result(xmlns, raw_xml)

    def set_bootorder_pxe(self) -> str:
        selector = "InstanceID=Intel(r)%20AMT:%20Boot%20Configuration%200"
        xmlns = f"{self.CIM}/CIM_BootConfigSetting"
        nsmap: Dict[str | None, str] = {"p": xmlns, "a": self.ADR, "x": self.XSD}

        P = ElementMaker(namespace=xmlns, nsmap=nsmap)
        REQUEST = P.ChangeBootOrder_INPUT
        SOURCE = P.Source
        A = ElementMaker(namespace=self.ADR, nsmap=nsmap)
        ADDRESS = A.Address
        REFERENCEPARAMETERS = A.ReferenceParameters
        X = ElementMaker(namespace=self.XSD, nsmap=nsmap)
        RESOURCEURI = X.ResourceURI
        SELECTORSET = X.SelectorSet
        SELECTOR = X.Selector

        request: Any = REQUEST(
            SOURCE(
                ADDRESS(f"http://{self.host}:{self.port}/wsman"),
                REFERENCEPARAMETERS(
                    RESOURCEURI(f"{self.CIM}/CIM_BootSourceSetting"),
                    SELECTORSET(
                        SELECTOR("Intel(r) AMT: Force PXE Boot", Name="InstanceID")
                    ),
                ),
            ),
        )
        input_xml = etree.tostring(request, pretty_print=True).decode("utf-8")
        raw_xml = self.wsman_input(
            input_xml,
            "invoke",
            "-a",
            "ChangeBootOrder",
            f"{xmlns}?{selector}",
        )
        return self._check_bootorder_result(xmlns, raw_xml)

    def _bootconfig_to_internal_bootconfig(self, bootconfig: str) -> str:
        internal_bootconfig: str | None = None
        if bootconfig not in self.BOOTCONFIGROLE.keys():
            for key, val in self.BOOTCONFIGROLE.items():
                if val == bootconfig:
                    internal_bootconfig = key
                    break
        else:
            internal_bootconfig = bootconfig
        if internal_bootconfig is None:
            raise ValueError(f"Invalid boot config role {bootconfig} specified")
        return internal_bootconfig

    def set_bootconfig(self, cfg: str):
        internal_cfg = self._bootconfig_to_internal_bootconfig(cfg)
        selector = "Name=Intel(r)%20AMT%20Boot%20Service"
        xmlns = f"{self.CIM}/CIM_BootService"
        nsmap: Dict[str | None, str] = {"p": xmlns, "a": self.ADR, "x": self.XSD}

        P = ElementMaker(namespace=xmlns, nsmap=nsmap)
        REQUEST = P.SetBootConfigRole_INPUT
        BOOTCONFIGSETTING = P.BootConfigSetting
        ROLE = P.Role
        A = ElementMaker(namespace=self.ADR, nsmap=nsmap)
        ADDRESS = A.Address
        REFERENCEPARAMETERS = A.ReferenceParameters
        X = ElementMaker(namespace=self.XSD, nsmap=nsmap)
        RESOURCEURI = X.ResourceURI
        SELECTORSET = X.SelectorSet
        SELECTOR = X.Selector

        request: Any = REQUEST(
            BOOTCONFIGSETTING(
                ADDRESS(f"http://{self.host}:{self.port}/wsman"),
                REFERENCEPARAMETERS(
                    RESOURCEURI(f"{self.CIM}/CIM_BootConfigSetting"),
                    SELECTORSET(
                        SELECTOR(
                            "Intel(r) AMT: Boot Configuration 0", Name="InstanceID"
                        )
                    ),
                ),
            ),
            ROLE(internal_cfg),
        )
        input_xml = etree.tostring(request, pretty_print=True).decode("utf-8")
        raw_xml = self.wsman_input(
            input_xml,
            "invoke",
            "-a",
            "SetBootConfigRole",
            f"{xmlns}?{selector}",
        )
        tree = etree.fromstring(bytes(raw_xml, encoding="utf-8"))
        returnvalue = tree.find(f".//{{{xmlns}}}ReturnValue")
        if (
            returnvalue is None
            or returnvalue.text is None
            or self.BOOTCHANGERESULTS.get(returnvalue.text) is None
        ):
            raise ValueError("Could not determine boot change result")
        return self.BOOTCHANGERESULTS[returnvalue.text]

    def get_power_change_capabilities(self) -> dict[str, list[str]]:
        xmlns = f"{self.CIM}/CIM_PowerManagementCapabilities"
        raw_xml = self.wsman_retrieval("get", xmlns, "-k", "PowerChangeCapabilities")
        tree = etree.fromstring(bytes(raw_xml, encoding="utf-8"))

        capabilities: dict[str, list[str]] = {}

        capabilities["PowerChangeCapabilities"] = []
        for cap in tree.findall(f".//{{{xmlns}}}PowerChangeCapabilities"):
            if cap.text is None or self.POWERCHANGECAPABILITIES.get(cap.text) is None:
                raise KeyError("Empty capability returned")
            capabilities["PowerChangeCapabilities"].append(
                self.POWERCHANGECAPABILITIES[cap.text]
            )

        capabilities["PowerStatesSupported"] = []
        for state in tree.findall(f".//{{{xmlns}}}PowerStatesSupported"):
            if state.text is None or self.POWERSTATES.get(state.text) is None:
                raise KeyError("Empty power state returned")
            capabilities["PowerStatesSupported"].append(self.POWERSTATES[state.text])

        capabilities["RequestedPowerStatesSupported"] = []
        for state in tree.findall(f".//{{{xmlns}}}RequestedPowerStatesSupported"):
            if state.text is None or self.POWERSTATES.get(state.text) is None:
                raise KeyError("Empty power state returned")
            capabilities["RequestedPowerStatesSupported"].append(
                self.POWERSTATES[state.text]
            )

        return capabilities

    def _powerstate_to_internal_state(self, state: str) -> str:
        internal_state: str | None = None
        if state not in self.POWERSTATES.keys():
            for key, val in self.POWERSTATES.items():
                if val == state:
                    internal_state = key
                    break
        else:
            internal_state = state
        if internal_state is None:
            raise ValueError(f"Invalid state {state} specified")
        return internal_state

    def get_power_state(self) -> dict[str, str | list[str]]:
        xmlns = f"{self.CIM}/CIM_AssociatedPowerManagementService"
        raw_xml = self.wsman_retrieval("get", xmlns)
        tree = etree.fromstring(bytes(raw_xml, encoding="utf-8"))

        powerstate: dict[str, str | list[str]] = {}

        cur_powerstate = tree.find(f".//{{{xmlns}}}PowerState")
        if (
            cur_powerstate is None
            or cur_powerstate.text is None
            or self.POWERSTATES.get(cur_powerstate.text) is None
        ):
            raise ValueError("Could not determine power state")
        powerstate["PowerState"] = self.POWERSTATES[cur_powerstate.text]

        powerstate["AvailablePowerStates"] = []
        for avail_state in tree.findall(f".//{{{xmlns}}}AvailableRequestedPowerStates"):
            if (
                avail_state.text is None
                or self.POWERSTATES.get(avail_state.text) is None
            ):
                raise ValueError("Could not determine available power state")
            powerstate["AvailablePowerStates"].append(
                self.POWERSTATES[avail_state.text]
            )

        return powerstate

    def set_power_state(self, state: str) -> str:
        internal_state = self._powerstate_to_internal_state(state)
        selector = "Name=Intel(r)%20AMT%20Power%20Management%20Service"
        xmlns = f"{self.CIM}/CIM_PowerManagementService"
        nsmap: Dict[str | None, str] = {"p": xmlns, "a": self.ADR, "x": self.XSD}

        P = ElementMaker(namespace=xmlns, nsmap=nsmap)
        REQUEST = P.RequestPowerStateChange_INPUT
        POWERSTATE = P.PowerState
        MANAGEDELEMENT = P.ManagedElement
        A = ElementMaker(namespace=self.ADR, nsmap=nsmap)
        ADDRESS = A.Address
        REFERENCEPARAMETERS = A.ReferenceParameters
        X = ElementMaker(namespace=self.XSD, nsmap=nsmap)
        RESOURCEURI = X.ResourceURI
        SELECTORSET = X.SelectorSet
        SELECTOR = X.Selector

        request: Any = REQUEST(
            POWERSTATE(internal_state),
            MANAGEDELEMENT(
                ADDRESS(f"http://{self.host}:{self.port}/wsman"),
                REFERENCEPARAMETERS(
                    RESOURCEURI(f"{self.CIM}/CIM_ComputerSystem"),
                    SELECTORSET(SELECTOR("ManagedSystem", Name="Name")),
                ),
            ),
        )
        input_xml = etree.tostring(request, pretty_print=True).decode("utf-8")
        raw_xml = self.wsman_input(
            input_xml,
            "invoke",
            "-a",
            "RequestPowerStateChange",
            f"{xmlns}?{selector}",
        )
        tree = etree.fromstring(bytes(raw_xml, encoding="utf-8"))
        returnvalue = tree.find(f".//{{{xmlns}}}ReturnValue")
        if (
            returnvalue is None
            or returnvalue.text is None
            or self.POWERCHANGERESULTS.get(returnvalue.text) is None
        ):
            raise ValueError("Could not determine power state")
        return self.POWERCHANGERESULTS[returnvalue.text]


if __name__ == "__main__":
    host = "node1amt.svc.kzp.home.arpa"
    port = 623
    user = "admin"
    password = environ.get("AMT_PASSWORD")
    if password is None:
        raise ValueError("Need AMT password in environ AMT_PASSWORD")
    client = WSManClient(host, port, user, password)

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
