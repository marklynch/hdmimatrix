"""Tests for BaseHDMIMatrix shared logic (init, properties, validation, parsing, repr).

Uses HDMIMatrix (the concrete sync subclass) to test base class behaviour,
since BaseHDMIMatrix is abstract.
"""

import logging
from unittest.mock import MagicMock

import pytest

from hdmimatrix.hdmimatrix import AsyncHDMIMatrix, HDMIMatrix

from .conftest import SAMPLE_VIDEO_STATUS, SAMPLE_VIDEO_STATUS_PARSED, TEST_HOST, TEST_PORT


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
