import struct
from .globals import BASE_MSG, MemTypeCode
from .packet_utils import set_word_count

class PositionData:
    def __init__(self, socket, code, address: int):
        self.code = code
        self.address = address
        self.socket = socket
        self._snpx_seq = 0

    def read(self):
        """
        Read joints from robot
        Should probably make this more dynamic / smarter
        """

        # build packet
        command = BASE_MSG.copy()
        set_word_count(command, 0x04)
        command[43] = MemTypeCode.R # memory type code
        command[46] = 0x32 # size in bytes

        # Request Joints
        self.socket.sendall(bytearray(command))
        response = self.socket.recv(2048)

        # Trim response down to the joint values
        float_data = response[108:-24]

        # Decode as 32-bit little-endian floats
        joint_values = []
        for i in range(0, len(float_data), 4):
            chunk = float_data[i:i+4]
            if len(chunk) < 4:
                break
            val = struct.unpack("<f", chunk)[0]
            joint_values.append(val)

        return joint_values

