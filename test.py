#!/usr/bin/env python3
import hdmimatrix

def main():
    """Example usage of the AVGear TMX44PRO controller"""

    # Create controller instance
    matrix = hdmimatrix.HDMIMatrix(host="192.168.0.178", port=4001)  # Replace with your device IP

    matrix.connect()
    print(matrix)


    name = matrix.get_device_name()
    print("Device name:", name)

    # status = matrix.get_device_status()
    # print("Device status:", status)

    # type = matrix.get_device_type()
    # print("Device type:", type)


    # version = matrix.get_device_version()
    # print("Device version:", version)

    power = matrix.power_on()
    print(power)

    output = matrix.route_input_to_output(1,1)
    print(output)

    matrix.disconnect()
    




if __name__ == "__main__":
    main()
