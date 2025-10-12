import socket
import asyncio
import logging
import time
from enum import Enum
from typing import Optional
from abc import ABC, abstractmethod


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
    STATUS_VIDEO = "STA_VIDEO."
    STATUS_PHDBT = "STA_PHDBT."
    STATUS_INPUT = "STA_IN."
    STATUS_OUTPUT = "STA_OUT."
    STATUS_HDCP = "STA_HDCP."
    STATUS_DOWNSCALING = "STA_DS."
    ROUTE_OUTPUT = "OUT{:02d}:{:02d}."
    OUTPUT_ON = "@OUT{:02d}."
    OUTPUT_OFF = "$OUT{:02d}."


class BaseHDMIMatrix(ABC):
    """Base class for HDMI Matrix controllers with shared functionality"""

    def __init__(self, host: str = "192.168.0.178", port: int = 4001,
                  logger: Optional[logging.Logger] = None):
        """
        Initialize the matrix switch controller

        Args:
            host: IP address for TCP connection (default 192.168.0.178)
            port: TCP port (default 4001)
            logger: Optional logger instance
        """
        self.host = host
        self.port = port

        # TODO - make this be configurable based on the matrix type
        # eg 4x4 or 8x8
        self._input_count = 4
        self._output_count = 4

        # Initialise logging if logger is not passed in.
        if logger is None:
            self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            self.logger.setLevel('INFO')

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
    def input_count(self, value: int):
        raise RuntimeError(f"input_count is read-only — attempted to set it to {value}")

    @property
    def output_count(self):
        return self._output_count
    
    @output_count.setter
    def output_count(self, value: int):
        raise RuntimeError(f"output_count is read-only — attempted to set it to {value}")

    def _validate_routing_params(self, input: int, output: int):
        """Validate input and output parameters for routing"""
        if not 1 <= input <= self.input_count:
            raise ValueError(f"Input must be between 1 and {self.input_count}")
        
        if not 1 <= output <= self.output_count:
            raise ValueError(f"Output must be between 1 and {self.output_count}")

    def parse_video_status(self, status_response: str) -> dict:
        """
        Parse video status response into a routing dictionary
        
        Args:
            status_response: Raw response from get_video_status()
            
        Returns:
            dict: Mapping of output number to input number
            
        Example:
            {1: 1, 2: 2, 3: 1, 4: 1}  # output_number: input_number
        """
        import re
        
        routing = {}
        
        # Parse each line of the response
        for line in status_response.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Match pattern: "Output XX Switch To In YY!"
            match = re.search(r'Output\s+(\d+)\s+Switch\s+To\s+In\s+(\d+)!', line)
            if match:
                output_num = int(match.group(1))
                input_num = int(match.group(2))
                routing[output_num] = input_num
        
        return routing

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active"""
        pass


class HDMIMatrix(BaseHDMIMatrix):
    """Synchronous controller for AVGear (and possibly other) HDMI Matrix switches"""

    def __init__(self, host: str = "192.168.0.178", port: int = 4001,
                  logger: Optional[logging.Logger] = None):
        super().__init__(host, port, logger)
        self.connection: Optional[socket.socket] = None

    @property
    def is_connected(self) -> bool:
        """Check if synchronous connection is active"""
        return self.connection is not None

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
    def get_device_name(self) -> str:
        return self._process_request(Commands.NAME.value.encode('ascii'))

    def get_device_status(self) -> str:
        return self._process_request(Commands.STATUS.value.encode('ascii'))

    def get_device_type(self) -> str:
        return self._process_request(Commands.TYPE.value.encode('ascii'))

    def get_device_version(self) -> str:
        return self._process_request(Commands.VERSION.value.encode('ascii'))

    def get_video_status(self) -> str:
        return self._process_request(Commands.STATUS_VIDEO.value.encode('ascii'))

    def get_video_status_parsed(self) -> dict:
        """Get video status and return parsed routing dictionary"""
        status = self.get_video_status()
        return self.parse_video_status(status)

    def get_hdbt_power_status(self) -> str:
        """Get HDBT power status"""
        return self._process_request(Commands.STATUS_PHDBT.value.encode('ascii'))

    def get_input_status(self) -> str:
        """Get connection status of all HDMI input ports"""
        return self._process_request(Commands.STATUS_INPUT.value.encode('ascii'))

    def get_output_status(self) -> str:
        """Get connection status of all HDMI output ports"""
        return self._process_request(Commands.STATUS_OUTPUT.value.encode('ascii'))

    def get_hdcp_status(self) -> str:
        """Get HDCP status information"""
        return self._process_request(Commands.STATUS_HDCP.value.encode('ascii'))

    def get_downscaling_status(self) -> str:
        """Get downscaling status of each output"""
        return self._process_request(Commands.STATUS_DOWNSCALING.value.encode('ascii'))

    # Command Methods
    def power_off(self) -> str:
        """Power off the HDMI matrix"""
        return self._process_request(Commands.POWEROFF.value.encode('ascii'))

    def power_on(self) -> str:
        """Power On the HDMI matrix"""
        return self._process_request(Commands.POWERON.value.encode('ascii'))

    def route_input_to_output(self, input: int, output: int) -> str:
        """Select HDMI input to route to HDMI output"""
        self._validate_routing_params(input, output)
        return self._process_request(Commands.ROUTE_OUTPUT.value.format(output, input).encode('ascii'))

    def output_on(self, output: int) -> str:
        """Turn on specific HDMI output"""
        if not 1 <= output <= self.output_count:
            raise ValueError(f"Output must be between 1 and {self.output_count}")
        return self._process_request(Commands.OUTPUT_ON.value.format(output).encode('ascii'))

    def output_off(self, output: int) -> str:
        """Turn off specific HDMI output"""
        if not 1 <= output <= self.output_count:
            raise ValueError(f"Output must be between 1 and {self.output_count}")
        return self._process_request(Commands.OUTPUT_OFF.value.format(output).encode('ascii'))

    # Internal methods
    def _process_request(self, request: bytes) -> str:
        if not self.connection:
            raise RuntimeError("Not connected. Call connect() first.")

        # Send the command
        self.connection.send(request)
        self.logger.debug(f'Send Command: {request}')        

        # Read all the responses back
        response = self._read_response()
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

    # Context manager support
    def __enter__(self):
        """Synchronous context manager entry"""
        if not self.connect():
            raise RuntimeError("Failed to connect")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Synchronous context manager exit"""
        self.disconnect()


class AsyncHDMIMatrix(BaseHDMIMatrix):
    """Asynchronous controller for AVGear (and possibly other) HDMI Matrix switches"""

    def __init__(self, host: str = "192.168.0.178", port: int = 4001,
                  logger: Optional[logging.Logger] = None):
        super().__init__(host, port, logger)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._connection_lock: Optional[asyncio.Lock] = None

    @property
    def is_connected(self) -> bool:
        """Check if async connection is active"""
        return self.writer is not None and not self.writer.is_closing()

    # Connection methods
    async def connect(self) -> bool:
        """Establish async TCP/IP connection to the matrix switch"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self._connection_lock = asyncio.Lock()
            self.logger.info(f"Async connected to {self.host}:{self.port}")

            # Read any welcome data to clear the buffer
            try:
                data = await asyncio.wait_for(
                    self.reader.read(SOCKET_RECV_BUFFER), 
                    timeout=1.0
                )
                self.logger.debug(f"Discarding: {data}")
            except asyncio.TimeoutError:
                # No welcome data, that's fine
                pass

            return True

        except Exception as e:
            self.logger.error(f"Async connection failed: {e}")
            return False

    async def disconnect(self):
        """Close the async connection"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
            self.reader = None
            self._connection_lock = None
            self.logger.info("Async disconnected")

    # Information Methods
    async def get_device_name(self) -> str:
        return await self._process_request(Commands.NAME.value.encode('ascii'))

    async def get_device_status(self) -> str:
        return await self._process_request(Commands.STATUS.value.encode('ascii'))

    async def get_device_type(self) -> str:
        return await self._process_request(Commands.TYPE.value.encode('ascii'))

    async def get_device_version(self) -> str:
        return await self._process_request(Commands.VERSION.value.encode('ascii'))

    async def get_video_status(self) -> str:
        return await self._process_request(Commands.STATUS_VIDEO.value.encode('ascii'))

    async def get_video_status_parsed(self) -> dict:
        """Get video status and return parsed routing dictionary"""
        status = await self.get_video_status()
        return self.parse_video_status(status)

    async def get_hdbt_power_status(self) -> str:
        """Get HDBT power status"""
        return await self._process_request(Commands.STATUS_PHDBT.value.encode('ascii'))

    async def get_input_status(self) -> str:
        """Get connection status of all HDMI input ports"""
        return await self._process_request(Commands.STATUS_INPUT.value.encode('ascii'))

    async def get_output_status(self) -> str:
        """Get connection status of all HDMI output ports"""
        return await self._process_request(Commands.STATUS_OUTPUT.value.encode('ascii'))

    async def get_hdcp_status(self) -> str:
        """Get HDCP status information"""
        return await self._process_request(Commands.STATUS_HDCP.value.encode('ascii'))

    async def get_downscaling_status(self) -> str:
        """Get downscaling status of each output"""
        return await self._process_request(Commands.STATUS_DOWNSCALING.value.encode('ascii'))

    # Command Methods
    async def power_off(self) -> str:
        """Power off the HDMI matrix"""
        return await self._process_request(Commands.POWEROFF.value.encode('ascii'))

    async def power_on(self) -> str:
        """Power On the HDMI matrix"""
        return await self._process_request(Commands.POWERON.value.encode('ascii'))

    async def route_input_to_output(self, input: int, output: int) -> str:
        """Select HDMI input to route to HDMI output"""
        self._validate_routing_params(input, output)
        return await self._process_request(Commands.ROUTE_OUTPUT.value.format(output, input).encode('ascii'))

    async def output_on(self, output: int) -> str:
        """Turn on specific HDMI output"""
        if not 1 <= output <= self.output_count:
            raise ValueError(f"Output must be between 1 and {self.output_count}")
        return await self._process_request(Commands.OUTPUT_ON.value.format(output).encode('ascii'))

    async def output_off(self, output: int) -> str:
        """Turn off specific HDMI output"""
        if not 1 <= output <= self.output_count:
            raise ValueError(f"Output must be between 1 and {self.output_count}")
        return await self._process_request(Commands.OUTPUT_OFF.value.format(output).encode('ascii'))

    # Internal methods
    async def _process_request(self, request: bytes) -> str:
        if not self.writer or not self.reader or not self._connection_lock:
            raise RuntimeError("Not connected. Call connect() first.")

        # Use lock to ensure only one request at a time
        async with self._connection_lock:
            # Send the command
            self.writer.write(request)
            await self.writer.drain()
            self.logger.debug(f'Send Command: {request}')        

            # Read all the responses back
            response = await self._read_response()
            return response

    async def _read_response(self, timeout: float = 2.0) -> str:
        """
        Read all available response data from the device asynchronously
        
        Args:
            timeout: Total timeout in seconds
            
        Returns:
            str: Complete response string or empty string if no response
        """
        if not self.reader:
            return ""
            
        try:
            response_parts = []
            start_time = asyncio.get_event_loop().time()
            last_data_time = start_time
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    # Try to read data with a short timeout
                    data = await asyncio.wait_for(
                        self.reader.read(SOCKET_RECV_BUFFER), 
                        timeout=0.1
                    )
                    
                    if data:
                        response_parts.append(data.decode('ascii', errors='ignore'))
                        last_data_time = asyncio.get_event_loop().time()
                        self.logger.debug(f"Received data chunk: {repr(data)}")
                    else:
                        # Connection closed
                        break
                        
                except asyncio.TimeoutError:
                    # No data available right now
                    if response_parts and (asyncio.get_event_loop().time() - last_data_time) > SOCKET_END_OF_DATA_TIMEOUT:
                        # We got some data but nothing new for 0.5 seconds
                        break
                    await asyncio.sleep(SOCKET_RECEIVE_DELAY)  # Small delay before next attempt
                    continue
                    
                except Exception as e:
                    self.logger.error(f"Error during async read: {e}")
                    break
            
            complete_response = ''.join(response_parts).strip()
            if complete_response:
                self.logger.debug(f"Complete response: {repr(complete_response)}")
                return complete_response
            else:
                self.logger.debug("No response received")
                return ""
                
        except Exception as e:
            self.logger.error(f"Error reading async response: {e}")
            return ""

    # Async context manager support
    async def __aenter__(self):
        """Async context manager entry"""
        if not await self.connect():
            raise RuntimeError("Failed to connect")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


# Example usage:
async def example_async_usage():
    """Example of how to use the AsyncHDMIMatrix class"""
    matrix = AsyncHDMIMatrix("192.168.0.178", 4001)
    
    # Using async context manager
    async with matrix:
        # Get device information
        name = await matrix.get_device_name()
        print(f"Device name: {name}")
        
        status = await matrix.get_device_status()
        print(f"Status: {status}")
        
        # Route input 1 to output 1
        result = await matrix.route_input_to_output(1, 1)
        print(f"Route result: {result}")

def example_sync_usage():
    """Example of how to use the original HDMIMatrix class"""
    matrix = HDMIMatrix("192.168.0.178", 4001)
    
    # Using sync context manager
    with matrix:
        # Get device information
        name = matrix.get_device_name()
        print(f"Device name: {name}")
        
        status = matrix.get_device_status()
        print(f"Status: {status}")
        
        # Route input 1 to output 1
        result = matrix.route_input_to_output(1, 1)
        print(f"Route result: {result}")

async def example_concurrent_operations():
    """Example showing that async operations are serialized due to TCP connection constraints"""
    matrix = AsyncHDMIMatrix("192.168.0.178", 4001)
    
    async with matrix:
        # These operations will be serialized due to the connection lock
        # but they're still async and won't block the event loop
        tasks = [
            matrix.get_device_name(),
            matrix.get_device_status(),
            matrix.get_device_type(),
            matrix.get_device_version()
        ]
        
        results = await asyncio.gather(*tasks)
        print("Results (executed serially due to TCP constraint):", results)
        
        # Sequential routing operations
        await matrix.route_input_to_output(1, 1)
        await matrix.route_input_to_output(2, 2)

async def example_video_status_parsing():
    """Example showing how to use the video status parsing"""
    matrix = AsyncHDMIMatrix("192.168.0.178", 4001)
    
    async with matrix:
        # Get raw video status
        raw_status = await matrix.get_video_status()
        print(f"Raw status:\n{raw_status}")
        
        # Get parsed video status
        routing = await matrix.get_video_status_parsed()
        print(f"\nParsed routing: {routing}")
        
        # Show which input is connected to each output
        print("\nCurrent routing:")
        for output, input_num in sorted(routing.items()):
            print(f"  Output {output} <- Input {input_num}")

if __name__ == "__main__":
    # Run sync example
    print("Running synchronous example:")
    example_sync_usage()
    
    # Run async examples
    print("\nRunning asynchronous example:")
    asyncio.run(example_async_usage())
    
    print("\nRunning concurrent operations example:")
    asyncio.run(example_concurrent_operations())
    
    print("\nRunning video status parsing example:")
    asyncio.run(example_video_status_parsing())