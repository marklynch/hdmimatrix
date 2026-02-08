#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Allow running directly from the examples/ directory without installing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hdmimatrix import HDMIMatrix, AsyncHDMIMatrix

def main():
    """Example usage of the AVGear TMX44PRO controller"""   
    # example_sync_usage()
    asyncio.run(example_async_usage())

async def example_async_usage():
    """Example of how to use the AsyncHDMIMatrix class"""
    matrix = AsyncHDMIMatrix("192.168.0.178", 4001)

    # Using async context manager
    async with matrix:
        # Get device information
        # name = await matrix.get_device_name()
        # print(f"Device name: {name}")

        # type = await matrix.get_device_type()
        # print(f"Device type: {type}")

        # version = await matrix.get_device_version()
        # print(f"Device version: {version}")

        # status = await matrix.power_on()
        # print(f"Power ON: {status}")

        # # Wait for it to wake up
        # wait_time = 8
        # # Wait for it to wake up
        # print(f"sleeping for {wait_time} seconds")
        # await asyncio.sleep(wait_time)
        # print("woke up")


        status = await matrix.get_device_status()
        print(f"Status: {status}")

        # status = await matrix.get_video_status()
        # print(f"Video Status: {status}")

        # status = await matrix.get_video_status_parsed()
        # print(f"Video Status: {status}")

        # hdbt_power = await matrix.get_hdbt_power_status()
        # print(f"HDBT Power Status: {hdbt_power}")

        # input_status = await matrix.get_input_status()
        # print(f"Input Status: {input_status}")

        # output_status = await matrix.get_output_status()
        # print(f"Output Status: {output_status}")

        # result = await matrix.output_on(1)
        # print(f"Output on result: {result}")


        # # Route input 1 to output 1
        # result = await matrix.route_input_to_output(1, 1)
        # print(f"Route result: {result}")

        status = await matrix.get_hdcp_status()
        print(f"Status: {status}")

        downscaling_status = await matrix.get_downscaling_status()
        print(f"Downscaling Status: {downscaling_status}")




if __name__ == "__main__":
    main()
