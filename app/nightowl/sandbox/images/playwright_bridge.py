#!/usr/bin/env python3
"""Bridge script: receives a JSON command string, drives Playwright, returns JSON result."""

import json
import sys
import base64

from playwright.sync_api import sync_playwright

_browser = None
_page = None


def _ensure_browser():
    global _browser, _page
    if _browser is None:
        pw = sync_playwright().start()
        _browser = pw.chromium.launch(headless=True)
        _page = _browser.new_page()
    return _page


def handle(command: dict) -> dict:
    page = _ensure_browser()
    action = command.get("action")

    if action == "navigate":
        page.goto(command["url"], wait_until="domcontentloaded")
        return {"title": page.title(), "text": page.inner_text("body")[:4000]}

    elif action == "click":
        page.click(command["selector"])
        return {"action": "click", "success": True}

    elif action == "fill":
        page.fill(command["selector"], command.get("value", ""))
        return {"action": "fill", "success": True}

    elif action == "select":
        page.select_option(command["selector"], command.get("value", ""))
        return {"action": "select", "success": True}

    elif action == "screenshot":
        data = page.screenshot()
        return {"screenshot": base64.b64encode(data).decode()}

    else:
        return {"error": f"Unknown action: {action}"}


if __name__ == "__main__":
    cmd = json.loads(sys.argv[1])
    result = handle(cmd)
    print(json.dumps(result))
