"""
System Variables Manager for SNPX client.
Handles assignment management and read/write operations for system variables.
"""
import socket
import struct
from .globals import VariableInfo, VariableTypes, ServiceReqCode, MemTypeCode
from .packet_utils import build_memory_read_packet, build_memory_write_packet

class SystemVariableGroup:
    """
    Represents a group of system variables that are assigned sequentially.
    Allows reading and writing all variables in the group at once.
    """
    
    def __init__(self, manager, variables: list[tuple[str, VariableInfo]], var_infos: list[dict]):
        """
        Initialize a system variable group.
        
        :param manager: Reference to SystemVariablesManager instance
        :param variables: List of (var_name, var_type) tuples
        :param var_infos: List of variable info dicts from _sys_vars
        """
        self._manager = manager
        self._variables = variables  # List of (var_name, var_type) tuples
        self._var_infos = var_infos  # List of variable info dicts
        
        # Calculate total size and starting address
        self._start_asg_num = var_infos[0]["index"]
        self._total_size = sum(info["size"] for info in var_infos)
        self._start_address = self._start_asg_num - 1
    
    def read(self) -> tuple:
        """
        Read all variables in the group at once.
        
        :returns: Tuple of values in the same order as variables were added
        """
        # Build a single read packet for all variables
        command = build_memory_read_packet(
            mem_type=MemTypeCode.R,
            address=self._start_address,
            size=self._total_size,
            service_code=ServiceReqCode.READ_SYS_MEMORY
        )
        
        # Send the packet and receive the response
        self._manager.socket.send(bytearray(command))
        payload = self._manager.socket.recv(1024)
        print(payload)
        
        # Extract and decode each variable
        values = []
        current_offset = 0
        
        for (var_name, var_type), var_info in zip(self._variables, self._var_infos):
            size_bytes = var_info["size"] * 2  # Convert words to bytes
            
            # Extract data for this variable (starting at byte 44 + current_offset)
            data_start = 56 + current_offset
            data_end = data_start + size_bytes
            data_bytes = payload[data_start:data_end]
            
            if len(data_bytes) < size_bytes:
                raise ValueError(f"Received insufficient data for variable {var_name}")
            
            # Decode the value
            value = self._manager._decode_value(data_bytes, var_type)
            values.append(value)
            
            current_offset += size_bytes
        
        return tuple(values)
    
    def write(self, values: tuple):
        """
        Write all variables in the group at once.
        
        :param values: Tuple of values in the same order as variables were added
        """
        if len(values) != len(self._variables):
            raise ValueError(f"Expected {len(self._variables)} values, got {len(values)}")
        
        # Encode all values into a single payload
        payload_parts = []
        for (var_name, var_type), value in zip(self._variables, values):
            encoded = self._manager._encode_value(value, var_type)
            payload_parts.append(encoded)
        
        # Concatenate all payloads
        combined_payload = b''.join(payload_parts)
        
        # Build a single write packet for all variables
        command = build_memory_write_packet(
            mem_type=MemTypeCode.R,
            address=self._start_address,
            size=self._total_size,
            service_code=ServiceReqCode.WRITE_SYS_MEMORY,
            payload=combined_payload
        )
        
        # Send the packet and receive the response
        self._manager.socket.sendall(bytearray(command))
        
        # Cleanup socket
        _ = self._manager.socket.recv(1024)


class SystemVariablesManager:
    """
    Manages system variable assignments and read/write operations.
    Handles automatic assignment allocation and tracking.
    """
    
    def __init__(self, sock: socket.socket, send_str_callback):
        """
        Initialize the system variables manager.
        
        :param sock: Socket connection to robot controller
        :param send_str_callback: Callback function to send string commands (takes string, returns bytes)
        """
        self.socket = sock
        self._send_str = send_str_callback
        self._sys_vars = {}
    
    def check_if_asg_avail(self, num: int, size: int = 1) -> bool:
        """
        Check if an assignment number range is available.
        Returns True if the assignment number range [num, num + size - 1] is available,
        False if any part of the range overlaps with existing variables.
        
        :param num: Starting assignment number to check
        :param size: Size in words (16-bit registers) that need to be available
        :returns: True if available, False otherwise
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
    
    def set_asg(self, var_name: str, var_type: VariableInfo, asg_num: int = None):
        """
        Sets a variable assignment using the SETASG command.

        Variables given will be assigned to the $ASG_NUM at the asg_num specified.
        If no asg_num is given, it will find the next available num.
        
        :param var_name: Name of the system variable
        :param var_type: Variable type information
        :param asg_num: Optional assignment number (auto-assigned if None)
        """
        # Return if the variable has already been added
        if self._sys_vars.get(var_name) is not None:
            return

        # Check assignment number
        if asg_num is None:
            asg_num = self.get_next_asg_num(var_type.size)
        elif not self.check_if_asg_avail(asg_num, var_type.size):
            raise ValueError(f"Assignment number {asg_num} is not available for size {var_type.size}")
        
        # Verify asg number is positive
        if asg_num < 1:
            raise ValueError("Assignment index must be greater than 0")

        command_string = f"SETASG {asg_num} {var_type.size} {var_name} {var_type.multiply}"
        self._send_str(command_string)

        # Add to dict so we don't set asg again if not needed
        self._sys_vars[var_name] = {
            "size": var_type.size,
            "multiply": var_type.multiply,
            "index": asg_num
        }
    
    def _encode_value(self, value, var_type: VariableInfo) -> bytes:
        """
        Encode a value to bytes based on variable type.
        
        :param value: Value to encode
        :param var_type: Variable type information
        :returns: Encoded bytes
        """
        # Determine how many bytes the variable occupies (size is in 16-bit words)
        byte_len = var_type.size * 2
        
        # Handle strings
        if var_type == VariableTypes.STRING:
            # STRING (160 bytes / 80 registers) -> ASCII string
            payload = str(value).encode('ascii', errors='replace')[:byte_len]
            if len(payload) < byte_len:
                payload = payload + b'\x00' * (byte_len - len(payload))
            return payload
        
        # Handle other types
        try:
            payload = struct.pack(var_type.fmt, value)
        except Exception as e:
            raise ValueError(f"Failed to pack value {value} with format {var_type.fmt}: {e}")
        
        # Ensure payload is exactly byte_len
        if len(payload) < byte_len:
            payload = payload + b'\x00' * (byte_len - len(payload))
        elif len(payload) > byte_len:
            payload = payload[:byte_len]
        
        return payload
    
    def _decode_value(self, data_bytes: bytes, var_type: VariableInfo):
        """
        Decode bytes to a value based on variable type.
        
        :param data_bytes: Bytes to decode
        :param var_type: Variable type information
        :returns: Decoded value (float, int, or str)
        """
        # Handle strings
        if var_type == VariableTypes.STRING:
            # STRING (160 bytes / 80 registers) -> ASCII string
            value = data_bytes.decode('ascii').strip('\x00')
            return value

        # Handle other types
        try:
            value = struct.unpack(var_type.fmt, data_bytes)[0]
        except Exception as e:
            raise ValueError(f"Failed to unpack bytes with format {var_type.fmt}: {e}")

        return value
    
    def read(self, var_name: str, var_type: VariableInfo):
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
        size = var_info["size"]  # Number of registers (words) to read
        
        # %R register address is 0-based word address. For %R1, the address is 0 (0x0000).
        start_word_address = asg_num - 1
        
        # 2. Construct the Read Request packet
        command = build_memory_read_packet(
            mem_type=MemTypeCode.R,
            address=start_word_address,
            size=size,
            service_code=ServiceReqCode.READ_SYS_MEMORY
        )

        # 3. Send the packet and receive the response
        self.socket.send(bytearray(command))
        payload = self.socket.recv(1024)

        # Extract data payload
        data_start = 44
        data_end = data_start + (size * 2)
        data_bytes = payload[data_start:data_end]
        
        if len(payload) < 4:
            # The received data is less than expected
            raise ValueError(f"Received only {len(data_bytes)} bytes of data for an expected {size * 2} bytes.")

        # Decode the payload
        return self._decode_value(data_bytes, var_type)
    
    def write(self, var_name: str, var_type: VariableInfo, value):
        """
        Write system variable by first assigning it to an %R register, then writing to the register.
        
        :param var_name: Name of variable, usually starts with "$"
        :param var_type: Type of variable, must be one of VariableTypes
        :param value: Value to write (float, int, or str)
        """
        # 1. Make sure variable is assigned in robot (and retrieve the assignment number/type info)
        self.set_asg(var_name=var_name, var_type=var_type)
        
        var_info = self._sys_vars.get(var_name)
        if var_info is None:
            raise Exception(f"Failed to assign variable {var_name}")

        asg_num = var_info["index"]
        size = var_info["size"]  # Number of registers (words) to read
        
        # %R register address is 0-based word address. For %R1, the address is 0 (0x0000).
        start_word_address = asg_num - 1
        
        # 2. Encode the value to bytes
        payload = self._encode_value(value, var_type)
        
        # 3. Construct the Write Request packet
        command = build_memory_write_packet(
            mem_type=MemTypeCode.R,
            address=start_word_address,
            size=size,
            service_code=ServiceReqCode.WRITE_SYS_MEMORY,
            payload=payload
        )

        # 4. Send the packet and receive the response
        self.socket.sendall(bytearray(command))

        # Cleanup socket
        _ = self.socket.recv(1024)
    
    def create_var_group(self, variables: list[tuple[str, VariableInfo]]) -> SystemVariableGroup:
        """
        Create a group of system variables with sequential assignments.
        Each variable is assigned immediately after the previous one, with assignment
        numbers increasing by the size of each variable.
        
        :param variables: List of (var_name, var_type) tuples
        :returns: SystemVariableGroup object for reading/writing all variables
        """
        if not variables:
            raise ValueError("Variable list cannot be empty")
        
        # Check if any variables are already assigned
        for var_name, var_type in variables:
            if self._sys_vars.get(var_name) is not None:
                raise ValueError(f"Variable {var_name} is already assigned. Cannot add to group.")
        
        # Get starting assignment number
        first_size = variables[0][1].size
        start_asg_num = self.get_next_asg_num(first_size)
        
        # Assign each variable sequentially
        var_infos = []
        current_asg_num = start_asg_num
        
        for var_name, var_type in variables:
            # Assign the variable
            self.set_asg(var_name, var_type, asg_num=current_asg_num)
            
            # Get the stored info
            var_info = self._sys_vars.get(var_name)
            if var_info is None:
                raise Exception(f"Failed to assign variable {var_name} in group")
            
            var_infos.append(var_info)
            
            # Move to next assignment number (current + size)
            current_asg_num += var_type.size
        
        # Create and return the group
        return SystemVariableGroup(self, variables, var_infos)