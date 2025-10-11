#!/usr/bin/env python3
from hdmimatrix import HDMIMatrix, AsyncHDMIMatrix
import asyncio

def main():
    """Example usage of the AVGear TMX44PRO controller"""

    # # Create controller instance
    # matrix = hdmimatrix.HDMIMatrix(host="192.168.0.178", port=4001)  # Replace with your device IP

    # matrix.connect()
    # print(matrix)


    # name = matrix.get_device_name()
    # print("Device name:", name)

    # # status = matrix.get_device_status()
    # # print("Device status:", status)

    # # type = matrix.get_device_type()
    # # print("Device type:", type)


    # # version = matrix.get_device_version()
    # # print("Device version:", version)

    # power = matrix.power_on()
    # print(power)

    # output = matrix.route_input_to_output(1,1)
    # print(output)

    # matrix.disconnect()
    
    # example_sync_usage()
    asyncio.run(example_async_usage())

    # asyncio.run(example_concurrent_operations())

async def example_async_usage():
    """Example of how to use the AsyncHDMIMatrix class"""
    matrix = AsyncHDMIMatrix("192.168.0.178", 4001)
    
    # Using async context manager
    async with matrix:
        # Get device information
        name = await matrix.get_device_name()
        print(f"Device name: {name}")
        
        type = await matrix.get_device_type()
        print(f"Device type: {type}")
        
        version = await matrix.get_device_version()
        print(f"Device version: {version}")

        # status = await matrix.get_device_status()
        # print(f"Status: {status}")
        
        status = await matrix.get_video_status()
        print(f"Video Status: {status}")

        status = await matrix.get_video_status_parsed()
        print(f"Video Status: {status}")

        hdbt_power = await matrix.get_hdbt_power_status()
        print(f"HDBT Power Status: {hdbt_power}")

        input_status = await matrix.get_input_status()
        print(f"Input Status: {input_status}")

        output_status = await matrix.get_output_status()
        print(f"Output Status: {output_status}")

        # Route input 1 to output 1
        result = await matrix.route_input_to_output(1, 1)
        print(f"Route result: {result}")


def example_sync_usage():
    """Example of how to use the original HDMIMatrix class"""
    matrix = HDMIMatrix("192.168.0.178", 4001)
    
    # Using sync context manager
    with matrix:
        # Get device information
        name = matrix.get_device_name()
        print(f"Device name: {name}")
        
        status = matrix.get_device_status()
        print(f"Status: {status}")
        
        status = matrix.get_video_status()
        print(f"Video Status: {status}")

        status = matrix.get_video_status_parsed()
        print(f"Video Status: {status}")

        hdbt_power = matrix.get_hdbt_power_status()
        print(f"HDBT Power Status: {hdbt_power}")

        input_status = matrix.get_input_status()
        print(f"Input Status: {input_status}")

        output_status = matrix.get_output_status()
        print(f"Output Status: {output_status}")

        # Route input 1 to output 1
        result = matrix.route_input_to_output(1, 1)
        print(f"Route result: {result}")



async def example_concurrent_operations():
    """Example showing that async operations are serialized due to TCP connection constraints"""
    matrix = AsyncHDMIMatrix("192.168.0.178", 4001)
    
    async with matrix:
        # These operations will be serialized due to the connection lock
        # but they're still async and won't block the event loop
        tasks = [
            matrix.get_device_name(),
            matrix.get_device_status(),
            matrix.get_device_type(),
            matrix.get_device_version()
        ]
        
        results = await asyncio.gather(*tasks)
        print("Results (executed serially due to TCP constraint):", results)
        
        # Sequential routing operations
        await matrix.route_input_to_output(1, 1)
        await matrix.route_input_to_output(2, 2)

if __name__ == "__main__":
    main()
