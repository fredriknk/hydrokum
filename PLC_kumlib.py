import logging
import snap7
import time
import threading
logging.basicConfig(level=logging.WARNING)

class ConfigPLC:
    def __init__(self, ip_address, commands, statusAddr, update_status=True):
        self.logger = logging.getLogger(__name__)
        self.plc = snap7.logo.Logo()
        self.ip_address = ip_address
        self.connected = False
        self.commands = commands

        self.status_data = {
            'address': statusAddr,
            'byte_array': bytearray(1),
            'status': 0
        }

        if update_status:
            self.status_thread = threading.Thread(target=self._update_status, daemon=True)
        else:
            self.status_thread = None

    def connect(self, timeout=5):
        try:
            self.plc.connect(self.ip_address, 0x0300, 0x0200)
            self.connected = self.plc.get_connected()
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")

        if self.connected:
            self.logger.info("Connected")
            if self.status_thread:
                self.status_thread.start()  # start the status update thread if available
        else:
            self.logger.error("Connection failed")

    def disconnect(self):
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join()  # stop the status update thread if available
        self.plc.disconnect()
        self.logger.info("Disconnected")

    def write_command(self, address, command, delay=0.1):
        if self.connected:
            self.plc.write(address, command)
            self.logger.info(f"Wrote command 0b{command:08b} to {address}")
            # For PLC_kum type
            if command in [self.commands.get('open'), self.commands.get('close'), self.commands.get('estop')]:
                time.sleep(delay)  # delay in seconds before sending 'none' command
                self.plc.write(address, self.commands.get('none', 0b0000000))
                self.logger.info(f"Wrote command 0b{self.commands.get('none', 0b0000000):08b} to {address}")
        else:
            self.logger.error("Not connected to the PLC. Please connect first.")

    def get_command_list(self):
        return self.commands.keys()

    def _update_status(self):
        while self.connected:
            try:
                self.status_data['status'] = self.plc.read(self.status_data['address'])
                time.sleep(1.0)  # Update status every 0.3 seconds
            except Exception as e:
                self.logger.error(f"Error updating status: {e}")
                self.connected = False

    def get_status(self):
        return self.status_data['status']

def init_plcs(ip_addresses, type , commands):
        plcs = {}

        # Define your PLCs
        for i, ip in enumerate(ip_addresses,commands):
            plcs[f"{type}{i + 1}"] = ConfigPLC(ip,commands)

        # Connect all PLCs
        for plc_id in plcs.keys():
            try:
                print(f"Connecting to {plc_id}...")
                plcs[plc_id].connect()
                plcs[plc_id].status = 'Connected'
                print(f"Connected to {plc_id}")
            except Exception as e:
                plcs[plc_id].status = 'PLC unreachable'
                print(f"Failed to connect to {plc_id}. Error: {str(e)}")

        return plcs


def generate_status_indicators(plc, bit_meanings):
    status_indicators = []
    if plc.status == 'Connected':
        status_data = plc.status_data
        binary_representation = format(status_data['status'], '08b')[::-1]

        for i, bit in zip(range(6), binary_representation):
            color = 'green' if bit == '1' else 'red'
            status_indicators.append({'text': bit_meanings[i], 'color': color})

        return status_indicators

    else:
        status_indicators.append({'text': "PLC not connected", 'color': 'red'})
        return status_indicators