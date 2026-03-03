# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [Unreleased]
### Added
- Added `get_output_power_status()` — queries the power on/off state of each output port (`STA_POUT.`).
- Added `get_output_power_status_parsed()` — parses the `STA_POUT.` response into a `{port: bool}` dict.
### Changed
### Fixed
### Removed


## [0.5.0] - 2026-03-02
### Added
- Added `is_hdbt_powered_on()` — returns `True` if HDBaseT power is currently on.

## [0.4.0] - 2026-03-02
### Added
- Added `get_input_status_parsed()` — parses `STA_IN.` response into `{port: bool}` dict.
- Added `get_output_status_parsed()` — parses `STA_OUT.` response into `{port: bool}` dict.
- Added `all_outputs_on()` / `all_outputs_off()` — enable/disable all output ports at once (`@OUT00.` / `$OUT00.`).
- Added `hdbt_power_on()` / `hdbt_power_off()` — power the HDBaseT receivers on/off (`PHDBTON.` / `PHDBTOFF.`).

## [0.3.0] - 2026-03-01
### Added
- Added `is_powered_on()` helper function.

## [0.2.0] - 2026-02-25
### Added
- Added autoreconnect functionality
- Added docstrings to all public methods that were missing them
- Explicit __all__: Added __all__ = ["HDMIMatrix", "AsyncHDMIMatrix", "Commands"]

### Changed
- Use `logging.INFO` instead of `'INFO'` string when setting loglevel
- Cleanup extra whitespace in file
- Refactored `HDMIMatrix` and `AsyncHDMIMatrix` to reduce duplicated code
- Import organization: Reorganized imports in alphabetical order for better maintainability
- Logging improvements: Added guard to prevent duplicate log handlers when multiple instances share the same logger
- Socket timeout handling: Wrapped welcome banner reception in try-except to gracefully handle devices that don't send one
- Error handling in _read_response: Improved exception handling with proper socket timeout restoration using a finally block to ensure cleanup even when errors occur
- Async event loop: Replaced deprecated asyncio.get_event_loop() with asyncio.get_running_loop() for better async context handling


## [0.1.0] - 2026-02-08
### Added
- `__repr__` method on base class for easier debugging (e.g. `HDMIMatrix(192.168.0.178:4001, connected=True)`).
- Added examples to the examples folder
- Added tests for the whole library

### Fixed
- Socket not cleaned up on failed connection — `connect()` now closes and nullifies the socket in the error path, preventing `is_connected` from incorrectly returning `True` after a connection failure.
- Added dev tools dependencies and configuration to `pyproject.toml`


## [0.0.6] - 2025-10-13
### Added
- Support for `get_hdcp_status()` and `get_downscaling_status()` commands.

## [0.0.5] - 2025-10-13
### Added
- Support for `output_on` and `output_off` commands.

## [0.0.4] - 2025-10-11
### Added
- Support for `get_hdbt_power_status` and `get_input_status` and `get_output_status` commands.
- Added documenation manuals for reference.

## [0.0.3] - 2025-08-09
### Added
- Support for `get_video_status` and `get_video_status_parsed` to show the routing matrix

## [0.0.2] - 2025-08-08
### Added
- Support for async methods to support homeassistant

## [0.0.1] - 2025-08-06
### Added
- Basic functionality working - poweron/off, switch input/output and get status, version and name