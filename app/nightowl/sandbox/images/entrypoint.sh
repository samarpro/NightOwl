#!/bin/bash
# Start Xvfb and VNC server, then exec the CMD
Xvfb :99 -screen 0 1280x1024x24 &
sleep 0.5
x11vnc -display :99 -nopw -forever -quiet &
exec "$@"
