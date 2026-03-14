#!/usr/bin/env python3
"""Bridge script: receives a JSON command, drives xdotool/scrot for desktop automation."""

import json
import sys
import subprocess
import base64


def handle(command: dict) -> dict:
    action = command.get("action")

    if action == "screenshot":
        path = "/tmp/screenshot.png"
        subprocess.run(["scrot", path], check=True)
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return {"screenshot": data}

    elif action == "click":
        x, y = command["coords"]
        subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "1"], check=True)
        return {"success": True}

    elif action == "double_click":
        x, y = command["coords"]
        subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "--repeat", "2", "1"], check=True)
        return {"success": True}

    elif action == "type":
        text = command.get("text", "")
        subprocess.run(["xdotool", "type", "--", text], check=True)
        return {"success": True}

    elif action == "scroll":
        x, y = command.get("coords", [0, 0])
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=True)
        subprocess.run(["xdotool", "click", "4"], check=True)  # scroll up; use 5 for down
        return {"success": True}

    else:
        return {"error": f"Unknown action: {action}"}


if __name__ == "__main__":
    cmd = json.loads(sys.argv[1])
    result = handle(cmd)
    print(json.dumps(result))
