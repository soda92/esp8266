#!/bin/bash
# Script to upload main.py (and the driver) to the ESP8266

# Port configuration - persistent symlink
PORT=/dev/esp8266

echo "Uploading il3820.py..."
uv run ampy --port $PORT put il3820.py

echo "Uploading main.py..."
uv run ampy --port $PORT put main.py

echo "Done! Press the Reset button on your board."
