# Sandbox

Ephemeral Docker containers for sandboxed agent execution. Each sandbox mode (CLI, browser, computer use) maps to a dedicated Docker image with the appropriate tooling pre-installed.

## Container Lifecycle

Containers are created lazily on first tool use via `ensure_container()` — no upfront provisioning. Each session gets at most one container per mode. Containers are resource-limited (512MB RAM, 0.5 CPU by default) and labeled with the session ID. On shutdown, `cleanup_all()` stops and removes all tracked containers.

## Manager (`manager.py`)

`DockerSandboxManager` tracks session-to-container mappings and provides the core operations: create, exec, cleanup, and file extraction. All Docker operations run in a thread executor to avoid blocking the event loop.

On container creation, the manager fetches active Composio credentials (currently GitHub tokens) and injects them as environment variables. A git credential helper is automatically configured so `git clone`/`push` with HTTPS URLs works without the agent needing to handle authentication.

## Tools

Execution tools are `@hitl_gated` — the agent must self-report risk. File tools are ungated (read-only or contained writes).

### `bash_exec` (`bash_tool.py`)

Runs a shell command inside a CLI container. Returns stdout on success, stderr + exit code on failure.

### Browser tools (`browser_tool.py`)

Three tools for headless browsing via Playwright inside a browser container:

- **`browser_navigate`** — navigate to a URL, returns page snapshot
- **`browser_interact`** — interact with elements (click, fill, select) by CSS selector
- **`browser_screenshot`** — capture the current page as base64

Commands are serialized as JSON and executed via a `playwright-bridge` helper script inside the container.

### Computer use tools (`computer_use_tool.py`)

Desktop automation via Xvfb + VNC inside a computer-use container:

- **`computer_use_screenshot`** — capture the desktop as base64
- **`computer_use_action`** — mouse clicks, keyboard input, scrolling by coordinates

Commands go through a `computer-use-bridge` helper script.

### File tools (`file_tools.py`)

Three ungated tools for file operations inside containers:

- **`sandbox_read`** — read a file with line numbers, optional offset/limit for large files
- **`sandbox_write`** — write a file (base64-encoded transport to avoid escaping issues), creates parent dirs
- **`sandbox_ls`** — list directory contents or find files by glob pattern

## Docker Images

Dockerfiles live in `sandbox/images/`. Each image bundles its bridge script:

- `cli.Dockerfile` — bash shell with common tools
- `browser.Dockerfile` — headless Chromium + Playwright + `playwright_bridge.py`
- `computer_use.Dockerfile` — Xvfb + VNC + `computer_use_bridge.py`
