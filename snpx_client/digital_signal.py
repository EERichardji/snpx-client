import math
from .globals import BASE_MSG, ServiceReqCode
from .packet_utils import set_word_count, set_address, set_payload_length

class DigitalSignal:
    """
    Robot digital signal
    """

    def __init__(self, socket, code, address: int):
        self.socket = socket
        self.code = code
        self.address = address

    @staticmethod
    def _decode_digital_outputs(response, requested_bits) -> list[bool]:
        """
        Helper for decoding boolean values from robot byte responses
        """
        if not response:
            print("No response received for digital outputs")
            return []

        if isinstance(response, bytes):
            response = response.hex()

        clean_hex = response.replace(" ", "").replace(":", "")
        data_hex = clean_hex[112:] if len(clean_hex) > 112 else clean_hex[88:-4]

        if len(data_hex) < 2:
            print("Response too short for digital output read")
            return []

        bool_list = []
        bits_decoded = 0

        for i in range(0, len(data_hex), 2):
            if bits_decoded >= requested_bits:
                break

            try:
                byte_val = int(data_hex[i:i+2], 16)
                for bit in range(8):
                    if bits_decoded >= requested_bits:
                        break
                    bool_list.append(bool((byte_val >> bit) & 1))
                    bits_decoded += 1
            except ValueError:
                for _ in range(8):
                    if bits_decoded >= requested_bits:
                        break
                    bool_list.append(False)
                    bits_decoded += 1

        return bool_list

    def read(self, count: int, start_index : int = 1) -> list[bool]:
        """
        Read a list of bools from the robot's IO
        """
        
        start_index = self.address + start_index - 1
        command = BASE_MSG.copy()

        # Use packet utilities for common fields
        set_word_count(command, count)
        set_address(command, start_index)
        
        # Memory type code
        command[43] = self.code
        
        # Payload length (byte allocation)
        byte_allocation = ((count + 7) // 8) * 8
        set_payload_length(command, byte_allocation)

        self.socket.send(bytearray(command))
        resp = self.socket.recv(1024)
        return self._decode_digital_outputs(resp.hex(), count)


    def write(self, value : list[bool], start_index: int = 1):
        """
        Write a list of boolean values to a digital signal in the robot starting at the specified index
        """
        start_index = self.address + start_index - 1
        command = BASE_MSG.copy()

        count = len(value)
        if count == 0:
            return

        # Custom fields for digital write
        if count <= 48:
            command[9], command[17] = 0x01, 0x01
        else:
            command[9], command[17], command[31] = 0x02, 0x02, 0x80

        # Use packet utilities for common fields
        set_word_count(command, count)
        set_address(command, start_index)
        
        # Service code and memory type
        command[42] = ServiceReqCode.WRITE_SYS_MEMORY
        command[43] = self.code

        # Payload length (byte allocation)
        byte_allocation = ((count + 7) // 8) * 8
        set_payload_length(command, byte_allocation)

        if count > 48:
            command[42:42] = [0x00] * 6
            command[48:48] = [0x01, 0x01]
            command = command[:-8]

        byte_count = math.ceil(count / 8)
        payload = bytearray(byte_count)
        for i in range(byte_count):
            byte = 0
            for j in range(8):
                bit_index = i * 8 + j
                if bit_index < count and value[bit_index]:
                    byte |= (1 << j)
            if i < len(payload):
                payload[i] = byte

        if count > 48:
            command.extend(payload)
            command[4] = len(payload)
        else:
            command[48:48] = payload
            command = command[:-len(payload)]

        self.socket.send(bytearray(command))

        # Cleanup after to remove garbage values
        _ = self.socket.recv(1024)
