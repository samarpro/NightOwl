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
    xvfb \
    x11vnc \
    xdotool \
    imagemagick \
    scrot \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pyautogui pillow

# Bridge script that accepts JSON commands and drives xdotool/scrot
COPY computer_use_bridge.py /usr/local/bin/computer-use-bridge
RUN chmod +x /usr/local/bin/computer-use-bridge

# Start Xvfb + VNC on container boot
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /root

ENV DISPLAY=:99

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
