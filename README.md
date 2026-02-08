
# AVGear HDMI Matrix Python Library

Python library to control AVGear HDMI Matrix switches (tested with TMX44PRO AVK, may work with others). Both synchronous and asynchronous APIs are provided. Contributions for other models are welcome!

This is used for the [AVGear Matrix integration for homeassistant](https://github.com/marklynch/hass-avgear-matrix).

Inspired by [pyblackbird](https://github.com/koolsb/pyblackbird/).

## Features

- **TCP/IP control**: Communicate with the matrix over the network
- **Sync & Async APIs**: Use either blocking or asyncio-based methods
- **Device info**: Query device name, type, version, and status
- **Routing control**: Route HDMI inputs to outputs programmatically
- **Video status parsing**: Parse and display current input/output routing
- **Context manager support**: Use with `with` or `async with` for auto-connect/disconnect
- **Logging**: Built-in debug/info/error logging

## Installation

Clone the repo and install dependencies (if any):

```bash
git clone https://github.com/marklynch/hdmimatrix.git
cd hdmimatrix
# Optionally: pip install .
```

## Usage

### Synchronous Example

```python
from hdmimatrix import HDMIMatrix

matrix = HDMIMatrix("192.168.0.178", 4001)
with matrix:
    print(matrix.get_device_name())
    print(matrix.get_device_status())
    matrix.route_input_to_output(1, 1)
```

### Asynchronous Example

```python
import asyncio
from hdmimatrix import AsyncHDMIMatrix

async def main():
    matrix = AsyncHDMIMatrix("192.168.0.178", 4001)
    async with matrix:
        print(await matrix.get_device_name())
        print(await matrix.get_device_status())
        await matrix.route_input_to_output(1, 1)

asyncio.run(main())
```

### Video Status Parsing

```python
with matrix:
    routing = matrix.get_video_status_parsed()
    print(routing)  # {1: 1, 2: 3, 3: 2, 4: 4}

    # Show which input is connected to each output
    for output, input_num in sorted(routing.items()):
        print(f"  Output {output} <- Input {input_num}")
```

### Power and Output Control

```python
with matrix:
    matrix.power_on()
    matrix.power_off()

    # Enable/disable individual outputs
    matrix.output_on(2)
    matrix.output_off(2)
```

## API Overview

- `HDMIMatrix` (sync) and `AsyncHDMIMatrix` (async) classes
- Connection:
  - `connect()`
  - `disconnect()`
  - Context manager support (`with` / `async with`)
- Info:
  - `get_device_name()`
  - `get_device_status()`
  - `get_device_type()`
  - `get_device_version()`
  - `get_video_status()`
  - `get_video_status_parsed()`
  - `get_hdbt_power_status()`
  - `get_input_status()`
  - `get_output_status()`
  - `get_hdcp_status()`
  - `get_downscaling_status()`
- Control:
  - `power_on()`
  - `power_off()`
  - `route_input_to_output(input, output)`
  - `output_on(output)`
  - `output_off(output)`

## Development

Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests

python3 -m pytest tests/

# Run with coverage report
python3 -m pytest tests/ --cov=hdmimatrix --cov-report=term-missing

# Generate HTML coverage report
python3 -m pytest tests/ --cov=hdmimatrix --cov-report=html
# Then open htmlcov/index.html in your browser
```

## Contributing

Pull requests for new features, bug fixes, and support for other AVGear models are welcome!

## License

MIT
