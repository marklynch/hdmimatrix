import socket
import logging
import time
from enum import Enum


SOCKET_RECV_BUFFER = 2048 # size of socket recieve buffer
SOCKET_TIMEOUT = 5.0
SOCKET_END_OF_DATA_TIMEOUT = 0.5 # if no data recieved assume end of message
SOCKET_RECEIVE_DELAY = 0.05 # delay between recieves

class Commands(Enum):
    POWERON = "PowerON."
    POWEROFF = "PowerOFF."
    NAME = "/*Name."
    TYPE = "/*Type."
    VERSION = "/^Version."
    STATUS = "STA."

class HDMIMatrix:
    """Controller for AVGear (and possibly other) HDMI Matrix switches"""

    def __init__(self, host: str = "192.168.0.178", port: int = 4001,
                  logger: logging.Logger = None):
        """
        Initialize the matrix switch controller

        Args:
            host: IP address for TCP connection (default 192.168.0.178)
            port: TCP port (default 4001)
        """
        self.host = host
        self.port = port
        self.connection = None

        # TODO - make this be configurable based on the matrix type
        # eg 4x4 or 8x8
        self._input_count = 4
        self._output_count = 4

        # Initialise logging if logger is not passed in.
        if logger is None:
            self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            self.logger.setLevel('DEBUG')

            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        else:
            self.logger = logger

    @property
    def input_count(self):
        return self._input_count

    @input_count.setter
    def input_count(self, value:int):
        raise RuntimeError(f"input_count is read-only — attempted to set it to {value}")

    @property
    def output_count(self):
        return self._output_count
    @output_count.setter
    def output_count(self, value:int):
        raise RuntimeError(f"output_count is read-only — attempted to set it to {value}")


    # Connection methods
    def connect(self) -> bool:
        """Establish TCP/IP connection to the matrix switch"""
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(SOCKET_TIMEOUT)
            self.connection.connect((self.host, self.port))
            self.logger.info(f"Connected to {self.host}:{self.port}")

            # Read any data the welcome data to clear the buffer
            data = self.connection.recv(SOCKET_RECV_BUFFER)
            self.logger.debug(f"Discarding: {data}")

            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Close the connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Disconnected")


    # Information Methods

    def get_device_name(self):
        return self._process_request(Commands.NAME.value.encode('ascii'))

    def get_device_status(self):
        return self._process_request(Commands.STATUS.value.encode('ascii'))

    def get_device_type(self):
        return self._process_request(Commands.TYPE.value.encode('ascii'))

    def get_device_version(self):
        return self._process_request(Commands.VERSION.value.encode('ascii'))

    # Command Methods

    def power_off(self):
        """
        Power off the HDMI matrix
        """
        return self._process_request(Commands.POWEROFF.value.encode('ascii'))

    def power_on(self):
        """
        Power On the HDMI matrix
        """
        return self._process_request(Commands.POWERON.value.encode('ascii'))

    def route_input_to_output(self, input:int, output:int):
        """
        Select HDMI input to route to HDMI output
        """
        if not 0 <= input <= self.input_count:
            raise ValueError(f"Input must be between 1 and {self.input_count}")
        
        if not 0 <= output <= self.output_count:
            raise ValueError(f"Output must be between 1 and {self.output_count}")

        return self._process_request(f"OUT{output:02d}:{input:02d}.".encode('ascii'))


    # Internal methods
    def _process_request(self, request: bytes):

        # Send the command
        self.connection.send(request)
        self.logger.debug(f'Send Command: {request}')        

        # Read all the responses back
        response = self._read_response()

        # self.logger.debug(response)
        return response
    

    def _read_response(self, timeout: float = 2.0) -> str:
        """
        Read all available response data from the device - this uses a timeout
        based method as there is no protocol format and output can be multiple
        lines.
        
        Args:
            timeout: Total timeout in seconds
            
        Returns:
            str: Complete response string or empty string if no response
        """

        if not self.connection:
            return ""
            
        try:
            # Set socket to non-blocking mode temporarily
            original_timeout = self.connection.gettimeout()
            self.connection.settimeout(0.1)  # Short timeout for individual reads
            
            response_parts = []
            start_time = time.time()
            last_data_time = start_time
            
            while (time.time() - start_time) < timeout:
                try:
                    # Try to read data
                    data = self.connection.recv(SOCKET_RECV_BUFFER)
                    if data:
                        response_parts.append(data.decode('ascii', errors='ignore'))
                        last_data_time = time.time()
                        self.logger.debug(f"Received data chunk: {repr(data)}")
                    else:
                        # No data received, check if we should continue waiting
                        if response_parts and (time.time() - last_data_time) > SOCKET_END_OF_DATA_TIMEOUT:
                            # We got some data but nothing new for 0.5 seconds
                            break
                        time.sleep(SOCKET_RECEIVE_DELAY)  # Small delay before next attempt
                        
                except socket.timeout:
                    # No data available right now
                    if response_parts and (time.time() - last_data_time) > SOCKET_END_OF_DATA_TIMEOUT:
                        # We got some data but nothing new for 0.5 seconds
                        break
                    time.sleep(SOCKET_RECEIVE_DELAY)  # Small delay before next attempt
                    continue
                    
                except Exception as e:
                    self.logger.error(f"Error during read: {e}")
                    break
            
            # Restore original timeout
            self.connection.settimeout(original_timeout)
            
            complete_response = ''.join(response_parts).strip()
            if complete_response:
                self.logger.debug(f"Complete response: {repr(complete_response)}")
                return complete_response
            else:
                self.logger.debug("No response received")
                return ""
                
        except Exception as e:
            self.logger.error(f"Error reading response: {e}")
            return ""