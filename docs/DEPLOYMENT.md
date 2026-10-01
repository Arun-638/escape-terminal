# 🚀 ESCAPE THE TERMINAL — Production LAN Deployment Guide

**Zero-Cost (₹0), Self-Hosted Linux Escape-Room Competition Platform**

---

## 1. System Requirements

### Hardware Requirements
| Resource | Minimum (20 Teams) | Recommended (40 Teams) |
| :--- | :--- | :--- |
| **CPU** | 4 Cores (x86_64) | 8 Cores (x86_64) |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 30 GB SSD | 50 GB NVMe / SSD |
| **Network** | Gigabit Ethernet (1 Gbps) | Gigabit Ethernet switch (Cat6) |

> **Cost:** ₹0. The entire stack runs on any spare college lab desktop or laptop acting as the LAN server.

### Operating System
- **Recommended:** Ubuntu Server 22.04 LTS or 24.04 LTS
- **Alternative:** Debian 12 Bookworm, Arch Linux, Fedora Server

---

## 2. Prerequisites Installation

Run on the host machine:

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker Engine and Docker Compose Plugin
sudo apt install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable Docker service and grant current user permissions
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

---

## 3. Host Kernel Tuning for High Concurrency

When running 40+ simultaneous isolated containers and multiplexed WebSockets, increase Linux file descriptor and connection limits:

```bash
sudo tee -a /etc/sysctl.conf << 'EOF'
# Escape The Terminal Kernel Optimization
fs.file-max = 2097152
vm.max_map_count = 262144
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.ip_local_port_range = 10240 65535
EOF

sudo sysctl -p
```

---

## 4. College LAN Network Configuration

1. Connect the host server to the competition network switch via Gigabit Ethernet.
2. Assign a static IP address to the server (e.g. `192.168.1.100`):

```bash
# Check your interface name
ip a

# Edit netplan configuration (Ubuntu)
sudo nano /etc/netplan/01-netcfg.yaml
```

Example Netplan configuration:
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
```

Apply netplan:
```bash
sudo netplan apply
```

---

## 5. Clone and Launch Stack

```bash
# 1. Clone or copy repository to host
git clone <repo-url> /opt/escape-the-terminal
cd /opt/escape-the-terminal

# 2. Run automated setup script
chmod +x scripts/*.sh
./scripts/setup.sh

# 3. Configure environment variables (if customizing defaults)
cp .env.example .env
nano .env

# 4. Start the production stack
./scripts/start.sh
```

---

## 6. Port Allocations & Services

All traffic is unified through **Nginx Reverse Proxy on Port 80**:

| Service | Internal Port | External Path / URL |
| :--- | :--- | :--- |
| **Nginx Ingress** | `80` | `http://192.168.1.100/` |
| **CTFd Platform** | `8000` | `http://192.168.1.100/challenges` |
| **Web Terminal UI** | `8080` | `http://192.168.1.100/terminal` |
| **Live Scoreboard** | `8080` | `http://192.168.1.100/scoreboard` |
| **Admin Controls** | `8080` | `http://192.168.1.100/admin` |
| **PostgreSQL 16** | `5432` | Internal Docker Network only |
| **Redis 7** | `6379` | Internal Docker Network only |
| **Team Sandboxes** | None (PTY) | Multiplexed via WebSockets (`/ws/terminal/{id}`) |

---

## 7. Verification & Health Check

```bash
# 1. Inspect running containers
docker compose -f docker/docker-compose.yml ps

# 2. Check terminal microservice health
curl -s http://192.168.1.100/health | jq .

# Expected output:
# {
#   "status": "healthy",
#   "app": "Escape The Terminal Service",
#   "docker_connected": true,
#   "active_sessions": 0
# }

# 3. Check CTFd responsiveness
curl -I http://192.168.1.100/
# HTTP/1.1 200 OK
```

---

## 8. Backup & Restore Runbook

### Creating Backups
```bash
# Takes a timestamped snapshot of PostgreSQL database and CTFd uploads
./scripts/backup.sh
# Output saved to: backups/escape_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Restoring from Backup
```bash
# Restore from a backup archive
./scripts/restore.sh backups/escape_backup_YYYYMMDD_HHMMSS.sql.gz
```
