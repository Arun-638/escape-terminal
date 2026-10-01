# ==============================================================================
# ESCAPE THE TERMINAL — Team Sandbox Container
# Zero-Cost, Self-Hosted Linux Escape-Room Competition Platform
# ==============================================================================
FROM debian:bookworm-slim

# Avoid prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm-256color

# Install standard Linux utilities required for challenges
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    findutils \
    grep \
    sed \
    gawk \
    xxd \
    file \
    procps \
    nano \
    less \
    python3-minimal \
    && rm -rf /var/lib/apt/lists/*

# Hardening: Strip unnecessary SUID/SGID bits to eliminate privilege escalation risks
RUN find / -xdev -perm /6000 -type f -exec chmod a-s {} \; || true

# Create unprivileged competition player user
RUN groupadd -g 1001 player && \
    useradd -u 1001 -g player -m -d /home/player -s /bin/bash player

# Setup scripts directory
WORKDIR /opt/scripts
COPY scripts/generate_challenges.py /opt/scripts/generate_challenges.py
COPY scripts/entrypoint.sh /opt/scripts/entrypoint.sh
RUN chmod +x /opt/scripts/entrypoint.sh /opt/scripts/generate_challenges.py

# Setup custom player shell environment with banner & prompt
RUN echo 'export PS1="\[\033[01;32m\]player@escape\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "' >> /home/player/.bashrc && \
    echo 'alias ls="ls --color=auto"' >> /home/player/.bashrc && \
    echo 'alias ll="ls -la --color=auto"' >> /home/player/.bashrc && \
    echo 'echo "====================================================="' >> /home/player/.bashrc && \
    echo 'echo "🐧 ESCAPE THE TERMINAL — SESSION ACTIVE"' >> /home/player/.bashrc && \
    echo 'echo "   Emergency Lockdown in Progress. Inspect README.txt"' >> /home/player/.bashrc && \
    echo 'echo "====================================================="' >> /home/player/.bashrc

# Set working directory to player's home
WORKDIR /home/player

ENTRYPOINT ["/opt/scripts/entrypoint.sh"]
CMD ["/bin/bash"]
