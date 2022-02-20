from itertools import chain
from typing import Any, Dict, cast
from lxml import etree
from .wsmanclient import WSManClient

# ElementMaker is not typed yet, workaround from
#   https://github.com/python/mypy/issues/6948#issuecomment-654371424
from lxml.builder import ElementMaker as ElementMaker_untyped

ElementMaker = cast(Any, ElementMaker_untyped)


class BootController:
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

    def __init__(self, client: WSManClient):
        self.client = client

    def get_boot_capabilities(self) -> list[str]:
        xmlns = f"{WSManClient.AMT}/AMT_BootCapabilities"
        raw_xml = self.client.retrieve("get", xmlns)
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
        fault = tree.find(f".//{{{WSManClient.SOAPENV}}}Fault")
        if fault is not None:
            text = tree.find(
                f".//{{{WSManClient.SOAPENV}}}Reason//{{{WSManClient.SOAPENV}}}Text"
            )
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
        xmlns = f"{WSManClient.AMT}/AMT_BootSettingData"
        raw_xml = self.client.retrieve("get", f"{xmlns}?{selector}")
        return self._parse_bootparams(xmlns, raw_xml)

    def clear_bootparams(self) -> dict[str, str]:
        return self.set_bootparams({})

    def set_bootparams(self, params: dict[str, str]) -> dict[str, str]:
        # See step 3 of
        #   https://software.intel.com/sites/manageability/AMT_Implementation_and_Reference_Guide/default.htm?turl=WordDocuments%2Fsetsolstorageredirectionandotherbootoptions.htm
        selector = "InstanceID=Intel(r)%20AMT:BootSettingData%200"
        xmlns = f"{WSManClient.AMT}/AMT_BootSettingData"
        wsman_args = chain.from_iterable(
            [
                ["-k", f"{key}={val}"]
                for key, val in (self.BOOTSETTINGDATA | params).items()
            ]
        )
        raw_xml = self.client.retrieve(
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
        xmlns = f"{WSManClient.CIM}/CIM_BootConfigSetting"
        raw_xml = self.client.retrieve(
            "invoke", "-a", "ChangeBootOrder", "-d", "6", f"{xmlns}?{selector}"
        )
        return self._check_bootorder_result(xmlns, raw_xml)

    def set_bootorder_pxe(self) -> str:
        selector = "InstanceID=Intel(r)%20AMT:%20Boot%20Configuration%200"
        xmlns = f"{WSManClient.CIM}/CIM_BootConfigSetting"
        nsmap: Dict[str | None, str] = {
            "p": xmlns,
            "a": WSManClient.ADR,
            "x": WSManClient.XSD,
        }

        P = ElementMaker(namespace=xmlns, nsmap=nsmap)
        REQUEST = P.ChangeBootOrder_INPUT
        SOURCE = P.Source
        A = ElementMaker(namespace=WSManClient.ADR, nsmap=nsmap)
        ADDRESS = A.Address
        REFERENCEPARAMETERS = A.ReferenceParameters
        X = ElementMaker(namespace=WSManClient.XSD, nsmap=nsmap)
        RESOURCEURI = X.ResourceURI
        SELECTORSET = X.SelectorSet
        SELECTOR = X.Selector

        request: Any = REQUEST(
            SOURCE(
                ADDRESS(self.client.soap_address()),
                REFERENCEPARAMETERS(
                    RESOURCEURI(f"{WSManClient.CIM}/CIM_BootSourceSetting"),
                    SELECTORSET(
                        SELECTOR("Intel(r) AMT: Force PXE Boot", Name="InstanceID")
                    ),
                ),
            ),
        )
        input_xml = etree.tostring(request, pretty_print=True).decode("utf-8")
        raw_xml = self.client.send_input(
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
        xmlns = f"{WSManClient.CIM}/CIM_BootService"
        nsmap: Dict[str | None, str] = {
            "p": xmlns,
            "a": WSManClient.ADR,
            "x": WSManClient.XSD,
        }

        P = ElementMaker(namespace=xmlns, nsmap=nsmap)
        REQUEST = P.SetBootConfigRole_INPUT
        BOOTCONFIGSETTING = P.BootConfigSetting
        ROLE = P.Role
        A = ElementMaker(namespace=WSManClient.ADR, nsmap=nsmap)
        ADDRESS = A.Address
        REFERENCEPARAMETERS = A.ReferenceParameters
        X = ElementMaker(namespace=WSManClient.XSD, nsmap=nsmap)
        RESOURCEURI = X.ResourceURI
        SELECTORSET = X.SelectorSet
        SELECTOR = X.Selector

        request: Any = REQUEST(
            BOOTCONFIGSETTING(
                ADDRESS(self.client.soap_address()),
                REFERENCEPARAMETERS(
                    RESOURCEURI(f"{WSManClient.CIM}/CIM_BootConfigSetting"),
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
        raw_xml = self.client.send_input(
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
