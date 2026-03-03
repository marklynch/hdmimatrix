#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Allow running directly from the examples/ directory without installing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hdmimatrix import HDMIMatrix, CECLogicalAddress, CECCommand

with HDMIMatrix("192.168.0.178") as matrix:
    # Power on the display connected to output 1
    # (matrix at logical addr 4 → TV at addr 0)
    # Works
    # matrix.send_cec_command("O", 1, CECLogicalAddress.PLAYBACK_1, CECLogicalAddress.TV, CECCommand.DISPLAY_POWER_ON)

    # Doesn't work
    # matrix.send_cec_command("O", 1, CECLogicalAddress.PLAYBACK_1, CECLogicalAddress.BROADCAST, CECCommand.DISPLAY_POWER_OFF)

    matrix.send_cec_command("O", 1, CECLogicalAddress.PLAYBACK_2, CECLogicalAddress.TV, CECCommand.DISPLAY_POWER_OFF)
    # # Mute the display on output 1 - works
    # matrix.send_cec_command("O", 1, CECLogicalAddress.PLAYBACK_1, CECLogicalAddress.TV, CECCommand.DISPLAY_MUTE)


    # matrix.send_cec_command("O", 1, CECLogicalAddress.PLAYBACK_1, CECLogicalAddress.TV, CECCommand.DISPLAY_VOLUME_UP)

    # # Power off an input source (e.g. Blu-ray on input 1)
    # matrix.send_cec_command("I", 1, CECLogicalAddress.TV, CECLogicalAddress.PLAYBACK_1, CECCommand.SOURCE_POWER_OFF)