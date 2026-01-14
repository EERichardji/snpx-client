from .globals import VariableInfo
import socket


class VariableGroup:
    def __init__(self, sock: socket, vars: dict[str, VariableInfo]):
        self.vars = vars

    def read_all(self):
        pass
