"""Tests for BaseHDMIMatrix shared logic (init, properties, validation, parsing, repr).

Uses HDMIMatrix (the concrete sync subclass) to test base class behaviour,
since BaseHDMIMatrix is abstract.
"""

import logging
from unittest.mock import MagicMock

import pytest

from hdmimatrix.hdmimatrix import AsyncHDMIMatrix, HDMIMatrix, CECLogicalAddress, CECCommand

from .conftest import (
    SAMPLE_INPUT_STATUS, SAMPLE_INPUT_STATUS_PARSED,
    SAMPLE_OUTPUT_STATUS, SAMPLE_OUTPUT_STATUS_PARSED,
    SAMPLE_VIDEO_STATUS, SAMPLE_VIDEO_STATUS_PARSED,
    TEST_HOST, TEST_PORT,
)


# --- Initialization ---

class TestInit:

    def test_default_host_and_port(self):
        matrix = HDMIMatrix()
        assert matrix.host == "192.168.0.178"
        assert matrix.port == 4001

    def test_custom_host_and_port(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        assert matrix.host == TEST_HOST
        assert matrix.port == TEST_PORT

    def test_default_input_output_counts(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        assert matrix._input_count == 4
        assert matrix._output_count == 4

    def test_auto_logger_created(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        assert isinstance(matrix.logger, logging.Logger)
        assert "HDMIMatrix" in matrix.logger.name

    def test_auto_logger_has_stream_handler(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        handler_types = [type(h) for h in matrix.logger.handlers]
        assert logging.StreamHandler in handler_types

    def test_auto_logger_level_is_info(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        assert matrix.logger.level == logging.INFO

    def test_custom_logger_used(self):
        custom_logger = logging.getLogger("test.custom")
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT, logger=custom_logger)
        assert matrix.logger is custom_logger

    def test_custom_logger_no_extra_handlers(self):
        custom_logger = logging.getLogger("test.custom.no_handlers")
        handler_count_before = len(custom_logger.handlers)
        HDMIMatrix(TEST_HOST, TEST_PORT, logger=custom_logger)
        assert len(custom_logger.handlers) == handler_count_before

    def test_auto_reconnect_default_true(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        assert matrix.auto_reconnect is True

    def test_auto_reconnect_custom_false(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT, auto_reconnect=False)
        assert matrix.auto_reconnect is False


# --- Properties ---

class TestProperties:

    def test_input_count_returns_4(self, sync_matrix):
        assert sync_matrix.input_count == 4

    def test_output_count_returns_4(self, sync_matrix):
        assert sync_matrix.output_count == 4

    def test_input_count_setter_raises_runtime_error(self, sync_matrix):
        with pytest.raises(RuntimeError, match="read-only"):
            sync_matrix.input_count = 8

    def test_output_count_setter_raises_runtime_error(self, sync_matrix):
        with pytest.raises(RuntimeError, match="read-only"):
            sync_matrix.output_count = 8


# --- Validation ---

class TestValidation:

    def test_valid_1_1(self, sync_matrix):
        sync_matrix._validate_routing_params(1, 1)  # should not raise

    def test_valid_4_4(self, sync_matrix):
        sync_matrix._validate_routing_params(4, 4)  # should not raise

    def test_valid_2_3(self, sync_matrix):
        sync_matrix._validate_routing_params(2, 3)  # should not raise

    def test_input_zero(self, sync_matrix):
        with pytest.raises(ValueError, match="Input must be between 1 and 4"):
            sync_matrix._validate_routing_params(0, 1)

    def test_input_five(self, sync_matrix):
        with pytest.raises(ValueError, match="Input must be between 1 and 4"):
            sync_matrix._validate_routing_params(5, 1)

    def test_input_negative(self, sync_matrix):
        with pytest.raises(ValueError, match="Input must be between 1 and 4"):
            sync_matrix._validate_routing_params(-1, 1)

    def test_output_zero(self, sync_matrix):
        with pytest.raises(ValueError, match="Output must be between 1 and 4"):
            sync_matrix._validate_routing_params(1, 0)

    def test_output_five(self, sync_matrix):
        with pytest.raises(ValueError, match="Output must be between 1 and 4"):
            sync_matrix._validate_routing_params(1, 5)

    def test_output_negative(self, sync_matrix):
        with pytest.raises(ValueError, match="Output must be between 1 and 4"):
            sync_matrix._validate_routing_params(1, -1)

    def test_both_invalid_raises_input_error_first(self, sync_matrix):
        with pytest.raises(ValueError, match="Input"):
            sync_matrix._validate_routing_params(0, 0)


# --- Input status parsing ---

class TestParseInputStatus:

    def test_full_4_inputs(self, sync_matrix):
        result = sync_matrix.parse_input_status(SAMPLE_INPUT_STATUS)
        assert result == SAMPLE_INPUT_STATUS_PARSED

    def test_all_connected(self, sync_matrix):
        result = sync_matrix.parse_input_status("IN 1 2 3 4\nLINK Y Y Y Y")
        assert result == {1: True, 2: True, 3: True, 4: True}

    def test_none_connected(self, sync_matrix):
        result = sync_matrix.parse_input_status("IN 1 2 3 4\nLINK N N N N")
        assert result == {1: False, 2: False, 3: False, 4: False}

    def test_single_input(self, sync_matrix):
        result = sync_matrix.parse_input_status("IN 1\nLINK Y")
        assert result == {1: True}

    def test_empty_string(self, sync_matrix):
        result = sync_matrix.parse_input_status("")
        assert result == {}

    def test_no_link_line(self, sync_matrix):
        result = sync_matrix.parse_input_status("IN 1 2 3 4")
        assert result == {}

    def test_link_without_in_line(self, sync_matrix):
        result = sync_matrix.parse_input_status("LINK Y Y Y Y")
        assert result == {}

    def test_extra_whitespace(self, sync_matrix):
        result = sync_matrix.parse_input_status("IN  1  2  3  4\nLINK  Y  N  Y  N")
        assert result == {1: True, 2: False, 3: True, 4: False}

    def test_carriage_returns(self, sync_matrix):
        result = sync_matrix.parse_input_status("IN 1 2 3 4\r\nLINK N N Y Y")
        assert result == {1: False, 2: False, 3: True, 4: True}

    def test_case_insensitive(self, sync_matrix):
        result = sync_matrix.parse_input_status("in 1 2 3 4\nlink y n y n")
        assert result == {1: True, 2: False, 3: True, 4: False}


# --- Output status parsing ---

class TestParseOutputStatus:

    def test_full_8_outputs(self, sync_matrix):
        result = sync_matrix.parse_output_status(SAMPLE_OUTPUT_STATUS)
        assert result == SAMPLE_OUTPUT_STATUS_PARSED

    def test_all_connected(self, sync_matrix):
        result = sync_matrix.parse_output_status("OUT 1 2 3 4 5 6 7 8\nLINK Y Y Y Y Y Y Y Y")
        assert result == {1: True, 2: True, 3: True, 4: True, 5: True, 6: True, 7: True, 8: True}

    def test_none_connected(self, sync_matrix):
        result = sync_matrix.parse_output_status("OUT 1 2 3 4 5 6 7 8\nLINK N N N N N N N N")
        assert result == {1: False, 2: False, 3: False, 4: False, 5: False, 6: False, 7: False, 8: False}

    def test_empty_string(self, sync_matrix):
        result = sync_matrix.parse_output_status("")
        assert result == {}

    def test_no_link_line(self, sync_matrix):
        result = sync_matrix.parse_output_status("OUT 1 2 3 4 5 6 7 8")
        assert result == {}

    def test_link_without_out_line(self, sync_matrix):
        result = sync_matrix.parse_output_status("LINK Y Y Y Y Y Y Y Y")
        assert result == {}

    def test_carriage_returns(self, sync_matrix):
        result = sync_matrix.parse_output_status("OUT 1 2 3 4 5 6 7 8\r\nLINK Y N N N Y N N N")
        assert result == {1: True, 2: False, 3: False, 4: False, 5: True, 6: False, 7: False, 8: False}

    def test_case_insensitive(self, sync_matrix):
        result = sync_matrix.parse_output_status("out 1 2 3 4 5 6 7 8\nlink y n y n y n y n")
        assert result == {1: True, 2: False, 3: True, 4: False, 5: True, 6: False, 7: True, 8: False}


# --- Video status parsing ---

class TestParseVideoStatus:

    def test_full_4x4(self, sync_matrix):
        result = sync_matrix.parse_video_status(SAMPLE_VIDEO_STATUS)
        assert result == SAMPLE_VIDEO_STATUS_PARSED

    def test_single_line(self, sync_matrix):
        result = sync_matrix.parse_video_status("Output 1 Switch To In 2!")
        assert result == {1: 2}

    def test_empty_string(self, sync_matrix):
        result = sync_matrix.parse_video_status("")
        assert result == {}

    def test_no_matches(self, sync_matrix):
        result = sync_matrix.parse_video_status("No valid data here\nAnother line")
        assert result == {}

    def test_mixed_content(self, sync_matrix):
        data = "Header info\nOutput 1 Switch To In 3!\nSome noise\nOutput 2 Switch To In 1!\n"
        result = sync_matrix.parse_video_status(data)
        assert result == {1: 3, 2: 1}

    def test_extra_whitespace(self, sync_matrix):
        data = "Output   1   Switch   To   In   2!"
        result = sync_matrix.parse_video_status(data)
        assert result == {1: 2}

    def test_carriage_returns(self, sync_matrix):
        data = "Output 1 Switch To In 1!\r\nOutput 2 Switch To In 2!\r\n"
        result = sync_matrix.parse_video_status(data)
        assert result == {1: 1, 2: 2}

    def test_double_digit_numbers(self, sync_matrix):
        data = "Output 10 Switch To In 12!"
        result = sync_matrix.parse_video_status(data)
        assert result == {10: 12}


# --- _build_cec_command ---

class TestBuildCECCommand:

    def test_output_volume_up_with_enums(self, sync_matrix):
        # port=5, src=PLAYBACK_1(4), dst=TV(0) → header=(4<<4)|0=0x40="40"
        result = sync_matrix._build_cec_command(
            "O", 5, CECLogicalAddress.PLAYBACK_1, CECLogicalAddress.TV, CECCommand.DISPLAY_VOLUME_UP
        )
        assert result == b"CECO05404441."

    def test_output_power_on_with_raw_ints(self, sync_matrix):
        # port=3, src=8, dst=0 → header=(8<<4)|0=0x80="80", cmd="04"
        result = sync_matrix._build_cec_command("O", 3, 8, 0, CECCommand.DISPLAY_POWER_ON)
        assert result == b"CECO038004."

    def test_input_source_power_off_with_enums(self, sync_matrix):
        # port=1, src=TV(0), dst=PLAYBACK_1(4) → header=(0<<4)|4=0x04="04", cmd="446C"
        result = sync_matrix._build_cec_command(
            "I", 1, CECLogicalAddress.TV, CECLogicalAddress.PLAYBACK_1, CECCommand.SOURCE_POWER_OFF
        )
        assert result == b"CECI0104446C."

    def test_output_power_off_standalone_opcode(self, sync_matrix):
        # CECCommand.DISPLAY_POWER_OFF = "36" (standalone, no 0x44 prefix)
        # port=1, src=PLAYBACK_1(4), dst=TV(0) → header=0x40="40"
        result = sync_matrix._build_cec_command(
            "O", 1, CECLogicalAddress.PLAYBACK_1, CECLogicalAddress.TV, CECCommand.DISPLAY_POWER_OFF
        )
        assert result == b"CECO014036."

    def test_display_mute_with_enums(self, sync_matrix):
        # port=2, src=PLAYBACK_1(4), dst=TV(0) → header=0x40="40", cmd="4443"
        result = sync_matrix._build_cec_command(
            "O", 2, CECLogicalAddress.PLAYBACK_1, CECLogicalAddress.TV, CECCommand.DISPLAY_MUTE
        )
        assert result == b"CECO02404443."

    def test_port_boundary_1(self, sync_matrix):
        result = sync_matrix._build_cec_command("O", 1, 0, 0, CECCommand.DISPLAY_POWER_ON)
        assert result == b"CECO010004."

    def test_port_boundary_16(self, sync_matrix):
        result = sync_matrix._build_cec_command("O", 16, 0, 0, CECCommand.DISPLAY_POWER_ON)
        assert result == b"CECO160004."

    def test_lowercase_direction_normalized(self, sync_matrix):
        result = sync_matrix._build_cec_command("o", 1, 0, 0, CECCommand.DISPLAY_POWER_ON)
        assert result == b"CECO010004."

    def test_invalid_direction_raises(self, sync_matrix):
        with pytest.raises(ValueError, match="direction"):
            sync_matrix._build_cec_command("X", 1, 0, 0, CECCommand.DISPLAY_POWER_ON)

    def test_port_zero_raises(self, sync_matrix):
        with pytest.raises(ValueError, match="port"):
            sync_matrix._build_cec_command("O", 0, 0, 0, CECCommand.DISPLAY_POWER_ON)

    def test_port_17_raises(self, sync_matrix):
        with pytest.raises(ValueError, match="port"):
            sync_matrix._build_cec_command("O", 17, 0, 0, CECCommand.DISPLAY_POWER_ON)

    def test_src_addr_out_of_range_raises(self, sync_matrix):
        with pytest.raises(ValueError, match="src_addr"):
            sync_matrix._build_cec_command("O", 1, 16, 0, CECCommand.DISPLAY_POWER_ON)

    def test_dst_addr_out_of_range_raises(self, sync_matrix):
        with pytest.raises(ValueError, match="dst_addr"):
            sync_matrix._build_cec_command("O", 1, 0, 16, CECCommand.DISPLAY_POWER_ON)

    def test_raw_string_command(self, sync_matrix):
        # Allow passing a raw hex string instead of enum
        # port=1, src=4, dst=0 → header=0x40="40", cmd="4441"
        result = sync_matrix._build_cec_command("O", 1, 4, 0, "4441")
        assert result == b"CECO01404441."


# --- Repr ---

class TestRepr:

    def test_sync_disconnected(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        assert repr(matrix) == f"HDMIMatrix({TEST_HOST}:{TEST_PORT}, connected=False)"

    def test_sync_connected(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        matrix.connection = MagicMock()  # simulate connected state
        assert repr(matrix) == f"HDMIMatrix({TEST_HOST}:{TEST_PORT}, connected=True)"

    def test_async_disconnected(self):
        matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)
        assert repr(matrix) == f"AsyncHDMIMatrix({TEST_HOST}:{TEST_PORT}, connected=False)"

    def test_async_connected(self):
        matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        matrix.writer = mock_writer
        assert repr(matrix) == f"AsyncHDMIMatrix({TEST_HOST}:{TEST_PORT}, connected=True)"
