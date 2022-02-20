import subprocess


class WSManClient:
    IPS = "http://intel.com/wbem/wscim/1/ips-schema/1"
    CIM = "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2"
    AMT = "http://intel.com/wbem/wscim/1/amt-schema/1"

    XSD = "http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd"
    ADR = "http://schemas.xmlsoap.org/ws/2004/08/addressing"
    SOAPENV = "http://www.w3.org/2003/05/soap-envelope"

    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def soap_address(self) -> str:
        return f"http://{self.host}:{self.port}/wsman"

    def retrieve(self, *args: str) -> str:
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

    def send_input(self, input: str, *args: str) -> str:
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
            self.retrieve("enumerate", "http://schemas.dmtf.org/wbem/wscim/1/*")
        )
