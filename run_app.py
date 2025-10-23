#!/usr/bin/env python3
"""
Entry point for PyInstaller to build the whiteboard application.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from whiteboard import main

if __name__ == "__main__":
    main()
