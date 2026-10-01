# 🐧 ESCAPE THE TERMINAL — Player Briefing & Survival Guide

**College LAN Linux Escape-Room Competition**

---

## 1. Mission Briefing

You and your teammate have been locked inside an isolated Linux server environment under **EMERGENCY QUARANTINE PROTOCOL**.

All network exits are sealed. The system has locked down 6 security containment chambers:

```
[ Door 1 ] ➔ [ Door 2 ] ➔ [ Door 3 ] ➔ [ Door 4 ] ➔ [ Door 5 ] ➔ [ Door 6 ] ➔ 🏆 ESCAPE!
```

You have **50 MINUTES** to investigate the system, bypass security controls, decrypt tokens, and escape the terminal before total system lockdown!

---

## 2. Connecting to the Platform

1. Connect your computer to the competition LAN Ethernet cable or authorized College Wi-Fi.
2. Open your browser (Google Chrome, Firefox, or Brave recommended) and visit:
   ```
   http://192.168.1.100/
   ```
3. Click **Login** and enter your Team Username and Password provided on your credentials slip.
4. Click **💻 Terminal** in the top navigation bar to open your team's live interactive sandbox console.

---

## 3. Terminal Interface & Helpful Shortcuts

Your terminal connects directly into your team's private Linux container (`escape-team-XX`).

| Keybinding | Function |
| :--- | :--- |
| `Ctrl + C` | Cancel a running command or break out of an infinite loop |
| `clear` or `Ctrl + L` | Clear terminal screen |
| `Tab` | Command and filename auto-completion |
| `Up / Down Arrows` | Browse previous shell command history |
| `Ctrl + Shift + V` | Paste text into terminal |

> 💡 **Notice:** Your container is completely isolated. You have standard unprivileged `player` permissions. You do **not** need `root` or `sudo` to solve any challenge.

---

## 4. The 6 Security Escape Doors

### 🚪 Door 1 — Filesystem Investigation
- **Objective:** The filesystem has quarantined sectors mounted under `/escape/room1/`.
- **Skills:** `pwd`, `ls`, `cd`, `cat`, `find`
- **Goal:** Locate the emergency sector maintenance clue and extract the access key (`ESCAPE{DOOR1_SECTOR_...}`).

### 🚪 Door 2 — Hidden Files & Hex Decoding
- **Objective:** System logs indicate dotfiles (`.`) were generated to obscure security keys.
- **Skills:** `ls -la`, `cat`, hexadecimal decoding
- **Helpful Commands:**
  ```bash
  ls -la /home/player
  # Decode hex using python:
  python3 -c "print(bytes.fromhex('<HEX_STRING>').decode())"
  # Or xxd:
  echo "<HEX_STRING>" | xxd -r -p
  ```

### 🚪 Door 3 — Log Extraction & Base64 Stream Forensics
- **Objective:** Sift through system audit logs (`system_audit.log`) to uncover critical anomaly codes.
- **Skills:** `grep`, `tail`, `base64`
- **Helpful Commands:**
  ```bash
  grep -i "quarantine" /escape/room3/system_audit.log
  echo "<BASE64_STRING>" | base64 -d
  ```

### 🚪 Door 4 — File Permissions & Executables
- **Objective:** Multiple script utilities exist in `/escape/room4/bin/`, but only one has executable permissions (`+x`).
- **Skills:** `ls -l`, Linux permission bits (`rwx`), running scripts
- **Helpful Commands:**
  ```bash
  ls -l /escape/room4/bin/
  ./target_utility
  ```

### 🚪 Door 5 — Process & Environment Forensics
- **Objective:** Search environment variables and runtime configurations for the chamber override key.
- **Skills:** `env`, `printenv`, `grep`
- **Helpful Commands:**
  ```bash
  env | grep -i escape
  cat /escape/room5/runtime.env
  ```

### 🚪 Door 6 — Forensic Timestamp & Checksum Audit
- **Objective:** An unauthorized configuration change occurred recently in `/escape/room6/`. Find the altered file and calculate its checksum or extract the final escape pod key.
- **Skills:** `ls -lt`, `sha256sum`, file inspection
- **Helpful Commands:**
  ```bash
  ls -lt /escape/room6/
  sha256sum /escape/room6/<altered_file>
  ```

---

## 5. Submitting Flags & Scoring

- **Flag Format:** Most keys follow `ESCAPE{DOOR<X>_...}`.
- Submissions can be entered via:
  1. The **Submit Solution** prompt in your browser terminal window.
  2. The **CTFd Challenges** portal (`/challenges`).
- **Door Value:** Each solved door awards **100 Points**.
- **Progressive Hints:** If you get stuck, you can unlock tiered hints. Note that unlocking hints deducts points (-15 or -25 points) from your score, so use them strategically!

Good luck, engineers. May the shell be with you! 🐧
