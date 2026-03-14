FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    wget \
    jq \
    git \
    python3 \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Playwright + Chromium
RUN pip3 install --break-system-packages playwright \
    && playwright install --with-deps chromium

# Bridge script that accepts JSON commands and drives Playwright
COPY playwright_bridge.py /usr/local/bin/playwright-bridge
RUN chmod +x /usr/local/bin/playwright-bridge

RUN useradd -m -s /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox

CMD ["sleep", "infinity"]
