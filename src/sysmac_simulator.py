# Sysmac Simulator Connection
# Copyright (C) 2024 Joseph Ryan
# Copyright (C) 2021 Simumatik AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import ctypes
import re


class SimulatorVariable:
    def __init__(self, revision: str, address: str, size: int):
        self.revision = revision
        self.address = address
        self.size = size
        self.type = None
        self.low_index = None
        self.high_index = None


class SysmacSimulator:

    def __init__(self):
        self.ip_address = '127.0.0.1'
        self.port = 7000
        self.nex_socket_dll = None
        self.handle = ctypes.c_short()
        self.variable_dictionary = {}

    def connect(self):
        self.nex_socket_dll = ctypes.WinDLL('C:\\Program Files\\OMRON\\Sysmac Studio\\MATLAB\\Win64\\NexSocket.dll')
        self.nex_socket_dll.NexSock_initialize()
        self.nex_socket_dll.NexSockClient_connect(ctypes.byref(self.handle),
                                                  self.ip_address.encode('utf-8'),
                                                  ctypes.c_int16(self.port))

    def disconnect(self):
        self.nex_socket_dll.NexSock_close(self.handle.value)
        self.nex_socket_dll.NexSock_terminate()

    def get_variable_info(self, variable_name: str):
        response, error = self.send_command(f'GetVarAddrText 1 VAR://{variable_name}')
        revision = response[0].decode('utf-8')
        address = response[2].decode('utf-8')[:-1]
        size = int(address.split(',')[-1])//8
        variable_info = SimulatorVariable(revision, address, size)
        return variable_info

    def populate_from_file(self, filename: str):
        with open(filename, 'r') as file:
            next(file)
            for line in file:
                tokens = line.rstrip().split()
                if len(tokens) > 1:
                    if re.search(r'\[.*?\]', tokens[1]):
                        indexes = re.findall(r'\[.*?\]', tokens[1])
                        if len(indexes) > 0:
                            indexes = re.sub(r'[\[{}\]]', '', indexes[0]).split('..')
                        index = int(indexes[0])
                        end = int(indexes[1])
                        while index <= end:
                            variable_name = tokens[0] + f'[{index}]'
                            sim_variable = self.get_variable_info(variable_name)
                            self.variable_dictionary[variable_name] = sim_variable
                            index = index + 1
                    else:
                        sim_variable = self.get_variable_info(tokens[0])
                        self.variable_dictionary[tokens[0]] = sim_variable

    def read_variable(self, variable_name: str):
        if variable_name not in self.variable_dictionary:
            self.variable_dictionary[variable_name] = self.get_variable_info(variable_name)
        variable_info = self.variable_dictionary[variable_name]
        command = f'AsyncReadMemText {variable_info.revision} 1 {variable_info.address},2'
        response = self.send_command(command)[0][0]
        return response

    def write_variable(self, variable_name: str, value):
        if variable_name not in self.variable_dictionary:
            self.variable_dictionary[variable_name] = self.get_variable_info(variable_name)
        variable_info = self.variable_dictionary[variable_name]
        command = f'AsyncWriteMemText {variable_info.revision} 1 {variable_info.address},2,' + value.hex()
        response = self.send_command(command)
        return response

    def send_command(self, command):
        response = []
        error = None
        buffer = ctypes.create_string_buffer(512)
        self.nex_socket_dll.NexSock_send(self.handle, command.encode('utf-8'), len(command))
        while True:
            response_length = self.nex_socket_dll.NexSock_receive(self.handle, buffer, 512)
            if response_length == 0:
                break
            elif response_length < 0:
                error = buffer.value.decode('utf-8')
            else:
                response.append(buffer[:response_length])
        return response, error
