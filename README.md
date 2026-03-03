
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

    # Enable/disable all outputs at once
    matrix.all_outputs_on()
    matrix.all_outputs_off()

    # Enable/disable HDBaseT receiver power
    matrix.hdbt_power_on()
    matrix.hdbt_power_off()
```

### Power management
Working torwards making it easy to run this efficiently for example by making it easy to power off overnight here are some measurements.
- Overall power usage ~ 60w
- Turning off an output channel reduces about 2.5w per channel
- Turning off HDBT power saves approx 34w with 4 channels plugged in.
- So with all channels turned off and hdbt - it runs at ~19w 
- Turning power off has a residual power usage of ~4w

## API Overview

- `HDMIMatrix` (sync) and `AsyncHDMIMatrix` (async) classes
- Connection:
  - `connect()`
  - `disconnect()`
  - Context manager support (`with` / `async with`)
- Info:
  - `is_powered_on()`
  - `is_hdbt_powered_on()`
  - `is_output_on(output_num)` — cached for 1 s
  - `get_device_name()`
  - `get_device_status()`
  - `get_device_type()`
  - `get_device_version()`
  - `get_video_status()`
  - `get_video_status_parsed()`
  - `get_hdbt_power_status()`
  - `get_input_status()`
  - `get_input_status_parsed()`
  - `get_output_status()`
  - `get_output_status_parsed()`
  - `get_output_power_status()`
  - `get_output_power_status_parsed()`
  - `get_hdcp_status()`
  - `get_downscaling_status()`
- Control:
  - `power_on()`
  - `power_off()`
  - `route_input_to_output(input, output)`
  - `output_on(output)` — outputs 1–8 (1–4 HDBaseT, 5–8 HDMI loop)
  - `output_off(output)` — outputs 1–8
  - `all_outputs_on()`
  - `all_outputs_off()`
  - `hdbt_power_on()`
  - `hdbt_power_off()`

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
