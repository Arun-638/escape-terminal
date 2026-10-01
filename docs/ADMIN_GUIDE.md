# 🛡️ ESCAPE THE TERMINAL — Competition Administrator Guide

**Complete Operational Manual for LAN Event Organizers & System Administrators**

---

## 1. Quick Access URLs

| Interface | URL | Purpose |
| :--- | :--- | :--- |
| **Admin Control Center** | `http://<SERVER_IP>/admin` | Master timer, broadcast alerts, sandbox resets |
| **CTFd Admin Panel** | `http://<SERVER_IP>/admin` | CTFd challenge/user configuration |
| **Live Scoreboard** | `http://<SERVER_IP>/scoreboard` | Projector display with door progression |
| **Terminal Sandbox** | `http://<SERVER_IP>/terminal` | Participant terminal console |

---

## 2. Pre-Event Initialization (T-24h to T-2h)

### Step 1: Initialize CTFd Admin Account
1. Open `http://<SERVER_IP>/` in your browser.
2. Complete the setup wizard:
   - **CTF Name:** `🐧 ESCAPE THE TERMINAL`
   - **CTF Type:** `Teams`
   - **Admin Username:** `admin`
   - **Admin Password:** Strong administrator password.

### Step 2: Provision Competition Teams
Use the automated team provisioning utility to create team accounts with random secure passwords:

```bash
# Generate 30 competition teams with print-ready credentials table
python3 scripts/create_test_teams.py --teams 30 --print-table
```

*Example Output:*
```
+--------+----------------------+--------------------+-------------------+---------------+
| Team ID| Team Name            | Username           | Email             | Password      |
+--------+----------------------+--------------------+-------------------+---------------+
| 1      | Team CyberPhantoms   | cyberphantoms      | t01@escape.lan    | W3lc0me!T01   |
| 2      | Team BinaryBrawlers  | binarybrawlers     | t02@escape.lan    | K3rn3l!T02    |
| ...    | ...                  | ...                | ...               | ...           |
+--------+----------------------+--------------------+-------------------+---------------+
```
*Print or cut credential slips to distribute to team captains at registration.*

### Step 3: Projector / Big Screen Setup
1. Connect the lab projector or auditorium screen to the host or an organizer laptop.
2. Open `http://<SERVER_IP>/scoreboard`.
3. Press **F11** to toggle Fullscreen mode.
4. Verify the 6 door columns and live timer countdown banner are clearly visible.

---

## 3. Running the Competition (T-0 to T+50m)

### Starting the Countdown
1. In the **Admin Control Center** (`/admin`), click **▶ Start 50m**.
2. All participant terminal screens and the main scoreboard will simultaneously begin the synchronized 50-minute countdown.

### Emergency Controls
- **Pause Competition:** Click **⏸ Pause** (e.g. for emergency announcement or room briefing).
- **Resume Competition:** Click **⏯ Resume**.
- **Adjust Time:** Click **+5 Min** or **-5 Min** if technical delays require extra time.
- **Transmit Alert:** Type an announcement in the text field and click **🚨 Broadcast Alert** to flash a high-visibility red banner across all player terminals and the scoreboard.

### Resolving Team Sandbox Issues
If a participant accidentally wipes their shell environment, runs an infinite loop, or requests a fresh environment:
1. In `/admin`, find the team in the **Team Sandbox Supervision** table.
2. Click **🔄 Hard Reset Sandbox**.
3. The container is terminated, cleanly recreated, and reseeded within 1.5 seconds.
4. Solved progress on CTFd is **not** lost; only the container's temporary filesystem is restored.

---

## 4. Post-Competition Procedures

### Concluding the Event
1. Once the timer reaches `00:00`, the platform enters `finished` state.
2. Take a screenshot or export final standings from `/scoreboard`.
3. Run container cleanup to safely free system resources:

```bash
./scripts/cleanup_containers.sh
```

### Exporting and Backing Up Results
```bash
./scripts/backup.sh
```
All scores, solve timestamps, and user accounts are compressed into `backups/`.
