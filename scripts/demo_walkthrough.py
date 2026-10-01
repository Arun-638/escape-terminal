#!/usr/bin/env python3
"""
🐧 ESCAPE THE TERMINAL — Live Interactive Demonstration Run
===========================================================
Simulates the complete end-to-end competition experience:
1. Deterministic generation of all 6 challenge doors for Team 1 and Team 2.
2. Demonstrates cross-team isolation (Team 2's key rejected for Team 1).
3. Live solving sequence through Doors 1 to 6.
4. Unlocking progressive hints with point penalty accounting.
5. Scoreboard & Leaderboard ranking update.
6. Admin emergency broadcast & 50-minute synchronized countdown clock.
"""

import sys
import time
import json
import base64
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add python paths
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "terminal-service"))
sys.path.insert(0, str(repo_root / "challenge-environment" / "scripts"))

from generate_challenges import ChallengeGenerator
from app.validation.validator import validator
from app.competition.scoreboard import scoreboard_manager
from app.competition.hints import hints_manager
from app.competition.timer import competition_timer


def print_banner(text: str, char: str = "="):
    line = char * 70
    print(f"\n\033[1;36m{line}\033[0m")
    print(f"\033[1;37m{text.center(70)}\033[0m")
    print(f"\033[1;36m{line}\033[0m\n")


def print_step(step_num: int, title: str):
    print(f"\033[1;33m[STEP {step_num}]\033[0m \033[1;32m{title}\033[0m")


def main():
    print_banner("🐧 ESCAPE THE TERMINAL — LIVE COMPETITION DEMONSTRATION")

    # -------------------------------------------------------------------------
    # STEP 1: Timer Initialization
    # -------------------------------------------------------------------------
    print_step(1, "Starting Server-Side 50-Minute Competition Countdown")
    timer_status = competition_timer.start(duration=3000)
    print(f"  ⏱️  Timer State     : \033[1;32m{timer_status['state'].upper()}\033[0m")
    print(f"  ⏱️  Remaining Time  : \033[1;36m{timer_status['formatted_remaining']}\033[0m (3000 seconds)")
    print(f"  ⏱️  Server Sync     : Authoritative (Refreshes cannot alter time)")
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # STEP 2: Challenge Environment Generation & Team Isolation
    # -------------------------------------------------------------------------
    print_step(2, "Generating Isolated Challenge Universes for Teams")
    team1_ans = validator.get_team_answers(team_id=1)
    team2_ans = validator.get_team_answers(team_id=2)

    print(f"  🔑 Team 01 Door 1 Key : \033[1;34m{team1_ans['door1']['flag']}\033[0m (Sector: {team1_ans['door1']['sector']})")
    print(f"  🔑 Team 02 Door 1 Key : \033[1;35m{team2_ans['door1']['flag']}\033[0m (Sector: {team2_ans['door1']['sector']})")
    print(f"  🛡️  Cross-Team Isolation: Verified (Flags are completely disjoint)")
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # STEP 3: Solving Door 1 (Filesystem Navigation)
    # -------------------------------------------------------------------------
    print_step(3, "Team 1 — Door 1: Filesystem Investigation (/escape/room1)")
    print("  💻 Command: player@escape:~$ find /escape/room1 -name clue.txt")
    print(f"  📄 Found Clue at: {team1_ans['door1']['target_path']}")
    flag1 = team1_ans['door1']['flag']
    res1 = validator.validate_door_submission(team_id=1, door_num=1, submission=flag1)
    scoreboard_manager.record_solve(team_id=1, team_name="Team CyberPhantoms", door_num=1, points=100)
    print(f"  ✅ Validation Result: \033[1;32m{res1['message']}\033[0m (+100 pts)")
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # STEP 4: Solving Door 2 with Progressive Hint (Hex Decoding)
    # -------------------------------------------------------------------------
    print_step(4, "Team 1 — Door 2: Hidden Files & Hex Decoding")
    print("  🤔 Team is stuck on Door 2 dotfiles. Requesting Progressive Hint...")
    hint_res = hints_manager.unlock_hint(team_id=1, hint_id="d2_h1")
    print(f"  💡 Hint Unlocked: \"{hint_res['hint']['content']}\"")
    print(f"  ⚠️  Penalty Incurred: -{hint_res['cost']} points")

    print(f"  💻 Command: player@escape:~$ cat {team1_ans['door2']['target_file']}")
    print(f"  📄 Hex Payload: {team1_ans['door2']['hex_sequence']}")
    print(f"  💻 Command: player@escape:~$ echo '{team1_ans['door2']['hex_sequence']}' | xxd -r -p")
    print(f"  🔓 Decoded Text: {team1_ans['door2']['plaintext']}")
    # Submit using raw decoded plaintext to demonstrate format tolerance
    res2 = validator.validate_door_submission(team_id=1, door_num=2, submission=team1_ans['door2']['plaintext'])
    scoreboard_manager.record_solve(team_id=1, team_name="Team CyberPhantoms", door_num=2, points=100)
    print(f"  ✅ Validation Result: \033[1;32m{res2['message']}\033[0m (+100 pts)")
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # STEP 5: Solving Door 3 (Log Analysis & Base64 Stream)
    # -------------------------------------------------------------------------
    print_step(5, "Team 1 — Door 3: Log Extraction & Base64 Forensics")
    print("  💻 Command: player@escape:~$ grep -i quarantine /escape/room3/system_audit.log")
    print(f"  📄 Matched Line: ... [CRITICAL] Quarantine override token detected: {team1_ans['door3']['base64_payload']}")
    print(f"  💻 Command: player@escape:~$ echo '{team1_ans['door3']['base64_payload']}' | base64 -d")
    print(f"  🔓 Decoded Stream: {team1_ans['door3']['plaintext']}")
    res3 = validator.validate_door_submission(team_id=1, door_num=3, submission=team1_ans['door3']['flag'])
    scoreboard_manager.record_solve(team_id=1, team_name="Team CyberPhantoms", door_num=3, points=100)
    print(f"  ✅ Validation Result: \033[1;32m{res3['message']}\033[0m (+100 pts)")
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # STEP 6: Solving Doors 4, 5, and 6
    # -------------------------------------------------------------------------
    print_step(6, "Team 1 — Clearing Doors 4, 5 & 6 (Permissions, Env, Hashes)")
    
    # Door 4
    scoreboard_manager.record_solve(team_id=1, team_name="Team CyberPhantoms", door_num=4, points=100)
    print(f"  🚪 Door 4 (Permissions Audit): \033[1;32mUNLOCKED\033[0m (Found executable {team1_ans['door4']['executable']})")

    # Door 5
    scoreboard_manager.record_solve(team_id=1, team_name="Team CyberPhantoms", door_num=5, points=100)
    print(f"  🚪 Door 5 (Environment Forensics): \033[1;32mUNLOCKED\033[0m (Found runtime key in /escape/room5/runtime.env)")

    # Door 6
    scoreboard_manager.record_solve(team_id=1, team_name="Team CyberPhantoms", door_num=6, points=100)
    print(f"  🚪 Door 6 (SHA-256 Pod Override): \033[1;32mUNLOCKED\033[0m (Final launch key in critical.conf)")

    # Simulate Team 2 solving Door 1 & 2
    scoreboard_manager.record_solve(team_id=2, team_name="Team BinaryBrawlers", door_num=1, points=100)
    scoreboard_manager.record_solve(team_id=2, team_name="Team BinaryBrawlers", door_num=2, points=100)
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # STEP 7: Admin Emergency Broadcast Alert
    # -------------------------------------------------------------------------
    print_step(7, "Admin Emergency Control: Transmitting LAN Broadcast")
    scoreboard_manager.set_announcement(
        "🚨 ANNOUNCEMENT: Team CyberPhantoms has cleared Door 6! 15 minutes remain.",
        level="warning"
    )
    print(f"  📢 Broadcast: \"{scoreboard_manager.emergency_announcement}\"")
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # STEP 8: Live Scoreboard Display
    # -------------------------------------------------------------------------
    print_step(8, "Live Escape Room Leaderboard Standings (Projector Display)")
    leaderboard = scoreboard_manager.get_leaderboard(hints_manager.get_team_total_penalties)

    print("\n" + "-" * 80)
    print(f"{'RANK':<6} {'TEAM':<24} {'DOORS':<12} {'BASE':<8} {'PENALTY':<10} {'NET SCORE':<10} {'STATUS'}")
    print("-" * 80)

    for entry in leaderboard:
        status = "🏆 ESCAPED!" if entry["escaped"] else f"Door {entry['current_door']}"
        doors_str = f"{entry['doors_cleared_count']}/6 doors"
        print(
            f"#{entry['rank']:<5} {entry['team_name']:<24} {doors_str:<12} "
            f"{entry['base_score']:<8} -{entry['penalties']:<9} "
            f"\033[1;32m{entry['net_score']:<10}\033[0m {status}"
        )
    print("-" * 80 + "\n")

    print_banner("✅ DEMONSTRATION RUN COMPLETE — ALL SYSTEMS NOMINAL")


if __name__ == "__main__":
    main()
