# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
python3 -m pytest tests/

# Run a single test file
python3 -m pytest tests/test_sync.py

# Run a single test
python3 -m pytest tests/test_sync.py::TestConnect::test_connect_success

# Run tests with coverage
python3 -m pytest tests/ --cov=hdmimatrix --cov-report=term-missing

# Lint
ruff check hdmimatrix/ tests/

# Type check
mypy hdmimatrix/

# Build for PyPI
python3 -m build
python3 -m twine upload dist/*          # real upload
python3 -m twine upload --repository testpypi dist/*  # test upload
```

## Architecture

All code lives in a single module: `hdmimatrix/hdmimatrix.py`.

### Class hierarchy

```
BaseHDMIMatrix (ABC)
├── HDMIMatrix        — synchronous, uses socket
└── AsyncHDMIMatrix   — asynchronous, uses asyncio streams
```

`BaseHDMIMatrix` holds all shared logic: validation helpers (`_validate_routing_params`, `_build_route_command`, etc.), video status parsing (`parse_video_status`), and the `Commands` enum with all wire protocol strings.

### Auto-generated methods

The `_SIMPLE_COMMANDS` dict in `BaseHDMIMatrix` maps method names to `(docstring, Commands member)` pairs. `__init_subclass__` inspects each concrete subclass and auto-generates either sync or async wrappers for any name not already defined in that subclass. This means methods like `get_device_name`, `power_on`, `get_video_status`, etc. are not written explicitly in `HDMIMatrix` or `AsyncHDMIMatrix` — they are generated at class definition time. Only methods that need extra logic (e.g. `route_input_to_output`, `get_video_status_parsed`) are defined explicitly.

### Protocol

The device speaks a simple ASCII line protocol over TCP (default port 4001). Commands end with `.` (e.g. `STA_VIDEO.`, `OUT01:02.`). Responses are multi-line with no framing delimiter, so `_read_response` collects chunks until a 0.5 s idle gap (`SOCKET_END_OF_DATA_TIMEOUT`) or the 2 s total timeout.

### Tests

Tests are fully mock-based (no real device needed). `tests/conftest.py` provides shared fixtures:
- `sync_matrix` / `async_matrix` — unconnected instances
- `connected_sync_matrix` / `connected_async_matrix` — instances with a mocked socket/stream, pre-connected, with `recv`/`read` reset to raise timeout so each test can configure its own response chunks

Use `make_recv_side_effect(chunks)` (sync) or `make_async_read_side_effect(chunks)` (async) from conftest to simulate multi-chunk device responses.

`asyncio_mode = "auto"` is set in `pyproject.toml`, so async test functions work without explicit `@pytest.mark.asyncio`.
