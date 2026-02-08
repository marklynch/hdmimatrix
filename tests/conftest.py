"""Shared fixtures and helpers for hdmimatrix tests."""

import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hdmimatrix.hdmimatrix import (
    AsyncHDMIMatrix,
    HDMIMatrix,
    SOCKET_RECV_BUFFER,
    SOCKET_TIMEOUT,
)

# --- Test constants ---
TEST_HOST = "10.0.0.99"
TEST_PORT = 5001
WELCOME_DATA = b"Welcome to HDMI Matrix\r\n"

SAMPLE_VIDEO_STATUS = (
    "Output 1 Switch To In 1!\n"
    "Output 2 Switch To In 3!\n"
    "Output 3 Switch To In 2!\n"
    "Output 4 Switch To In 4!\n"
)

SAMPLE_VIDEO_STATUS_PARSED = {1: 1, 2: 3, 3: 2, 4: 4}


# --- Helpers ---

def make_recv_side_effect(data_chunks):
    """Create a side_effect callable for mock socket.recv.

    Returns data chunks in order, then raises socket.timeout forever.
    """
    chunks = list(data_chunks)
    index = 0

    def side_effect(bufsize):
        nonlocal index
        if index < len(chunks):
            chunk = chunks[index]
            index += 1
            return chunk
        raise socket.timeout

    return side_effect


def make_async_read_side_effect(data_chunks):
    """Create a side_effect list for mock async reader.read.

    Returns data chunks in order, then raises asyncio.TimeoutError.
    """
    effects = list(data_chunks) + [asyncio.TimeoutError]
    return effects


# --- Sync fixtures ---

@pytest.fixture
def sync_matrix():
    """Unconnected HDMIMatrix instance."""
    return HDMIMatrix(TEST_HOST, TEST_PORT)


@pytest.fixture
def connected_sync_matrix():
    """HDMIMatrix with a mocked socket connection.

    Yields (matrix, mock_socket). After connect, recv is reset to raise
    socket.timeout so tests can configure their own responses.
    """
    matrix = HDMIMatrix(TEST_HOST, TEST_PORT)
    mock_sock = MagicMock()
    mock_sock.recv.return_value = WELCOME_DATA
    mock_sock.gettimeout.return_value = SOCKET_TIMEOUT

    with patch("hdmimatrix.hdmimatrix.socket.socket", return_value=mock_sock):
        result = matrix.connect()
        assert result is True

    # Reset recv so tests can set their own side_effect
    mock_sock.recv.reset_mock()
    mock_sock.recv.side_effect = socket.timeout

    yield matrix, mock_sock

    matrix.disconnect()


# --- Async fixtures ---

@pytest.fixture
def async_matrix():
    """Unconnected AsyncHDMIMatrix instance."""
    return AsyncHDMIMatrix(TEST_HOST, TEST_PORT)


@pytest.fixture
async def connected_async_matrix():
    """AsyncHDMIMatrix with mocked asyncio streams.

    Yields (matrix, mock_reader, mock_writer). After connect, reader.read
    is reset to raise asyncio.TimeoutError so tests can configure responses.
    """
    matrix = AsyncHDMIMatrix(TEST_HOST, TEST_PORT)

    mock_reader = MagicMock()
    mock_reader.read = AsyncMock(return_value=WELCOME_DATA)

    mock_writer = MagicMock()
    mock_writer.write = MagicMock()
    mock_writer.drain = AsyncMock()
    mock_writer.close = MagicMock()
    mock_writer.wait_closed = AsyncMock()
    mock_writer.is_closing = MagicMock(return_value=False)

    with patch(
        "hdmimatrix.hdmimatrix.asyncio.open_connection",
        new_callable=AsyncMock,
        return_value=(mock_reader, mock_writer),
    ):
        result = await matrix.connect()
        assert result is True

    # Reset reader for test-specific configuration
    mock_reader.read.reset_mock()
    mock_reader.read.side_effect = asyncio.TimeoutError

    yield matrix, mock_reader, mock_writer

    # Teardown - clear references without calling real close
    matrix.writer = None
    matrix.reader = None
    matrix._connection_lock = None
