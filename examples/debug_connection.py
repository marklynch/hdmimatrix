#!/usr/bin/env python3
import asyncio
import socket
import errno

async def test_async_connection():
    """Test basic async connection"""
    try:
        print("Testing async connection...")
        reader, writer = await asyncio.open_connection('192.168.0.178', 4001)
        print("Async connection successful!")
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        print(f"Async connection failed: {e}")
        print(f"Error type: {type(e)}")

def test_sync_connection():
    """Test basic sync connection"""
    try:
        print("Testing sync connection...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('192.168.0.178', 4001))
        if result == 0:
            print("Sync connection successful!")
        else:
            print(f"Sync connection failed with code: {result}")
            print(f"Error meaning: {errno.errorcode.get(result, 'Unknown')}")
        sock.close()
    except Exception as e:
        print(f"Sync connection failed: {e}")

def test_sync_connection_direct():
    """Test direct socket connection"""
    try:
        print("Testing direct socket connection...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('192.168.0.178', 4001))
        print("Direct socket connection successful!")
        sock.close()
    except Exception as e:
        print(f"Direct socket connection failed: {e}")

if __name__ == "__main__":
    test_sync_connection()
    test_sync_connection_direct()
    asyncio.run(test_async_connection())