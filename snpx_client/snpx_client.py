import socket
import struct
import time
from .digital_signal import DigitalSignal
from .position_data import PositionData
from .globals import FanucVariable, VariableTypes, ServiceReqCode, MemTypeCode, INIT_MSG, BASE_MSG

class SnpxClient:
    def __init__(self, ip : str = "127.0.0.1", port: int = 60008, connect_on_init : bool = False):
        self.ip = ip
        self.port = port
        self._snpx_seq = 0
        self.socket = None
        self._sys_vars = {}

        if connect_on_init:
            self.connect()
        
    def init_signals(self):
        """
        Initialize signal / memory objects. This is required every time the socket is modified
        """
        self.send_str("CLRASG")

        self.di = DigitalSignal(socket=self.socket, code=MemTypeCode.I, address=0)
        self.do = DigitalSignal(socket=self.socket, code=MemTypeCode.Q, address=0)
        self.ui = DigitalSignal(socket=self.socket, code=MemTypeCode.I, address=6000)
        self.uo = DigitalSignal(socket=self.socket, code=MemTypeCode.Q, address=6000)
        self.si = DigitalSignal(socket=self.socket, code=MemTypeCode.I, address=7000) # SOP input
        self.so = DigitalSignal(socket=self.socket, code=MemTypeCode.Q, address=7000) # SOP output
        self.cart_pos = PositionData(socket=self.socket, code=0x08, address=12000)
        self.j_pos = PositionData(socket=self.socket, code=0x08, address=12026)
        
        # --- Set any default assignments ---
        # Position variable
        self.set_asg("POS[G1:0] 0.0", FanucVariable(size=50, multiply=0), 1)


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

    @staticmethod
    def _recv_snpx_packet(sock) -> bytes:
        """
        Receive a complete SNPX packet from the robot.
        SNPX packets are at least 56 bytes. 
        Max packet size is 81 bytes
        """
        # read 56-byte packet
        packet = bytearray()
        packet = sock.recv(1024)
        
        # Return payload if packet length is 56
        if len(packet) <= 56:
            return bytes(packet)

        # extract payload if packet is longer
        # packet length can be found in bytes 
        count_field = int.from_bytes(packet[46:48], "little")
        payload_len = count_field
        if payload_len < 0:
            payload_len = 0

        # read payload
        payload = bytearray()
        while len(payload) < payload_len:
            chunk = sock.recv(payload_len - len(payload))
            if not chunk or len(chunk) < 1:
                raise ConnectionError("Socket closed before payload complete")
            payload.extend(chunk)

        return bytes(payload)
    

    def check_if_asg_avail(self, num: int, size: int = 1) -> bool:
        """
        Check if an assignment number range is available.
        Returns True if the assignment number range [num, num + size - 1] is available,
        False if any part of the range overlaps with existing variables.
        
        :param num: Starting assignment number to check
        :param size: Size in words (16-bit registers) that need to be available
        """
        # Check if num is within valid range (must be positive)
        if num < 1:
            return False
        
        # Check for overlap with existing variables
        vals = self._sys_vars.values()
        for v in vals:
            # guard in case stored value isn't the expected dict
            try:
                existing_index = v.get("index")
                existing_size = v.get("size", 1)
                
                # Check if the requested range overlaps with this variable's range
                if num < existing_index + existing_size and num + size > existing_index:
                    return False
            except Exception:
                continue
        return True

    def get_next_asg_num(self, size: int = 1) -> int:
        """
        Get the next available assignment number that can accommodate the given size.
        Considers the size of existing variables to find non-overlapping ranges.
        
        :param size: Size in words (16-bit registers) needed for the variable
        :returns: The next available assignment number
        """
        # Start with 1 and find the first available slot
        start_num = 1
        while True:
            if self.check_if_asg_avail(start_num, size):
                return start_num
            start_num += 1

    def set_asg(self, var_name: str, var_type: FanucVariable, asg_num: int = None):
        """
        Sets a variable assignment using the SETASG command.

        Variables given will be assigned to the $ASG_NUM at the asg_num specified.
        If no asg_num is given, it will find the next available num 
        """
        # Return if the variable has already been added
        if self._sys_vars.get(var_name) != None:
            return

        # Check assignment number
        if asg_num == None:
            asg_num = self.get_next_asg_num(var_type.size)
        elif not self.check_if_asg_avail(asg_num, var_type.size):
            raise ValueError(f"Assignment number {asg_num} is not available for size {var_type.size}")
        
        # Verify asg number is positive
        if asg_num < 1:
            raise ValueError("Assignment index must be greater than 0")

        command_string = f"SETASG {asg_num} {var_type.size} {var_name} {var_type.multiply}"
        self.send_str(command_string)

        # Add to dict so we don't set asg again if not needed
        self._sys_vars[var_name] = {
            "size" : var_type.size,
            "multiply": var_type.multiply,
            "index": asg_num
        }

    def read_sys_var(self, var_name: str, var_type: FanucVariable):
        """
        Read system variable by first assigning it to an %R register, then reading the register.
        
        :param var_name: Name of variable, usually starts with "$"
        :param var_type: Type of variable, must be one of VariableTypes
        :returns: The decoded value (float, int, or str)
        """

        # 1. Make sure variable is assigned in robot (and retrieve the assignment number/type info)
        self.set_asg(var_name=var_name, var_type=var_type)
        
        var_info = self._sys_vars.get(var_name)
        if var_info is None:
             raise Exception(f"Failed to assign variable {var_name}")

        asg_num = var_info["index"]
        size = var_info["size"] # Number of registers (words) to read
        multiply = var_info["multiply"]
        
        # %R register address is 0-based word address. For %R1, the address is 0 (0x0000).
        start_word_address = asg_num - 1
        
        # 2. Construct the Read Request packet
        command = BASE_MSG.copy()

        # Update word count (bytes 2-3 and 30-31)
        count = size * 2 # Number of 16-bit words (registers)
        
        command[2] = count & 0xFF
        command[3] = (count >> 8) & 0xFF
        command[30] = count & 0xFF 

        # Update Read Command fields (bytes 42-47)
        command[42] = ServiceReqCode.READ_SYS_MEMORY # (0x04)
        command[43] = MemTypeCode.R # Memory Area: %R (Register)
        command[44] = start_word_address & 0xFF
        command[45] = (start_word_address >> 8) & 0xFF
        
        # Length of data in bytes (size * 2 bytes/word)
        payload_len = size #* 2 #int(size / 2)
        command[46] = payload_len & 0xFF
        command[47] = (payload_len >> 8) & 0xFF

        # 3. Send the packet and receive the response
        self.socket.send(bytearray(command))
        payload = SnpxClient._recv_snpx_packet(self.socket)
        #print_bytes_with_index(payload)

        # Extract data payload
        data_start = 44
        data_end = data_start + (size * 2)
        data_bytes = payload[data_start : data_end]
        
        if len(payload) < 4:
             # The received data is less than expected
             # In a real network setup, you might need to try a different offset
             raise ValueError(f"Received only {len(data_bytes)} bytes of data for an expected {payload_len} bytes.")

        # Decode the payload
        value = None
        
        # Handle strings
        if var_type == VariableTypes.STRING:
            # STRING (160 bytes / 80 registers) -> ASCII string
            value = data_bytes.decode('ascii').strip('\x00')
            return value

        # Handle other types
        try:
            value = struct.unpack(var_type.fmt, data_bytes)[0]
        except Exception as e:
            print(f"Failed to unpack bytes {e}")

        return value
        
    def write_sys_var(self, var_name: str, var_type: FanucVariable, value):
        """
        Write system variable by first assigning it to an %R register, then writing to the register.
        
        :param var_name: Name of variable, usually starts with "$"
        :param var_type: Type of variable, must be one of VariableTypes
        :returns: The decoded value (float, int, or str)
        """

        # 1. Make sure variable is assigned in robot (and retrieve the assignment number/type info)
        self.set_asg(var_name=var_name, var_type=var_type)
        
        var_info = self._sys_vars.get(var_name)
        if var_info is None:
             raise Exception(f"Failed to assign variable {var_name}")

        asg_num = var_info["index"]
        size = var_info["size"] # Number of registers (words) to read
        multiply = var_info["multiply"]
        
        # %R register address is 0-based word address. For %R1, the address is 0 (0x0000).
        start_word_address = asg_num - 1
        
        # 2. Construct the Read Request packet
        command = BASE_MSG.copy()

        # Update word count (bytes 2-3 and 30-31)
        count = size * 2 # Number of 16-bit words (registers)
        
        command[2] = count & 0xFF
        command[3] = (count >> 8) & 0xFF
        command[30] = count & 0xFF 

        # Update Read Command fields (bytes 42-47)
        command[42] = ServiceReqCode.WRITE_SYS_MEMORY
        command[43] = MemTypeCode.R 
        command[44] = start_word_address & 0xFF
        command[45] = (start_word_address >> 8) & 0xFF
        
        # Length of data in bytes (size * 2 bytes/word)
        payload_len = size #* 2 #int(size / 2)
        command[46] = payload_len & 0xFF
        command[47] = (payload_len >> 8) & 0xFF
        
        # determine how many bytes the variable occupies (size is in 16-bit words)
        byte_len = var_type.size * 2

        # Handle strings
        if var_type == VariableTypes.STRING:
            # STRING (160 bytes / 80 registers) -> ASCII string
            payload = str(value).encode('ascii', errors='replace')[:byte_len]
            if len(payload) < byte_len:
                payload = payload + b'\x00' * (byte_len - len(payload))            
                return value

        # Handle other types
        else:
            try:
                payload = struct.pack(var_type.fmt, value)
            except Exception as e:
                print(f"Failed to unpack bytes {e}")
                return None

        # ensure payload is exactly byte_len
        if len(payload) < byte_len:
            payload = payload + b'\x00' * (byte_len - len(payload))
        elif len(payload) > byte_len:
            payload = payload[:byte_len]

        # Place payload into command starting at byte index 48 (one byte per entry)
        # command is a list of ints so iterating payload (bytes) yields ints 0-255
        for i, b in enumerate(payload):
            command[48 + i] = b

        # 3. Send the packet and receive the response
        self.socket.sendall(bytearray(command))

        # Cleanup socket
        _ = self.socket.recv(1024)

    def send_str(self, string: str) -> bytes:
        """
        Send a string command to the robot controller as a packet. Returns response from controller
        
        :param string: The string to send (e.g., "CLRASG")
        """
        # Convert string to ASCII bytes
        payload = string.encode('ascii')
        payload_len = len(payload)
        
         # Build command packet
        command = BASE_MSG.copy()
        command[2] = 0x03
        command[4] = len(string)
        command[9] = 0x02
        command[17] = 0x00
        command[30] = 0x03
        command[31] = 0x80
        command[42] = ServiceReqCode.PLC_STATUS
        command[43] = 0x00
        command[48] = 0x01
        command[49] = 0x01
        command[50] = 0x07
        command[51] = 0x38
        command[54] = payload_len & 0xFF
        command[55] = (payload_len >> 8) & 0xFF
        command.extend(payload)
        
        # Send
        self.socket.sendall(bytearray(command))

        # Receive Acknowledge (clear buffer)
        response = self.socket.recv(1024)
        return response

 
def print_bytes_with_index(bytearr : bytes):
    for i in range(0, len(bytearr)):
        print(f"[{i}] - {bytearr[i]}")








