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
import struct


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
                        data_type = re.sub(r'\[.*?\]','', tokens[1])
                        if len(indexes) > 0:
                            indexes = re.sub(r'[\[{}\]]', '', indexes[0]).split('..')
                        index = int(indexes[0])
                        end = int(indexes[1])
                        while index <= end:
                            variable_name = tokens[0] + f'[{index}]'
                            sim_variable = self.get_variable_info(variable_name)
                            sim_variable.type = data_type
                            self.variable_dictionary[variable_name] = sim_variable
                            index = index + 1
                    else:
                        sim_variable = self.get_variable_info(tokens[0])
                        sim_variable.type = tokens[1]
                        self.variable_dictionary[tokens[0]] = sim_variable

    def read_variable(self, variable_name, type=None):
        if isinstance(variable_name, str) and type is not None:
            if variable_name not in self.variable_dictionary:
                self.variable_dictionary[variable_name] = self.get_variable_info(
                    variable_name)
                self.variable_dictionary[variable_name].type = type
            variable_info = self.variable_dictionary[variable_name]
        elif isinstance(variable_name, str) and type is None:
            if variable_name in self.variable_dictionary:
                variable_info = self.variable_dictionary[variable_name]
            else:
                return
        else:
            variable_info = variable_name
        command = f'AsyncReadMemText {variable_info.revision} 1 {variable_info.address},2'
        response = self.send_command(command)[0][0]
        response = self._unpack_bytes(response, variable_info.type)
        return response

    def write_variable(self, variable_name, value, type=None):
        if isinstance(variable_name, str) and type is not None:
            if variable_name not in self.variable_dictionary:
                self.variable_dictionary[variable_name] = self.get_variable_info(
                    variable_name)
                self.variable_dictionary[variable_name].type = type
            variable_info = self.variable_dictionary[variable_name]
        elif isinstance(variable_name, str) and type is None:
            if variable_name in self.variable_dictionary:
                variable_info = self.variable_dictionary[variable_name]
            else:
                return
        else:
            variable_info = variable_name
        send_bytes = self._pack_bytes(
            value, variable_info.type, variable_info.size)
        command = f'AsyncWriteMemText {variable_info.revision} 1 {variable_info.address},2,' + send_bytes.hex()
        response = self.send_command(command)
        return response

    def _unpack_bytes(self, data, data_type):
        result = None
        if data_type == 'BOOL':
            if data == b'\x01':
                result = True
            else:
                result = False
        elif data_type == 'SINT':
            result = struct.unpack("<b", data)[0]
        elif data_type == 'INT':
            result = struct.unpack("<h", data)[0]
        elif data_type == 'DINT':
            result = struct.unpack("<l", data)[0]
        elif data_type == 'LINT':
            result = struct.unpack("<q", data)[0]
        elif data_type == 'USINT':
            result = struct.unpack("<B", data)[0]
        elif data_type == 'UINT':
            result = struct.unpack("<H", data)[0]
        elif data_type == 'UDINT':
            result = struct.unpack("<L", data)[0]
        elif data_type == 'ULINT':
            result = struct.unpack("<Q", data)[0]
        elif data_type == 'REAL':
            result = struct.unpack("<f", data)[0]
        elif data_type == 'LREAL':
            result = struct.unpack("<d", data)[0]
        elif 'STRING' in data_type:
            result = data.decode('utf-8').strip('\x00')
        else:
            pass
        return result

    def _pack_bytes(self, data, data_type, size):
        packed_bytes = b''
        if data_type == 'BOOL':
            if data:
                packed_bytes = b'\x01'
            else:
                packed_bytes = b'\x00'
        elif data_type == 'SINT':
            packed_bytes = struct.pack("<b", data)
        elif data_type == 'INT':
            packed_bytes = struct.pack("<h", data)
        elif data_type == 'DINT':
            packed_bytes = struct.pack("<l", data)
        elif data_type == 'LINT':
            packed_bytes = struct.pack("<q", data)
        elif data_type == 'USINT':
            packed_bytes = struct.pack("<B", data)
        elif data_type == 'UINT':
            packed_bytes = struct.pack("<H", data)
        elif data_type == 'UDINT':
            packed_bytes = struct.pack("<L", data)
        elif data_type == 'ULINT':
            packed_bytes = struct.pack("<Q", data)
        elif data_type == 'REAL':
            packed_bytes = struct.pack("<f", data)
        elif data_type == 'LREAL':
            packed_bytes = struct.pack("<d", data)
        elif 'STRING' in data_type:
            packed_bytes = data.encode('utf-8')
            length_difference = size - len(packed_bytes)
            packed_bytes += length_difference * b'\x00'
        else:
            pass
        return packed_bytes

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
