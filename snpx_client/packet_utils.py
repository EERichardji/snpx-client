"""
Packet construction utilities for SNPX protocol.
Contains helper functions for building SNPX packets.
"""
from .globals import BASE_MSG, ServiceReqCode

def print_bytes_with_index(bytearr : bytes):
    for i in range(0, len(bytearr)):
        print(f"[{i}] - {bytearr[i]}")

def set_word_count(command: list[int], count: int) -> None:
    """
    Set word count in packet header (bytes 2-3 and 30).
    
    :param command: Packet command list to modify
    :param count: Word count value
    """
    command[2] = count & 0xFF
    command[3] = (count >> 8) & 0xFF
    command[30] = count & 0xFF


def set_address(command: list[int], address: int) -> None:
    """
    Set memory address in packet (bytes 44-45).
    
    :param command: Packet command list to modify
    :param address: Memory address (0-based)
    """
    command[44] = address & 0xFF
    command[45] = (address >> 8) & 0xFF


def set_payload_length(command: list[int], length: int) -> None:
    """
    Set payload length in packet (bytes 46-47).
    
    :param command: Packet command list to modify
    :param length: Payload length in bytes
    """
    command[46] = length & 0xFF
    command[47] = (length >> 8) & 0xFF


def build_memory_read_packet(mem_type: int, address: int, size: int, service_code: int) -> list[int]:
    """
    Build a memory read packet for SNPX protocol.
    
    :param mem_type: Memory type code (MemTypeCode)
    :param address: Memory address (0-based)
    :param size: Size in words (16-bit registers)
    :param service_code: Service request code (ServiceReqCode)
    :returns: Complete packet as list of integers
    """
    command = BASE_MSG.copy()
    
    # Word count (bytes 2-3 and 30)
    count = size * 2  # Number of 16-bit words
    set_word_count(command, count)
    
    # Service request code and memory type (bytes 42-43)
    command[42] = service_code
    command[43] = mem_type
    
    # Address (bytes 44-45)
    set_address(command, address)
    
    # Payload length (bytes 46-47)
    payload_len = size
    set_payload_length(command, payload_len)
    
    return command


def build_memory_write_packet(mem_type: int, address: int, size: int, service_code: int, payload: bytes) -> list[int]:
    """
    Build a memory write packet for SNPX protocol.
    
    :param mem_type: Memory type code (MemTypeCode)
    :param address: Memory address (0-based)
    :param size: Size in words (16-bit registers)
    :param service_code: Service request code (ServiceReqCode)
    :param payload: Data payload to write
    :returns: Complete packet as list of integers
    """
    command = BASE_MSG.copy()
    
    # Word count (bytes 2-3 and 30)
    count = size * 2  # Number of 16-bit words
    set_word_count(command, count)
    
    # Service request code and memory type (bytes 42-43)
    command[42] = service_code
    command[43] = mem_type
    
    # Address (bytes 44-45)
    set_address(command, address)
    
    # Payload length (bytes 46-47)
    payload_len = size
    set_payload_length(command, payload_len)
    
    # Place payload into command starting at byte index 48
    # command is a list of ints so iterating payload (bytes) yields ints 0-255
    # Ensure command list is long enough for payload
    required_length = 48 + len(payload)
    if len(command) < required_length:
        command.extend([0] * (required_length - len(command)))
    
    for i, b in enumerate(payload):
        command[48 + i] = b
    
    return command


def build_string_command_packet(string: str) -> list[int]:
    """
    Build a string command packet for SNPX protocol.
    This is the implementation of send_str() moved to utilities.
    
    :param string: The string command to send (e.g., "CLRASG")
    :returns: Complete packet as list of integers
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
    
    return command
