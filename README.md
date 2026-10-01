# 🐧 ESCAPE THE TERMINAL

### CTFd-Based, Zero-Cost, Self-Hosted Linux Escape-Room Competition Platform

A production-ready competition platform built for college technical fests and cybersecurity events. 

- **Engine**: Self-hosted, open-source [CTFd](https://ctfd.io/) 3.8.6
- **Total Cost**: **₹0** (No cloud, no VPS, no paid SaaS)
- **Target Topology**: College LAN (`192.168.x.x`), fully offline operational
- **Target Capacity**: 30–40 concurrent teams (50–60 participants), 50-minute event duration
- **Status**: **100% Production Ready** (All 13 Milestones Complete, 56/56 Tests Passing)

---

## 🚀 Quick Start (Production Server - Ubuntu LAN)

1. Clone or copy the repository onto the competition host machine.
2. Run automated setup:
   ```bash
   chmod +x scripts/*.sh
   ./scripts/setup.sh
   ```
3. Start the services:
   ```bash
   ./scripts/start.sh
   ```
4. Access platform interfaces:
   - **Player Terminal:** `http://<SERVER_IP>/terminal`
   - **Live Scoreboard:** `http://<SERVER_IP>/scoreboard`
   - **Admin Control Center:** `http://<SERVER_IP>/admin`
   - **CTFd Portal:** `http://<SERVER_IP>/challenges`

---

## 📚 Documentation & Manuals

| Document | Description |
| :--- | :--- |
| **[ARCHITECTURE.md](file:///f:/terminal/ARCHITECTURE.md)** | Technical architecture, container sandboxing, data flow, and threat model |
| **[DEVELOPMENT_STATUS.md](file:///f:/terminal/DEVELOPMENT_STATUS.md)** | Milestone completion matrix and automated verification test reports |
| **[DEPLOYMENT.md](file:///f:/terminal/docs/DEPLOYMENT.md)** | Step-by-step production LAN installation, kernel tuning, and Nginx ingress |
| **[ADMIN_GUIDE.md](file:///f:/terminal/docs/ADMIN_GUIDE.md)** | Competition manager handbook: timer, broadcasts, container resets, backups |
| **[PLAYER_GUIDE.md](file:///f:/terminal/docs/PLAYER_GUIDE.md)** | Participant briefing, the 6 escape doors, shortcuts, and scoring |
| **[SECURITY.md](file:///f:/terminal/docs/SECURITY.md)** | Security hardening, least-privilege, network isolation, and rate limiting |
| **[EVENT_DAY_CHECKLIST.md](file:///f:/terminal/docs/EVENT_DAY_CHECKLIST.md)** | T-24h to post-event operational checklist for the organizing committee |

---

## 🧪 Automated Test Verification

Run the full verification test suite across all 13 milestones:

```bash
pytest tests/ -v
```
*Result: 56 passed in 16.55s (100% pass rate).*
