# 📋 ESCAPE THE TERMINAL — Event-Day Operational Checklist

**Organizer Runbook from T-24 Hours to Post-Event Teardown**

---

## 🕒 T-24 Hours (Preparation & Staging)

- [ ] **Host Machine Ready:** Ubuntu Server 22.04/24.04 LTS updated with Gigabit Ethernet port.
- [ ] **Docker Pre-Warmed:** Base images pulled (`docker pull debian:bookworm-slim`, `postgres:16-alpine`, `redis:7-alpine`, `nginx:1.27-alpine`).
- [ ] **Challenge Image Built:** `docker build -t escape-challenge:latest challenge-environment/`.
- [ ] **Kernel Parameters Applied:** `sysctl -p` verified (`fs.file-max`, `net.core.somaxconn`).
- [ ] **Fresh Backup Taken:** Run `./scripts/backup.sh`.
- [ ] **Test Suite Run:** Execute `pytest tests/ -q` (Verify all 56 tests pass).

---

## 🕒 T-3 Hours (Lab & Network Setup)

- [ ] **Switch Setup:** Connect the 24/48-port Gigabit switch. Connect the host server via Cat6 cable.
- [ ] **Static IP Bound:** Verify host responds at `http://192.168.1.100`.
- [ ] **DHCP / Subnet Verification:** Connect a test laptop and ensure it receives an IP in `192.168.1.x/24`.
- [ ] **Stack Startup:** Run `./scripts/start.sh` and inspect health endpoint:
  ```bash
  curl -s http://192.168.1.100/health
  ```
- [ ] **Team Accounts Provisioned:** Run `python3 scripts/create_test_teams.py --teams 35 --print-table`.
- [ ] **Credentials Printed:** Print or cut out team username/password slips.

---

## 🕒 T-1 Hour (Projector & Room Readiness)

- [ ] **Projector Connection:** Connect host or coordinator laptop to main lab projector.
- [ ] **Scoreboard Displayed:** Open `http://192.168.1.100/scoreboard` in Google Chrome and press **F11**.
- [ ] **Admin Console Open:** Open `http://192.168.1.100/admin` on the lead organizer's laptop.
- [ ] **Timer Reset:** Verify timer displays `50:00 (not_started)`.

---

## 🕒 T-15 Minutes (Participant Seating & Briefing)

- [ ] **Distribute Credentials:** Hand out credential slips to registered team captains.
- [ ] **Network Check:** Instruct all participants to connect to the LAN and navigate to `http://192.168.1.100`.
- [ ] **Briefing:** Deliver 3-minute oral briefing using `docs/PLAYER_GUIDE.md`:
  - 6 Doors, 50 minutes duration.
  - Non-root environment (no `sudo` required).
  - Progressive hints deduct points (-15 / -25 pts).
  - Team resets available on request via organizers.

---

## 🕒 T-0 (Kickoff & Live Operation)

- [ ] **Start Master Timer:** In `/admin`, click **▶ Start 50m**.
- [ ] **Verify Scoreboard Sync:** Confirm scoreboard and all team screens display active countdown.
- [ ] **T+15m Checkpoint:** Check `/admin` for any teams requesting sandbox resets.
- [ ] **T+30m Checkpoint:** Check leading team on scoreboard.
- [ ] **T+45m (5-Min Warning):** Send broadcast: `🚨 5 MINUTES REMAINING! Wrap up all Door submissions!`
- [ ] **T+50m (Lockdown):** Timer reaches `00:00`. Competition state transitions to `finished`.

---

## 🕒 T+Post-Event (Wrap Up & Teardown)

- [ ] **Capture Final Standings:** Screenshot the `/scoreboard` podium (1st, 2nd, 3rd place).
- [ ] **Export Database:** Run `./scripts/backup.sh`.
- [ ] **Stop & Prune Sandboxes:** Run `./scripts/cleanup_containers.sh`.
- [ ] **Stop Services:** Run `./scripts/stop.sh`.
