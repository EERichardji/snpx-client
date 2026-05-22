import socket
import time
from .digital_signal import DigitalSignal
from .position_data import PositionData
from .system_variables import SystemVariablesManager
from .packet_utils import build_string_command_packet
from .globals import VariableInfo, VariableTypes, INIT_MSG, MemTypeCode,SegmentOffset

class SnpxClient:
    def __init__(self, ip: str = "127.0.0.1", port: int = 60008, connect_on_init: bool = False):
        self.ip = ip
        self.port = port
        self._snpx_seq = 0
        self.socket = None
        self.sys_vars = None  # Will be initialized in connect()

        if connect_on_init:
            self.connect()

    def init_signals(self):
        """
        Initialize signal / memory objects. This is required every time the socket is modified
        """
        self.send_str("CLRASG")

        # Initialize system variables manager
        self.sys_vars = SystemVariablesManager(self.socket, self.send_str)

        self.di = DigitalSignal(socket=self.socket, code=MemTypeCode.I, address=SegmentOffset.SDIO)
        self.do = DigitalSignal(socket=self.socket, code=MemTypeCode.Q, address=SegmentOffset.SDIO)
        self.ri = DigitalSignal(socket=self.socket, code=MemTypeCode.I, address=SegmentOffset.RDIO)
        self.ro = DigitalSignal(socket=self.socket, code=MemTypeCode.Q, address=SegmentOffset.RDIO)
        self.ui = DigitalSignal(socket=self.socket, code=MemTypeCode.I, address=SegmentOffset.UOP)
        self.uo = DigitalSignal(socket=self.socket, code=MemTypeCode.Q, address=SegmentOffset.UOP)
        self.si = DigitalSignal(socket=self.socket, code=MemTypeCode.I, address=SegmentOffset.SOP,
                                index_from_zero=True)  # SOP input
        self.so = DigitalSignal(socket=self.socket, code=MemTypeCode.Q, address=SegmentOffset.SOP,
                                index_from_zero=True)  # SOP output
        self.cart_pos = PositionData(socket=self.socket, code=MemTypeCode.R, address=12000)
        self.j_pos = PositionData(socket=self.socket, code=MemTypeCode.R, address=12026)

        # --- Set any default assignments ---
        # Position variable so that the position data class can work.
        # This is kind of janky - means the position data class leans heavily on the
        # client to create the assignment instead of doing it itself.
        self.sys_vars.set_asg("POS[G1:0] 0.0", VariableInfo(size=50, multiply=0), 1)

    def connect(self):
        """
        Sends packets to the robot controller to initialize the connection, clear past assignments, and define protocols
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.ip, self.port))
        self.socket.settimeout(5.0)
        time.sleep(0.1)

        # Empty initialization
        # Send init message (empty byte array )
        self.socket.send(b'\x00' * 56)
        if self.socket.recv(64)[0] != 1:
            raise Exception("Failed SNPX init")

        # Send init messages, first for protocol, second to clear previous assignments
        self.socket.send(bytearray.fromhex(INIT_MSG.replace(':', '')))
        self.socket.recv(1024)

        self.init_signals()

    def disconnect(self):
        try:
            self.socket.close()
        except Exception as e:
            print(f"Failed to close socket listening on {self.ip}:{self.port} - {e}")

    def send_str(self, string: str) -> bytes:
        """
        Send a string command to the robot controller as a packet. Returns response from controller

        :param string: The string to send (e.g., "CLRASG")
        """
        # Build command packet using utility function
        command = build_string_command_packet(string)

        # Send
        self.socket.sendall(bytearray(command))

        # Receive Acknowledge (clear buffer)
        response = self.socket.recv(1024)
        return response









