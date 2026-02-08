"""Tests for the Commands enum and module-level constants."""

import pytest

from hdmimatrix.hdmimatrix import (
    Commands,
    SOCKET_RECV_BUFFER,
    SOCKET_TIMEOUT,
    SOCKET_END_OF_DATA_TIMEOUT,
    SOCKET_RECEIVE_DELAY,
)


# --- Constants ---

class TestConstants:

    def test_socket_recv_buffer(self):
        assert SOCKET_RECV_BUFFER == 2048

    def test_socket_timeout(self):
        assert SOCKET_TIMEOUT == 5.0

    def test_socket_end_of_data_timeout(self):
        assert SOCKET_END_OF_DATA_TIMEOUT == 0.5

    def test_socket_receive_delay(self):
        assert SOCKET_RECEIVE_DELAY == 0.05


# --- Commands enum values ---

class TestCommandsValues:

    def test_poweron(self):
        assert Commands.POWERON.value == "PowerON."

    def test_poweroff(self):
        assert Commands.POWEROFF.value == "PowerOFF."

    def test_name(self):
        assert Commands.NAME.value == "/*Name."

    def test_type(self):
        assert Commands.TYPE.value == "/*Type."

    def test_version(self):
        assert Commands.VERSION.value == "/^Version."

    def test_status(self):
        assert Commands.STATUS.value == "STA."

    def test_status_video(self):
        assert Commands.STATUS_VIDEO.value == "STA_VIDEO."

    def test_status_phdbt(self):
        assert Commands.STATUS_PHDBT.value == "STA_PHDBT."

    def test_status_input(self):
        assert Commands.STATUS_INPUT.value == "STA_IN."

    def test_status_output(self):
        assert Commands.STATUS_OUTPUT.value == "STA_OUT."

    def test_status_hdcp(self):
        assert Commands.STATUS_HDCP.value == "STA_HDCP."

    def test_status_downscaling(self):
        assert Commands.STATUS_DOWNSCALING.value == "STA_DS."

    def test_route_output_format_string(self):
        assert Commands.ROUTE_OUTPUT.value == "OUT{:02d}:{:02d}."

    def test_output_on_format_string(self):
        assert Commands.OUTPUT_ON.value == "@OUT{:02d}."

    def test_output_off_format_string(self):
        assert Commands.OUTPUT_OFF.value == "$OUT{:02d}."


# --- Commands formatting ---

class TestCommandsFormatting:

    def test_route_output_format(self):
        assert Commands.ROUTE_OUTPUT.value.format(1, 3) == "OUT01:03."

    def test_route_output_format_double_digit(self):
        assert Commands.ROUTE_OUTPUT.value.format(12, 8) == "OUT12:08."

    def test_output_on_format(self):
        assert Commands.OUTPUT_ON.value.format(2) == "@OUT02."

    def test_output_off_format(self):
        assert Commands.OUTPUT_OFF.value.format(4) == "$OUT04."


# --- Commands enum properties ---

class TestCommandsEnumProperties:

    def test_member_count(self):
        assert len(Commands) == 15

    def test_all_values_are_strings(self):
        for cmd in Commands:
            assert isinstance(cmd.value, str), f"{cmd.name} value is not a string"

    def test_all_values_end_with_period(self):
        for cmd in Commands:
            assert cmd.value.endswith("."), f"{cmd.name} value does not end with '.'"

    def test_all_values_encode_to_ascii(self):
        for cmd in Commands:
            # Should not raise UnicodeEncodeError
            cmd.value.encode("ascii")
