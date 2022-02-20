from typing import Any, Dict, cast
from lxml import etree
from .wsmanclient import WSManClient

# ElementMaker is not typed yet, workaround from
#   https://github.com/python/mypy/issues/6948#issuecomment-654371424
from lxml.builder import ElementMaker as ElementMaker_untyped

ElementMaker = cast(Any, ElementMaker_untyped)


class PowerController:
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

    def __init__(self, client: WSManClient):
        self.client = client

    def get_power_change_capabilities(self) -> dict[str, list[str]]:
        xmlns = f"{WSManClient.CIM}/CIM_PowerManagementCapabilities"
        raw_xml = self.client.retrieve(
            "get", xmlns, "-k", "PowerChangeCapabilities"
        )
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
        xmlns = f"{WSManClient.CIM}/CIM_AssociatedPowerManagementService"
        raw_xml = self.client.retrieve("get", xmlns)
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
        xmlns = f"{WSManClient.CIM}/CIM_PowerManagementService"
        nsmap: Dict[str | None, str] = {
            "p": xmlns,
            "a": WSManClient.ADR,
            "x": WSManClient.XSD,
        }

        P = ElementMaker(namespace=xmlns, nsmap=nsmap)
        REQUEST = P.RequestPowerStateChange_INPUT
        POWERSTATE = P.PowerState
        MANAGEDELEMENT = P.ManagedElement
        A = ElementMaker(namespace=WSManClient.ADR, nsmap=nsmap)
        ADDRESS = A.Address
        REFERENCEPARAMETERS = A.ReferenceParameters
        X = ElementMaker(namespace=WSManClient.XSD, nsmap=nsmap)
        RESOURCEURI = X.ResourceURI
        SELECTORSET = X.SelectorSet
        SELECTOR = X.Selector

        request: Any = REQUEST(
            POWERSTATE(internal_state),
            MANAGEDELEMENT(
                ADDRESS(self.client.soap_address()),
                REFERENCEPARAMETERS(
                    RESOURCEURI(f"{WSManClient.CIM}/CIM_ComputerSystem"),
                    SELECTORSET(SELECTOR("ManagedSystem", Name="Name")),
                ),
            ),
        )
        input_xml = etree.tostring(request, pretty_print=True).decode("utf-8")
        raw_xml = self.client.send_input(
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
