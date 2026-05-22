import math
from .globals import BASE_MSG, ServiceReqCode
from .packet_utils import set_word_count, set_address, set_payload_length


class DigitalSignal:
    """
    Robot digital signal
    """

    def __init__(self, socket, code, address: int, index_from_zero: bool = False):
        self.socket = socket
        self.code = code
        self.address = address
        self.index_from_zero = index_from_zero

    @staticmethod
    def _decode_digital_outputs(response, requested_bits, bit_offset: int = 0) -> list[bool]:
        """
        Helper for decoding boolean values from robot byte responses

        :param response: Response from robot (hex string or bytes)
        :param requested_bits: Number of bits to decode
        :param bit_offset: Starting bit offset within the first byte (0-7)
        """
        if not response:
            print("No response received for digital outputs")
            return []

        if isinstance(response, bytes):
            response = response.hex()

        clean_hex = response.replace(" ", "").replace(":", "")
        data_hex = clean_hex[112:] if len(
            clean_hex) > 112 else clean_hex[88:-4]

        if len(data_hex) < 2:
            print("Response too short for digital output read")
            return []

        bool_list = []
        bits_decoded = 0
        first_byte = True

        for i in range(0, len(data_hex), 2):
            if bits_decoded >= requested_bits:
                break

            start_bit = bit_offset if first_byte else 0
            first_byte = False

            try:
                byte_val = int(data_hex[i:i+2], 16)
                for bit in range(start_bit, 8):
                    if bits_decoded >= requested_bits:
                        break
                    bool_list.append(bool((byte_val >> bit) & 1))
                    bits_decoded += 1
            except ValueError:
                bool_list.extend([False] * min(8 - start_bit,
                                 requested_bits - bits_decoded))
                bits_decoded += 8 - start_bit

        return bool_list

    def read(self, count: int, start_index: int = 1) -> list[bool]:
        """
        Read a list of bools from the robot's IO
        """

        if self.index_from_zero:
            start_index = self.address + start_index
        else:
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
        # 传递位偏移
        return self._decode_digital_outputs(resp.hex(), count, start_index)

    def write(self, value: list[bool], start_index: int = 1):
        """
        Write a list of boolean values to a digital signal in the robot starting at the specified index
        """
        if self.index_from_zero:
            start_index = self.address + start_index
        else:
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
        for bit_index in range(count):
            if value[bit_index]:
                byte_idx = bit_index // 8
                bit_pos = (start_index + bit_index) % 8
                payload[byte_idx] |= (1 << bit_pos)

        if count > 48:
            command.extend(payload)
            command[4] = len(payload)
        else:
            command[48:48] = payload
            command = command[:-len(payload)]

        self.socket.send(bytearray(command))

        # Cleanup after to remove garbage values
        _ = self.socket.recv(1024)
