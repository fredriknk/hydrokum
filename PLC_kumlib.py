import logging
import snap7
import time
import threading
from typing import List, Dict

logging.basicConfig(level=logging.WARNING)

class MockPLC:
    def __init__(self):
        self.connected = False
        self.status = 0

    def connect(self, *args, **kwargs):
        print("MockPLC: Attempting to connect.")
        self.connected = True
        print("MockPLC: Successfully connected.")
        return True

    def disconnect(self):
        print("MockPLC: Disconnecting.")
        self.connected = False

    def write(self, address, command):
        print(f"MockPLC: Writing command {command} to address {address}")
        if address == "V0":
            self.status = command

    def read(self, address):
        print(f"MockPLC: Reading status from address {address}")
        return self.status

    def get_connected(self):
        return self.connected
class ConfigPLC:
    def __init__(self, ip_address: str, commands: Dict[str, int], status_bits = None, status_reg: str = "V1", update_status: bool = True):
        """Initialize the ConfigPLC class."""
        self.logger = logging.getLogger(__name__)
        self.plc = snap7.logo.Logo()
        self.ip_address = ip_address
        self.connected = False
        self.commands = commands
        self.status_bits = status_bits

        self.status_data = {
            'address': status_reg,
            'byte_array': bytearray(1),
            'status': 0
        }

        self.status_thread = threading.Thread(target=self._update_status, daemon=True) if update_status else None

    def connect(self, timeout: int = 5):
        """Connect to the PLC."""
        try:
            self.plc.connect(self.ip_address, 0x0300, 0x0200)
            self.connected = self.plc.get_connected()
        except snap7.Snap7Exception as e:  # Replace with the actual exception types
            self.logger.error(f"Connection failed: {e}")

        if self.connected:
            self.logger.info("Connected")
            if self.status_thread:
                self.status_thread.start()

    def disconnect(self):
        """Disconnect from the PLC."""
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join()
        self.plc.disconnect()
        self.logger.info("Disconnected")

    def write_command(self, address: str, command: int, delay: float = 0.1):
        """Write command to the PLC."""
        if self.connected:
            self.plc.write(address, command)
            self.logger.info(f"Wrote command 0b{command:08b} to {address}")
            if command in [self.commands.get(key) for key in ['open', 'close', 'estop']]:
                time.sleep(delay)
                self.plc.write(address, self.commands.get('none', 0))
                self.logger.info(f"Wrote command 0b{self.commands.get('none', 0):08b} to {address}")

    def _update_status(self):
        """Update status of the PLC."""
        while self.connected:
            try:
                self.status_data['status'] = self.plc.read(self.status_data['address'])
                time.sleep(1.0)
            except snap7.Snap7Exception as e:  # Replace with the actual exception types
                self.logger.error(f"Error updating status: {e}")
                self.connected = False

    def get_status(self) -> int:
        """Get the current status of the PLC."""
        return self.status_data['status']


def init_plcs(ip_addresses: List[str], plc_type: str, commands: Dict[str, int],status_bits= None, status_reg="V1") -> Dict[str, ConfigPLC]:
    plcs = {}
    for i, ip in enumerate(ip_addresses):
        plcs[f"{plc_type}{i + 1}"] = ConfigPLC(ip, commands, status_bits , status_reg)

    return plcs

def connect_plcs(plcs):
    for plc_id, plc in plcs.items():
        try:
            print(f"Connecting to {plc_id}...")
            plc.connect()
            plc.status = 'Connected'
            print(f"Connected to {plc_id}")
        except Exception as e:
            plc.status = 'PLC unreachable'
            print(f"Failed to connect to {plc_id}. Error: {e}")

    return plcs


def generate_status_indicators(plc: ConfigPLC) -> List[Dict[str]]:
    status_indicators = []
    if plc.connected:
        status_data = plc.status_data
        binary_representation = format(status_data['status'], '08b')[::-1]

        for i, bit in enumerate(binary_representation[:len(plc.status_bits)]):
            color = 'green' if bit == '1' else 'red'
            status_indicators.append({'text': plc.status_bits[i], 'color': color})

        return status_indicators
    else:
        return [{'text': "PLC not connected", 'color': 'red'}]
