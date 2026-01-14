from dataclasses import dataclass


# Packet values should be kept in hex value for debugging with Wireshark
@dataclass
class VariableInfo():
    size : int # size in bytes
    multiply : int  # multiply - typically only used for INTs
    fmt: str = ""


class VariableTypes:
    INT = VariableInfo(size=2, multiply=1, fmt="<i")
    REAL = VariableInfo(size=2, multiply=0, fmt="<f")
    STRING = VariableInfo(size=80, multiply=0)


@dataclass
class SystemVariable:
    name: str
    data: VariableInfo

# Used at byte location 42
class ServiceReqCode:
    PLC_STATUS             = 0x00
    RETURN_PROG_NAME       = 0x03
    READ_SYS_MEMORY        = 0x04     # Used to read general memory register (Example: %R12344)
    READ_TASK_MEMORY       = 0x05
    READ_PROG_MEMORY       = 0x06
    WRITE_SYS_MEMORY       = 0x07
    WRITE_TASK_MEMORY      = 0x08
    WRITE_PROG_MEMORY      = 0x09
    RETURN_DATETIME        = 0x25
    RETURN_CONTROLLER_TYPE = 0x43


# Used at byte location 43
class MemTypeCode:
    R  = 0x08    # Register (Word)
    AI = 0x0a    # Analog Input (Word)
    AQ = 0x0c    # Analog Output (Word)
    I  = 0x48    # Descrete Input (Byte)
    Q  = 0x46    # Descrete Output (Byte)

BASE_MSG = [
    0x02,        # 00 - Type (03 is Return, 02 is Transmit)
    0x00,        # 01 - Reserved/Unknown
    0x00,        # 02 - Seq Number - FILL AT RUNTIME
    0x00,        # 03 - Reserved/Unknown
    0x00,        # 04 - Text Length - FILL AT RUNTIME ???
    0x00,        # 05 - Reserved/Unknown
    0x00,        # 06 - Reserved/Unknown
    0x00,        # 07 - Reserved/Unknown
    0x00,        # 08 - Reserved/Unknown
    0x01,        # 09 - Reserved/Unknown*
    0x00,        # 10 - Reserved/Unknown
    0x00,        # 11 - Reserved/Unknown
    0x00,        # 12 - Reserved/Unknown
    0x00,        # 13 - Reserved/Unknown
    0x00,        # 14 - Reserved/Unknown
    0x00,        # 15 - Reserved/Unknown
    0x00,        # 16 - Reserved/Unknown
    0x01,        # 17 - Reserved/Unknown*
    0x00,        # 18 - Reserved/Unknown
    0x00,        # 19 - Reserved/Unknown
    0x00,        # 20 - Reserved/Unknown
    0x00,        # 21 - Reserved/Unknown
    0x00,        # 22 - Reserved/Unknown
    0x00,        # 23 - Reserved/Unknown
    0x00,        # 24 - Reserved/Unknown
    0x00,        # 25 - Reserved/Unknown
    0x00,        # 26 - Time Seconds - FILL AT RUNTIME
    0x00,        # 27 - Time Minutes - FILL AT RUNTIME
    0x00,        # 28 - Time Hours   - FILL AT RUNTIME
    0x00,        # 29 - Reserved/Unknown
    0x00,        # 30 - Size ?????
    0xc0,        # 31 - Message Type
    0x00,        # 32 - Mailbox Source
    0x00,        # 33 - Mailbox Source
    0x00,        # 34 - Mailbox Source
    0x00,        # 35 - Mailbox Source
    0x10,        # 36 - Mailbox Destination
    0x0e,        # 37 - Mailbox Destination
    0x00,        # 38 - Mailbox Destination
    0x00,        # 39 - Mailbox Destination
    0x01,        # 40 - Packet Number
    0x01,        # 41 - Total Packet Number
    0x04,        # 42 - Service Request Code - (Operation Type SERVICE_REQUEST_CODE)
    0x46,        # 43 - Request Dependent Space (For Reading: set MEMORY_TYPE_CODE)
    0x00,        # 44 - Request Dependent Space (For Reading: set to Address - 1)(LSB)
    0x00,        # 45 - Request Dependent Space (For Reading: set to Address - 1)(MSB)
    0x00,        # 46 - Request Dependent Space (For Reading: Data Size Bytes)(LSB)
    0x00,        # 47 - Request Dependent Space (For Reading: Data Size Bytes)(MSB)
    0x00,        # 48 - Reserved/Unknown
    0x00,        # 49 - Reserved/Unknown
    0x00,        # 50 - Reserved/Unknown
    0x00,        # 51 - Reserved/Unknown
    0x00,        # 52 - Reserved/Unknown
    0x00,        # 53 - Reserved/Unknown
    0x00,        # 54 - Reserved/Unknown
    0x00         # 55 - Reserved/Unknown
]

INIT_MSG =  """08:00:01:00:00:00:00:00:00:01:00:
            00:00:00:00:00:00:01:00:00:00:00:00:
            00:00:00:00:00:00:00:01:c0:00:00:00:
            00:10:0e:00:00:01:01:4f:01:00:00:00:
            00:00:00:00:00:00:00:00:00"""