"""Tests for AsyncHDMIMatrix (asynchronous asyncio-based implementation)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hdmimatrix.hdmimatrix import AsyncHDMIMatrix, SOCKET_RECV_BUFFER

from .conftest import TEST_HOST, TEST_PORT, WELCOME_DATA


# --- Helpers for _read_response tests ---

def make_wait_for_replacement(side_effects):
    """Create an async function to replace asyncio.wait_for.

    Uses a plain async function instead of AsyncMock to avoid
    unawaited coroutine warnings from mock internals.
    """
    effects = list(side_effects)
    call_count = 0

    async def fake_wait_for(coro, *, timeout=None):
        nonlocal call_count
        # Consume the original coroutine to avoid ResourceWarning
        if asyncio.iscoroutine(coro):
            coro.close()
        if call_count < len(effects):
            effect = effects[call_count]
            call_count += 1
            if isinstance(effect, type) and issubclass(effect, BaseException):
                raise effect()
            return effect
        raise asyncio.TimeoutError()

    return fake_wait_for


async def noop_sleep(delay):
    """No-op replacement for asyncio.sleep to avoid delays in tests."""
    pass


# --- Connection ---

class TestAsyncConnection:

    async def test_connect_success(self):
        matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=WELCOME_DATA)
        mock_writer = MagicMock()
        mock_writer.is_closing = MagicMock(return_value=False)

        with patch(
            "hdmimatrix.hdmimatrix.asyncio.open_connection",
            new_callable=AsyncMock,
            return_value=(mock_reader, mock_writer),
        ):
            result = await matrix.connect()

        assert result is True
        assert matrix.is_connected
        assert matrix.reader is mock_reader
        assert matrix.writer is mock_writer
        assert isinstance(matrix._connection_lock, asyncio.Lock)

        # Cleanup
        matrix.writer = None
        matrix.reader = None
        matrix._connection_lock = None

    async def test_connect_failure(self):
        matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)

        with patch(
            "hdmimatrix.hdmimatrix.asyncio.open_connection",
            new_callable=AsyncMock,
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            result = await matrix.connect()

        assert result is False
        assert not matrix.is_connected

    async def test_connect_welcome_data_timeout(self):
        """Welcome data timeout is caught and connect still succeeds."""
        matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)
        mock_reader = MagicMock()
        # Use a plain MagicMock for read to avoid creating unawaited coroutines
        # when wait_for is patched to raise TimeoutError before calling it
        mock_reader.read = MagicMock(return_value=b"")
        mock_writer = MagicMock()
        mock_writer.is_closing = MagicMock(return_value=False)

        async def fake_wait_for(coro, *, timeout=None):
            if asyncio.iscoroutine(coro):
                coro.close()
            raise asyncio.TimeoutError()

        with patch(
            "hdmimatrix.hdmimatrix.asyncio.open_connection",
            new_callable=AsyncMock,
            return_value=(mock_reader, mock_writer),
        ):
            with patch(
                "hdmimatrix.hdmimatrix.asyncio.wait_for",
                side_effect=fake_wait_for,
            ):
                result = await matrix.connect()

        assert result is True

        # Cleanup
        matrix.writer = None
        matrix.reader = None
        matrix._connection_lock = None

    async def test_disconnect_when_connected(self):
        matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=WELCOME_DATA)
        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        mock_writer.is_closing = MagicMock(return_value=False)

        with patch(
            "hdmimatrix.hdmimatrix.asyncio.open_connection",
            new_callable=AsyncMock,
            return_value=(mock_reader, mock_writer),
        ):
            await matrix.connect()

        await matrix.disconnect()

        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_awaited_once()
        assert matrix.writer is None
        assert matrix.reader is None
        assert matrix._connection_lock is None

    async def test_disconnect_when_not_connected(self, async_matrix):
        await async_matrix.disconnect()  # should not raise

    def test_is_connected_true(self, async_matrix):
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        async_matrix.writer = mock_writer
        assert async_matrix.is_connected is True

    def test_is_connected_false_no_writer(self, async_matrix):
        assert async_matrix.is_connected is False

    def test_is_connected_false_writer_closing(self, async_matrix):
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = True
        async_matrix.writer = mock_writer
        assert async_matrix.is_connected is False


# --- Async context manager ---

class TestAsyncContextManager:

    async def test_connects_and_disconnects(self):
        matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=WELCOME_DATA)
        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        mock_writer.is_closing = MagicMock(return_value=False)

        with patch(
            "hdmimatrix.hdmimatrix.asyncio.open_connection",
            new_callable=AsyncMock,
            return_value=(mock_reader, mock_writer),
        ):
            async with matrix:
                assert matrix.is_connected

        assert not matrix.is_connected

    async def test_raises_on_connect_failure(self):
        matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)

        with patch(
            "hdmimatrix.hdmimatrix.asyncio.open_connection",
            new_callable=AsyncMock,
            side_effect=ConnectionRefusedError(),
        ):
            with pytest.raises(RuntimeError, match="Failed to connect"):
                async with matrix:
                    pass  # pragma: no cover

    async def test_disconnects_on_exception(self):
        matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)
        mock_reader = MagicMock()
        mock_reader.read = AsyncMock(return_value=WELCOME_DATA)
        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        mock_writer.is_closing = MagicMock(return_value=False)

        with patch(
            "hdmimatrix.hdmimatrix.asyncio.open_connection",
            new_callable=AsyncMock,
            return_value=(mock_reader, mock_writer),
        ):
            with pytest.raises(ValueError):
                async with matrix:
                    raise ValueError("test error")

        assert not matrix.is_connected
        mock_writer.close.assert_called()


# --- _process_request ---

class TestAsyncProcessRequest:

    async def test_raises_when_not_connected(self, async_matrix):
        with pytest.raises(RuntimeError, match="Not connected"):
            await async_matrix._process_request(b"STA.")

    async def test_sends_and_drains(self, connected_async_matrix):
        matrix, mock_reader, mock_writer = connected_async_matrix

        with patch.object(matrix, "_read_response", new_callable=AsyncMock, return_value="OK"):
            await matrix._process_request(b"STA.")

        mock_writer.write.assert_called_once_with(b"STA.")
        mock_writer.drain.assert_awaited_once()

    async def test_returns_response(self, connected_async_matrix):
        matrix, mock_reader, mock_writer = connected_async_matrix

        with patch.object(matrix, "_read_response", new_callable=AsyncMock, return_value="Device OK"):
            result = await matrix._process_request(b"STA.")

        assert result == "Device OK"


# --- _read_response ---

class TestAsyncReadResponse:

    async def test_single_chunk(self, connected_async_matrix):
        matrix, _, _ = connected_async_matrix

        fake_wait_for = make_wait_for_replacement([b"Hello World\r\n", asyncio.TimeoutError])
        mock_loop = MagicMock()
        times = iter([0.0, 0.0, 0.05, 0.6, 1.0, 1.5, 2.0, 2.5])
        mock_loop.time = MagicMock(side_effect=lambda: next(times))

        with patch("hdmimatrix.hdmimatrix.asyncio.wait_for", side_effect=fake_wait_for):
            with patch("hdmimatrix.hdmimatrix.asyncio.get_event_loop", return_value=mock_loop):
                with patch("hdmimatrix.hdmimatrix.asyncio.sleep", side_effect=noop_sleep):
                    result = await matrix._read_response()

        assert result == "Hello World"

    async def test_multiple_chunks(self, connected_async_matrix):
        matrix, _, _ = connected_async_matrix

        fake_wait_for = make_wait_for_replacement([b"Part1 ", b"Part2\r\n", asyncio.TimeoutError])
        mock_loop = MagicMock()
        times = iter([0.0, 0.0, 0.05, 0.1, 0.15, 0.7, 1.0, 1.5, 2.0, 2.5])
        mock_loop.time = MagicMock(side_effect=lambda: next(times))

        with patch("hdmimatrix.hdmimatrix.asyncio.wait_for", side_effect=fake_wait_for):
            with patch("hdmimatrix.hdmimatrix.asyncio.get_event_loop", return_value=mock_loop):
                with patch("hdmimatrix.hdmimatrix.asyncio.sleep", side_effect=noop_sleep):
                    result = await matrix._read_response()

        assert result == "Part1 Part2"

    async def test_no_data_returns_empty(self, connected_async_matrix):
        matrix, _, _ = connected_async_matrix

        fake_wait_for = make_wait_for_replacement([asyncio.TimeoutError])
        mock_loop = MagicMock()
        times = iter([0.0, 0.0, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 2.5])
        mock_loop.time = MagicMock(side_effect=lambda: next(times))

        with patch("hdmimatrix.hdmimatrix.asyncio.wait_for", side_effect=fake_wait_for):
            with patch("hdmimatrix.hdmimatrix.asyncio.get_event_loop", return_value=mock_loop):
                with patch("hdmimatrix.hdmimatrix.asyncio.sleep", side_effect=noop_sleep):
                    result = await matrix._read_response()

        assert result == ""

    async def test_not_connected_returns_empty(self, async_matrix):
        async_matrix.reader = None
        result = await async_matrix._read_response()
        assert result == ""

    async def test_connection_closed_returns_partial(self, connected_async_matrix):
        """When reader returns empty bytes, connection is closed."""
        matrix, _, _ = connected_async_matrix

        fake_wait_for = make_wait_for_replacement([b"Partial", b""])
        mock_loop = MagicMock()
        times = iter([0.0, 0.0, 0.05, 0.1, 0.15, 0.2, 0.5, 1.0, 1.5, 2.0])
        mock_loop.time = MagicMock(side_effect=lambda: next(times))

        with patch("hdmimatrix.hdmimatrix.asyncio.wait_for", side_effect=fake_wait_for):
            with patch("hdmimatrix.hdmimatrix.asyncio.get_event_loop", return_value=mock_loop):
                with patch("hdmimatrix.hdmimatrix.asyncio.sleep", side_effect=noop_sleep):
                    result = await matrix._read_response()

        assert result == "Partial"


# --- Information methods ---

class TestAsyncInfoMethods:

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
    async def test_sends_correct_command(self, async_matrix, method_name, expected_cmd):
        with patch.object(
            async_matrix, "_process_request", new_callable=AsyncMock, return_value="OK"
        ) as mock_req:
            method = getattr(async_matrix, method_name)
            result = await method()

        mock_req.assert_called_once_with(expected_cmd)
        assert result == "OK"

    async def test_get_video_status_parsed(self, async_matrix):
        with patch.object(
            async_matrix, "get_video_status", new_callable=AsyncMock
        ) as mock_status:
            mock_status.return_value = (
                "Output 1 Switch To In 1!\n"
                "Output 2 Switch To In 3!\n"
            )
            result = await async_matrix.get_video_status_parsed()

        assert result == {1: 1, 2: 3}


# --- Command methods ---

class TestAsyncCommandMethods:

    async def test_power_on(self, async_matrix):
        with patch.object(
            async_matrix, "_process_request", new_callable=AsyncMock, return_value="OK"
        ) as mock_req:
            result = await async_matrix.power_on()
        mock_req.assert_called_once_with(b"PowerON.")
        assert result == "OK"

    async def test_power_off(self, async_matrix):
        with patch.object(
            async_matrix, "_process_request", new_callable=AsyncMock, return_value="OK"
        ) as mock_req:
            result = await async_matrix.power_off()
        mock_req.assert_called_once_with(b"PowerOFF.")
        assert result == "OK"

    async def test_route_input_to_output(self, async_matrix):
        with patch.object(
            async_matrix, "_process_request", new_callable=AsyncMock, return_value="OK"
        ) as mock_req:
            result = await async_matrix.route_input_to_output(2, 3)
        mock_req.assert_called_once_with(b"OUT03:02.")
        assert result == "OK"

    async def test_route_input_to_output_invalid_input(self, async_matrix):
        with pytest.raises(ValueError, match="Input"):
            await async_matrix.route_input_to_output(0, 1)

    async def test_route_input_to_output_invalid_output(self, async_matrix):
        with pytest.raises(ValueError, match="Output"):
            await async_matrix.route_input_to_output(1, 5)

    @pytest.mark.parametrize("output", [1, 2, 3, 4])
    async def test_output_on_valid_range(self, async_matrix, output):
        with patch.object(
            async_matrix, "_process_request", new_callable=AsyncMock, return_value="OK"
        ) as mock_req:
            await async_matrix.output_on(output)
        expected = f"@OUT{output:02d}.".encode("ascii")
        mock_req.assert_called_once_with(expected)

    async def test_output_on_invalid_zero(self, async_matrix):
        with pytest.raises(ValueError, match="Output must be between"):
            await async_matrix.output_on(0)

    async def test_output_on_invalid_five(self, async_matrix):
        with pytest.raises(ValueError, match="Output must be between"):
            await async_matrix.output_on(5)

    @pytest.mark.parametrize("output", [1, 2, 3, 4])
    async def test_output_off_valid_range(self, async_matrix, output):
        with patch.object(
            async_matrix, "_process_request", new_callable=AsyncMock, return_value="OK"
        ) as mock_req:
            await async_matrix.output_off(output)
        expected = f"$OUT{output:02d}.".encode("ascii")
        mock_req.assert_called_once_with(expected)

    async def test_output_off_invalid_zero(self, async_matrix):
        with pytest.raises(ValueError, match="Output must be between"):
            await async_matrix.output_off(0)

    async def test_output_off_invalid_five(self, async_matrix):
        with pytest.raises(ValueError, match="Output must be between"):
            await async_matrix.output_off(5)
