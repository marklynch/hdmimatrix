import socket
import asyncio
import logging
import time
from enum import Enum
from typing import Optional
from abc import ABC, abstractmethod


__all__ = ["HDMIMatrix", "AsyncHDMIMatrix", "Commands"]

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
                  logger: Optional[logging.Logger] = None,
                  auto_reconnect: bool = True):
        """
        Initialize the matrix switch controller

        Args:
            host: IP address for TCP connection (default 192.168.0.178)
            port: TCP port (default 4001)
            logger: Optional logger instance
            auto_reconnect: Automatically reconnect and retry on connection
                loss (default True)
        """
        self.host = host
        self.port = port
        self.auto_reconnect = auto_reconnect

        # TODO - make this be configurable based on the matrix type
        # eg 4x4 or 8x8
        self._input_count = 4
        self._output_count = 4

        # Initialise logging if logger is not passed in.
        if logger is None:
            self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            self.logger.setLevel(logging.INFO)

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
    def input_count(self) -> int:
        """Number of HDMI input ports on the matrix (read-only)."""
        return self._input_count

    @input_count.setter
    def input_count(self, value: int):
        raise RuntimeError(f"input_count is read-only — attempted to set it to {value}")

    @property
    def output_count(self) -> int:
        """Number of HDMI output ports on the matrix (read-only)."""
        return self._output_count

    @output_count.setter
    def output_count(self, value: int):
        raise RuntimeError(f"output_count is read-only — attempted to set it to {value}")

    # Declarative mapping: method name -> (docstring, Commands member).
    # __init_subclass__ auto-generates sync or async wrappers for each entry.
    _SIMPLE_COMMANDS = {
        "get_device_name":        ("Query the device name configured on the matrix.", Commands.NAME),
        "get_device_status":      ("Query the overall device status.", Commands.STATUS),
        "get_device_type":        ("Query the device model/type identifier.", Commands.TYPE),
        "get_device_version":     ("Query the firmware version of the device.", Commands.VERSION),
        "get_video_status":       ("Query the raw video routing status string.", Commands.STATUS_VIDEO),
        "get_hdbt_power_status":  ("Get HDBT power status.", Commands.STATUS_PHDBT),
        "get_input_status":       ("Get connection status of all HDMI input ports.", Commands.STATUS_INPUT),
        "get_output_status":      ("Get connection status of all HDMI output ports.", Commands.STATUS_OUTPUT),
        "get_hdcp_status":        ("Get HDCP status information.", Commands.STATUS_HDCP),
        "get_downscaling_status": ("Get downscaling status of each output.", Commands.STATUS_DOWNSCALING),
        "power_on":               ("Power on the HDMI matrix.", Commands.POWERON),
        "power_off":              ("Power off the HDMI matrix.", Commands.POWEROFF),
    }

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        is_async = asyncio.iscoroutinefunction(cls.__dict__.get("_process_request"))
        for name, (doc, cmd) in BaseHDMIMatrix._SIMPLE_COMMANDS.items():
            if name not in cls.__dict__:
                cmd_bytes = cmd.value.encode("ascii")
                if is_async:
                    async def method(self, _cmd=cmd_bytes):
                        return await self._process_request(_cmd)
                else:
                    def method(self, _cmd=cmd_bytes):
                        return self._process_request(_cmd)
                method.__name__ = name
                method.__qualname__ = f"{cls.__qualname__}.{name}"
                method.__doc__ = doc
                method.__annotations__ = {"return": str}
                setattr(cls, name, method)

    def _validate_routing_params(self, input: int, output: int):
        """Validate input and output parameters for routing"""
        if not 1 <= input <= self.input_count:
            raise ValueError(f"Input must be between 1 and {self.input_count}")

        if not 1 <= output <= self.output_count:
            raise ValueError(f"Output must be between 1 and {self.output_count}")

    def _build_route_command(self, input: int, output: int) -> bytes:
        """Validate routing params and build the route command bytes."""
        self._validate_routing_params(input, output)
        return Commands.ROUTE_OUTPUT.value.format(output, input).encode("ascii")

    def _build_output_on_command(self, output: int) -> bytes:
        """Validate output param and build the output-on command bytes."""
        if not 1 <= output <= self.output_count:
            raise ValueError(f"Output must be between 1 and {self.output_count}")
        return Commands.OUTPUT_ON.value.format(output).encode("ascii")

    def _build_output_off_command(self, output: int) -> bytes:
        """Validate output param and build the output-off command bytes."""
        if not 1 <= output <= self.output_count:
            raise ValueError(f"Output must be between 1 and {self.output_count}")
        return Commands.OUTPUT_OFF.value.format(output).encode("ascii")

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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.host}:{self.port}, connected={self.is_connected})"


    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active"""
        pass


class HDMIMatrix(BaseHDMIMatrix):
    """Synchronous controller for AVGear (and possibly other) HDMI Matrix switches"""

    def __init__(self, host: str = "192.168.0.178", port: int = 4001,
                  logger: Optional[logging.Logger] = None,
                  auto_reconnect: bool = True):
        super().__init__(host, port, logger, auto_reconnect)
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
            if self.connection:
                self.connection.close()
                self.connection = None
            return False

    def disconnect(self):
        """Close the connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Disconnected")

    # Simple command methods (get_device_name, power_on, etc.) are
    # auto-generated by BaseHDMIMatrix.__init_subclass__.

    def get_video_status_parsed(self) -> dict:
        """Get video status and return parsed routing dictionary."""
        return self.parse_video_status(self.get_video_status())

    def route_input_to_output(self, input: int, output: int) -> str:
        return self._process_request(self._build_route_command(input, output))

    def output_on(self, output: int) -> str:
        """Enable a specific HDMI output port.

        Args:
            output: Output port number (1 to output_count).

        Raises:
            ValueError: If output is out of range.
        """
        return self._process_request(self._build_output_on_command(output))

    def output_off(self, output: int) -> str:
        """Disable a specific HDMI output port.

        Args:
            output: Output port number (1 to output_count).

        Raises:
            ValueError: If output is out of range.
        """
        return self._process_request(self._build_output_off_command(output))

    # Internal methods
    def _process_request(self, request: bytes) -> str:
        if not self.is_connected:
            if self.auto_reconnect:
                self.logger.info("Not connected, attempting auto-reconnect...")
                if not self.connect():
                    raise RuntimeError("Not connected and auto-reconnect failed.")
            else:
                raise RuntimeError("Not connected. Call connect() first.")

        try:
            self.connection.send(request)
            self.logger.debug(f'Send Command: {request}')
            return self._read_response()
        except (OSError, socket.timeout) as e:
            self.logger.warning(f"Connection error during request: {e}")
            self.disconnect()
            if self.auto_reconnect:
                self.logger.info("Attempting auto-reconnect...")
                if self.connect():
                    self.logger.info("Reconnected, retrying request...")
                    self.connection.send(request)
                    self.logger.debug(f'Send Command (retry): {request}')
                    return self._read_response()
            raise RuntimeError(f"Connection lost during request: {e}") from e

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
                  logger: Optional[logging.Logger] = None,
                  auto_reconnect: bool = True):
        super().__init__(host, port, logger, auto_reconnect)
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

    # Simple command methods (get_device_name, power_on, etc.) are
    # auto-generated by BaseHDMIMatrix.__init_subclass__.

    async def get_video_status_parsed(self) -> dict:
        """Get video status and return parsed routing dictionary."""
        return self.parse_video_status(await self.get_video_status())

    async def route_input_to_output(self, input: int, output: int) -> str:
        """Route an HDMI input to an HDMI output.

        Args:
            input: Input port number (1 to input_count).
            output: Output port number (1 to output_count).

        Raises:
            ValueError: If input or output is out of range.
        """
        return await self._process_request(self._build_route_command(input, output))

    async def output_on(self, output: int) -> str:
        """Enable a specific HDMI output port.

        Args:
            output: Output port number (1 to output_count).

        Raises:
            ValueError: If output is out of range.
        """
        return await self._process_request(self._build_output_on_command(output))

    async def output_off(self, output: int) -> str:
        """Disable a specific HDMI output port.

        Args:
            output: Output port number (1 to output_count).

        Raises:
            ValueError: If output is out of range.
        """
        return await self._process_request(self._build_output_off_command(output))

    # Internal methods
    async def _process_request(self, request: bytes) -> str:
        if not self.is_connected:
            if self.auto_reconnect:
                self.logger.info("Not connected, attempting auto-reconnect...")
                if not await self.connect():
                    raise RuntimeError("Not connected and auto-reconnect failed.")
            else:
                raise RuntimeError("Not connected. Call connect() first.")

        if not self._connection_lock:
            raise RuntimeError("Not connected. Call connect() first.")

        async with self._connection_lock:
            try:
                self.writer.write(request)
                await self.writer.drain()
                self.logger.debug(f'Send Command: {request}')
                return await self._read_response()
            except (OSError, asyncio.TimeoutError) as e:
                self.logger.warning(f"Connection error during request: {e}")
                await self.disconnect()
                if self.auto_reconnect:
                    self.logger.info("Attempting auto-reconnect...")
                    if await self.connect():
                        self.logger.info("Reconnected, retrying request...")
                        self.writer.write(request)
                        await self.writer.drain()
                        self.logger.debug(f'Send Command (retry): {request}')
                        return await self._read_response()
                raise RuntimeError(f"Connection lost during request: {e}") from e

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
