#!/usr/bin/env python3
"""
ohbot_pi.py — compatibility shim
Version: 6.0.0 (forwards to yobot_core)

All the real code now lives in yobot_core.py, which works on the
Raspberry Pi, macOS, and (eventually) Windows.

This file exists so the many programs that do `import ohbot_pi as ohbot`
(gui_server, ohbot_azure, ohbot_chat, calibration_server, timeline_server,
yobot_calibrate, ...) keep working with zero changes.

How it works: this module replaces itself with yobot_core in Python's
module table, so `import ohbot_pi` hands back the yobot_core module
itself. Reading AND writing attributes (e.g. the calibration scripts set
`ohbot.motorDefFile = ...`) both act directly on yobot_core — they are
literally the same module.
"""

import sys
import yobot_core

sys.modules['ohbot_pi'] = yobot_core
