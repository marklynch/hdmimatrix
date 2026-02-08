"""Tests for HDMIMatrix (synchronous socket-based implementation)."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from hdmimatrix.hdmimatrix import Commands, HDMIMatrix, SOCKET_RECV_BUFFER, SOCKET_TIMEOUT

from .conftest import TEST_HOST, TEST_PORT, WELCOME_DATA, make_recv_side_effect


# --- Connection ---

class TestConnection:

    def test_connect_success(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        mock_sock = MagicMock()
        mock_sock.recv.return_value = WELCOME_DATA

        with patch("hdmimatrix.hdmimatrix.socket.socket", return_value=mock_sock):
            result = matrix.connect()

        assert result is True
        assert matrix.is_connected
        mock_sock.connect.assert_called_once_with((TEST_HOST, TEST_PORT))
        mock_sock.settimeout.assert_called_with(SOCKET_TIMEOUT)
        mock_sock.recv.assert_called_once_with(SOCKET_RECV_BUFFER)
        matrix.disconnect()

    def test_connect_failure_connection_refused(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = ConnectionRefusedError("Connection refused")

        with patch("hdmimatrix.hdmimatrix.socket.socket", return_value=mock_sock):
            result = matrix.connect()

        assert result is False
        assert not matrix.is_connected
        mock_sock.close.assert_called_once()

    def test_connect_failure_timeout(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = socket.timeout("Connection timed out")

        with patch("hdmimatrix.hdmimatrix.socket.socket", return_value=mock_sock):
            result = matrix.connect()

        assert result is False
        assert not matrix.is_connected

    def test_connect_failure_generic_exception(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("Network unreachable")

        with patch("hdmimatrix.hdmimatrix.socket.socket", return_value=mock_sock):
            result = matrix.connect()

        assert result is False
        assert not matrix.is_connected
        mock_sock.close.assert_called_once()

    def test_disconnect_when_connected(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        assert matrix.is_connected
        matrix.disconnect()
        mock_sock.close.assert_called_once()
        assert not matrix.is_connected

    def test_disconnect_when_not_connected(self, sync_matrix):
        sync_matrix.disconnect()  # should not raise
        assert not sync_matrix.is_connected

    def test_is_connected_true_when_socket_exists(self, sync_matrix):
        sync_matrix.connection = MagicMock()
        assert sync_matrix.is_connected is True

    def test_is_connected_false_when_socket_none(self, sync_matrix):
        assert sync_matrix.is_connected is False


# --- Context manager ---

class TestContextManager:

    def test_connects_and_disconnects(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        mock_sock = MagicMock()
        mock_sock.recv.return_value = WELCOME_DATA

        with patch("hdmimatrix.hdmimatrix.socket.socket", return_value=mock_sock):
            with matrix:
                assert matrix.is_connected
        assert not matrix.is_connected

    def test_raises_on_connect_failure(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = ConnectionRefusedError()

        with patch("hdmimatrix.hdmimatrix.socket.socket", return_value=mock_sock):
            with pytest.raises(RuntimeError, match="Failed to connect"):
                with matrix:
                    pass  # pragma: no cover

    def test_disconnects_on_exception(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
        mock_sock = MagicMock()
        mock_sock.recv.return_value = WELCOME_DATA

        with patch("hdmimatrix.hdmimatrix.socket.socket", return_value=mock_sock):
            with pytest.raises(ValueError):
                with matrix:
                    raise ValueError("test error")
        assert not matrix.is_connected
        mock_sock.close.assert_called()


# --- _process_request ---

class TestProcessRequest:

    def test_raises_when_not_connected_and_reconnect_disabled(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT, auto_reconnect=False)
        with pytest.raises(RuntimeError, match="Not connected"):
            matrix._process_request(b"STA.")

    def test_sends_command_bytes(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        mock_sock.recv.side_effect = make_recv_side_effect([b"OK\r\n"])

        with patch("hdmimatrix.hdmimatrix.time.time") as mock_time, \
             patch("hdmimatrix.hdmimatrix.time.sleep"):
            mock_time.side_effect = [0.0, 0.0, 0.05, 0.6, 1.0, 1.5, 2.0, 2.5]
            matrix._process_request(b"STA.")

        mock_sock.send.assert_called_once_with(b"STA.")

    def test_returns_response_string(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        mock_sock.recv.side_effect = make_recv_side_effect([b"Device OK\r\n"])

        with patch("hdmimatrix.hdmimatrix.time.time") as mock_time, \
             patch("hdmimatrix.hdmimatrix.time.sleep"):
            mock_time.side_effect = [0.0, 0.0, 0.05, 0.6, 1.0, 1.5, 2.0, 2.5]
            result = matrix._process_request(b"STA.")

        assert result == "Device OK"

    def test_auto_reconnects_when_not_connected(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT, auto_reconnect=True)
        # Not connected, auto_reconnect should call connect() then process
        with patch.object(matrix, "connect", return_value=True) as mock_connect, \
             patch.object(matrix, "_read_response", return_value="OK"):
            # After connect, simulate connected state
            mock_sock = MagicMock()
            def set_connected():
                matrix.connection = mock_sock
                return True
            mock_connect.side_effect = set_connected

            result = matrix._process_request(b"STA.")

        mock_connect.assert_called_once()
        mock_sock.send.assert_called_once_with(b"STA.")
        assert result == "OK"

    def test_auto_reconnect_fails_raises_error(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT, auto_reconnect=True)
        with patch.object(matrix, "connect", return_value=False):
            with pytest.raises(RuntimeError, match="auto-reconnect failed"):
                matrix._process_request(b"STA.")

    def test_retries_on_send_failure(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        # First send raises OSError, reconnect succeeds, retry succeeds
        mock_sock.send.side_effect = [OSError("Broken pipe"), None]

        with patch.object(matrix, "connect", return_value=True) as mock_connect, \
             patch.object(matrix, "_read_response", return_value="OK"):
            def restore_connection():
                matrix.connection = mock_sock
                return True
            mock_connect.side_effect = restore_connection

            result = matrix._process_request(b"STA.")

        mock_connect.assert_called_once()
        assert result == "OK"

    def test_reconnect_fails_on_send_failure_raises_error(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        mock_sock.send.side_effect = OSError("Broken pipe")

        with patch.object(matrix, "connect", return_value=False):
            with pytest.raises(RuntimeError, match="Connection lost"):
                matrix._process_request(b"STA.")

    def test_no_retry_when_reconnect_disabled(self):
        matrix = HDMIMatrix(TEST_HOST, TEST_PORT, auto_reconnect=False)
        mock_sock = MagicMock()
        mock_sock.send.side_effect = OSError("Broken pipe")
        matrix.connection = mock_sock

        with pytest.raises(RuntimeError, match="Connection lost"):
            matrix._process_request(b"STA.")


# --- _read_response ---

class TestReadResponse:

    def test_single_chunk(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        mock_sock.recv.side_effect = make_recv_side_effect([b"Hello World\r\n"])

        with patch("hdmimatrix.hdmimatrix.time.time") as mock_time, \
             patch("hdmimatrix.hdmimatrix.time.sleep"):
            mock_time.side_effect = [0.0, 0.0, 0.05, 0.6, 1.0, 1.5, 2.0, 2.5]
            result = matrix._read_response()

        assert result == "Hello World"

    def test_multiple_chunks(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        mock_sock.recv.side_effect = make_recv_side_effect([b"Part1 ", b"Part2\r\n"])

        with patch("hdmimatrix.hdmimatrix.time.time") as mock_time, \
             patch("hdmimatrix.hdmimatrix.time.sleep"):
            # Two successful reads, then timeout triggers end-of-data
            mock_time.side_effect = [0.0, 0.0, 0.05, 0.1, 0.15, 0.7, 1.0, 1.5, 2.0]
            result = matrix._read_response()

        assert result == "Part1 Part2"

    def test_no_data_returns_empty(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        mock_sock.recv.side_effect = socket.timeout

        with patch("hdmimatrix.hdmimatrix.time.time") as mock_time, \
             patch("hdmimatrix.hdmimatrix.time.sleep"):
            # Jump past the total timeout
            mock_time.side_effect = [0.0, 0.0, 0.1, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0, 2.5]
            result = matrix._read_response()

        assert result == ""

    def test_not_connected_returns_empty(self, sync_matrix):
        sync_matrix.connection = None
        result = sync_matrix._read_response()
        assert result == ""

    def test_restores_original_timeout(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        mock_sock.gettimeout.return_value = 5.0
        mock_sock.recv.side_effect = make_recv_side_effect([b"OK"])

        with patch("hdmimatrix.hdmimatrix.time.time") as mock_time, \
             patch("hdmimatrix.hdmimatrix.time.sleep"):
            mock_time.side_effect = [0.0, 0.0, 0.05, 0.6, 1.0, 1.5, 2.0, 2.5]
            matrix._read_response()

        # Should restore original timeout (5.0) after setting it to 0.1
        timeout_calls = [call.args[0] for call in mock_sock.settimeout.call_args_list]
        assert 0.1 in timeout_calls
        assert timeout_calls[-1] == 5.0

    def test_strips_whitespace(self, connected_sync_matrix):
        matrix, mock_sock = connected_sync_matrix
        mock_sock.recv.side_effect = make_recv_side_effect([b"  Device OK  \r\n"])

        with patch("hdmimatrix.hdmimatrix.time.time") as mock_time, \
             patch("hdmimatrix.hdmimatrix.time.sleep"):
            mock_time.side_effect = [0.0, 0.0, 0.05, 0.6, 1.0, 1.5, 2.0, 2.5]
            result = matrix._read_response()

        assert result == "Device OK"


# --- Information methods ---

class TestInfoMethods:

    @pytest.mark.parametrize(
        "method_name,expected_cmd",
        [
            ("get_device_name", b"/*Name."),
            ("get_device_status", b"STA."),
            ("get_device_type", b"/*Type."),
            ("get_device_version", b"/^Version."),
            ("get_video_status", b"STA_VIDEO."),
            ("get_hdbt_power_status", b"STA_PHDBT."),
            ("get_input_status", b"STA_IN."),
            ("get_output_status", b"STA_OUT."),
            ("get_hdcp_status", b"STA_HDCP."),
            ("get_downscaling_status", b"STA_DS."),
        ],
    )
    def test_sends_correct_command(self, sync_matrix, method_name, expected_cmd):
        with patch.object(sync_matrix, "_process_request", return_value="OK") as mock_req:
            method = getattr(sync_matrix, method_name)
            result = method()

        mock_req.assert_called_once_with(expected_cmd)
        assert result == "OK"

    def test_get_video_status_parsed(self, sync_matrix):
        with patch.object(sync_matrix, "get_video_status") as mock_status:
            mock_status.return_value = (
                "Output 1 Switch To In 1!\n"
                "Output 2 Switch To In 3!\n"
            )
            result = sync_matrix.get_video_status_parsed()

        assert result == {1: 1, 2: 3}


# --- Command methods ---

class TestCommandMethods:

    def test_power_on(self, sync_matrix):
        with patch.object(sync_matrix, "_process_request", return_value="OK") as mock_req:
            result = sync_matrix.power_on()
        mock_req.assert_called_once_with(b"PowerON.")
        assert result == "OK"

    def test_power_off(self, sync_matrix):
        with patch.object(sync_matrix, "_process_request", return_value="OK") as mock_req:
            result = sync_matrix.power_off()
        mock_req.assert_called_once_with(b"PowerOFF.")
        assert result == "OK"

    def test_route_input_to_output(self, sync_matrix):
        with patch.object(sync_matrix, "_process_request", return_value="OK") as mock_req:
            result = sync_matrix.route_input_to_output(2, 3)
        # Format: OUT{output:02d}:{input:02d}.
        mock_req.assert_called_once_with(b"OUT03:02.")
        assert result == "OK"

    def test_route_input_to_output_boundary_1_1(self, sync_matrix):
        with patch.object(sync_matrix, "_process_request", return_value="OK") as mock_req:
            sync_matrix.route_input_to_output(1, 1)
        mock_req.assert_called_once_with(b"OUT01:01.")

    def test_route_input_to_output_boundary_4_4(self, sync_matrix):
        with patch.object(sync_matrix, "_process_request", return_value="OK") as mock_req:
            sync_matrix.route_input_to_output(4, 4)
        mock_req.assert_called_once_with(b"OUT04:04.")

    def test_route_input_to_output_invalid_input(self, sync_matrix):
        with pytest.raises(ValueError, match="Input"):
            sync_matrix.route_input_to_output(0, 1)

    def test_route_input_to_output_invalid_output(self, sync_matrix):
        with pytest.raises(ValueError, match="Output"):
            sync_matrix.route_input_to_output(1, 5)

    @pytest.mark.parametrize("output", [1, 2, 3, 4])
    def test_output_on_valid_range(self, sync_matrix, output):
        with patch.object(sync_matrix, "_process_request", return_value="OK") as mock_req:
            sync_matrix.output_on(output)
        expected = f"@OUT{output:02d}.".encode("ascii")
        mock_req.assert_called_once_with(expected)

    def test_output_on_invalid_zero(self, sync_matrix):
        with pytest.raises(ValueError, match="Output must be between"):
            sync_matrix.output_on(0)

    def test_output_on_invalid_five(self, sync_matrix):
        with pytest.raises(ValueError, match="Output must be between"):
            sync_matrix.output_on(5)

    def test_output_on_invalid_negative(self, sync_matrix):
        with pytest.raises(ValueError, match="Output must be between"):
            sync_matrix.output_on(-1)

    @pytest.mark.parametrize("output", [1, 2, 3, 4])
    def test_output_off_valid_range(self, sync_matrix, output):
        with patch.object(sync_matrix, "_process_request", return_value="OK") as mock_req:
            sync_matrix.output_off(output)
        expected = f"$OUT{output:02d}.".encode("ascii")
        mock_req.assert_called_once_with(expected)

    def test_output_off_invalid_zero(self, sync_matrix):
        with pytest.raises(ValueError, match="Output must be between"):
            sync_matrix.output_off(0)

    def test_output_off_invalid_five(self, sync_matrix):
        with pytest.raises(ValueError, match="Output must be between"):
            sync_matrix.output_off(5)
