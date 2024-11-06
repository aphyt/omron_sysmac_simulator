import ctypes


class SimulatorVariable:
    def __init__(self, revision: str, address: str, size: int):
        self.revision = revision
        self.address = address
        self.size = size


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

    def read_variable(self, variable_name: str):
        if variable_name not in self.variable_dictionary:
            self.variable_dictionary[variable_name] = self.get_variable_info(variable_name)
        variable_info = self.variable_dictionary[variable_name]
        command = f'AsyncReadMemText {variable_info.revision} 1 {variable_info.address},2'
        response = self.send_command(command)[0][0]
        return response

    def write_variable(self, variable_name: str, value):
        pass

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
