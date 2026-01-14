import socket
from .globals import VariableInfo

class SysVarsManager:
    def __init__(self, sock: socket, vars: dict[str, VariableInfo]):
        self.sock = sock
        self._vars = vars

    def set_asg(self):
        pass
    
    def read(self):
        pass