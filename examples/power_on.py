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
        status = await matrix.power_on()
        print(f"Power off: {status}")

        # # Wait for it to wake up
        wait_time = 5
        # Wait for it to wake up
        print(f"sleeping for {wait_time} seconds")
        await asyncio.sleep(wait_time)
        print("woke up")


        status = await matrix.get_device_status()
        print(f"Status: {status}")
        
        status = await matrix.get_hdcp_status()
        print(f"Status: {status}")



if __name__ == "__main__":
    main()
