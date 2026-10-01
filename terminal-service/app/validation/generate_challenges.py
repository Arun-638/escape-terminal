#!/usr/bin/env python3
"""
ESCAPE THE TERMINAL — Deterministic Challenge Filesystem Generator
=================================================================
Generates team-isolated, randomized challenge filesystems based on
deterministic HMAC-SHA256 seeding.

Supported Doors (Full Suite 1 to 6):
- Door 1: Filesystem Investigation (find, cd, ls, cat)
- Door 2: Hidden Files & Hexadecimal Decoding (ls -la, xxd, python)
- Door 3: Log Extraction & Base64 Stream Forensics (grep, base64)
- Door 4: Linux File Permissions & Executables (ls -l, permissions audit)
- Door 5: Process & Environment Forensics (env, printenv, procfs)
- Door 6: Forensic Timestamp & SHA-256 Checksum Audit (ls -lt, sha256sum)
"""

import os
import sys
import hmac
import hashlib
import random
import json
import base64
import argparse
from pathlib import Path


def derive_team_seed(team_id: int, competition_id: str = "escape2026", server_secret: str = "escape_master_secret_lan") -> int:
    """
    Derive a deterministic 64-bit integer seed from server secret, competition ID, and team ID.
    Formula: HMAC-SHA256(server_secret, competition_id + ":" + team_id)
    """
    message = f"{competition_id}:{team_id}".encode("utf-8")
    key = server_secret.encode("utf-8")
    digest = hmac.new(key, message, hashlib.sha256).digest()
    seed = int.from_bytes(digest[:8], byteorder="big")
    return seed


class ChallengeGenerator:
    def __init__(self, team_id: int, root_dir: Path, server_secret: str = "escape_master_secret_lan", competition_id: str = "escape2026", write_files: bool = True):
        self.team_id = team_id
        self.root_dir = Path(root_dir)
        self.home_dir = self.root_dir / "home" / "player"
        self.escape_dir = self.root_dir / "escape"
        self.seed = derive_team_seed(team_id, competition_id, server_secret)
        self.rng = random.Random(self.seed)
        self.answers = {}
        self.write_files = write_files

    def init_directories(self):
        """Create base directory tree."""
        if not self.write_files:
            return

        self.home_dir.mkdir(parents=True, exist_ok=True)
        self.escape_dir.mkdir(parents=True, exist_ok=True)

        for d in ["documents", "downloads", "logs", "old", "tmp"]:
            (self.home_dir / d).mkdir(parents=True, exist_ok=True)

    def generate_door_1(self):
        """
        DOOR 1 — Filesystem Investigation
        Learning objectives: pwd, ls, cd, find, cat
        """
        sectors = ["sector-alpha", "sector-beta", "sector-gamma", "sector-delta", "sector-omega"]
        self.rng.shuffle(sectors)
        target_sector = sectors[0]
        decoy_sectors = sectors[1:]

        d1_hex = self.rng.randbytes(4).hex().upper()
        door1_flag = f"ESCAPE{{DOOR1_SECTOR_{d1_hex}}}"
        self.answers["door1"] = {
            "flag": door1_flag,
            "target_path": f"/escape/room1/{target_sector}/clue.txt",
            "sector": target_sector
        }

        if not self.write_files:
            return

        readme_content = (
            "=====================================================\n"
            "🚨 EMERGENCY LOCKDOWN INITIATED — SECURITY LEVEL 1 🚨\n"
            "=====================================================\n\n"
            "System administrator notice:\n"
            "All terminal exits are sealed. The filesystem integrity has been\n"
            "partitioned into security isolation sectors under '/escape'.\n\n"
            "To unlock Door 1, you must investigate the server sectors,\n"
            "locate the emergency maintenance clue, and submit the verification key.\n\n"
            "HINT: Standard filesystem exploration tools (ls, cd, find, cat)\n"
            "will help you navigate deeper system partitions.\n\n"
            "— Emergency Operations Terminal\n"
        )
        (self.home_dir / "README.txt").write_text(readme_content, encoding="utf-8")

        room1_dir = self.escape_dir / "room1"
        room1_dir.mkdir(parents=True, exist_ok=True)

        target_path = room1_dir / target_sector
        target_path.mkdir(parents=True, exist_ok=True)
        (target_path / "clue.txt").write_text(
            f"=== DOOR 1 EMERGENCY BYPASS CODE ===\n"
            f"SECTOR IDENTIFIER: {target_sector}\n"
            f"ACCESS KEY: {door1_flag}\n\n"
            f"Submit this key to unlock Door 2.\n",
            encoding="utf-8"
        )

        for sector in decoy_sectors:
            sec_path = room1_dir / sector
            sec_path.mkdir(parents=True, exist_ok=True)
            (sec_path / "status.txt").write_text(f"Node: {sector}. Status: DEACTIVATED.\n", encoding="utf-8")

    def generate_door_2(self):
        """
        DOOR 2 — Hidden Files & Hex Decoding
        Learning objectives: ls -la, hidden dotfiles, hex decoding
        """
        word_pool = ["OVERRIDE", "SECURITY", "PROTOCOL", "FIREWALL", "TERMINAL", "GATEWAY", "CIPHER"]
        target_word = self.rng.choice(word_pool)
        target_number = self.rng.randint(100, 999)
        door2_plaintext = f"{target_word}-{target_number}"
        
        hex_sequence = " ".join(f"{b:02X}" for b in door2_plaintext.encode("utf-8"))
        door2_flag = f"ESCAPE{{DOOR2_{door2_plaintext}}}"

        hidden_files = [".room", ".secret", ".cache", ".config", ".secret_message", ".sysdata"]
        self.rng.shuffle(hidden_files)
        target_hidden_file = hidden_files[0]
        decoy_hidden_files = hidden_files[1:]

        self.answers["door2"] = {
            "flag": door2_flag,
            "plaintext": door2_plaintext,
            "hex_sequence": hex_sequence,
            "target_file": f"/home/player/{target_hidden_file}"
        }

        if not self.write_files:
            return

        target_path = self.home_dir / target_hidden_file
        target_path.write_text(
            f"# LOCKDOWN BYPASS FRAGMENT — DOOR 2\n"
            f"# DECODE HEXADECIMAL SEQUENCE TO OBTAIN PASSPHRASE:\n"
            f"{hex_sequence}\n"
            f"# FORMAT: Submit ESCAPE{{DOOR2_<DECODED_TEXT>}} to unlock Door 3.\n",
            encoding="utf-8"
        )

        for i, decoy in enumerate(decoy_hidden_files):
            decoy_path = self.home_dir / decoy
            decoy_path.write_text(f"# Expired Cache Segment #{i+1}\n", encoding="utf-8")

    def generate_door_3(self):
        """
        DOOR 3 — Log Extraction & Base64 Stream Forensics
        Learning objectives: grep, pipes, base64 decoding
        """
        d3_token = self.rng.randbytes(5).hex().upper()
        d3_plaintext = f"STREAM-AUDIT-{d3_token}"
        b64_payload = base64.b64encode(d3_plaintext.encode("utf-8")).decode("utf-8")
        door3_flag = f"ESCAPE{{DOOR3_{d3_plaintext}}}"

        self.answers["door3"] = {
            "flag": door3_flag,
            "plaintext": d3_plaintext,
            "base64_payload": b64_payload,
            "target_file": "/escape/room3/system_audit.log"
        }

        if not self.write_files:
            return

        room3_dir = self.escape_dir / "room3"
        room3_dir.mkdir(parents=True, exist_ok=True)

        # Generate realistic multi-line audit log with 1 target alert
        log_lines = []
        components = ["sshd", "kernel", "systemd", "cron", "dockerd", "authd"]
        for i in range(1, 101):
            comp = self.rng.choice(components)
            pid = self.rng.randint(100, 4000)
            if i == 47:
                # Target alert line
                log_lines.append(
                    f"2026-10-01 10:14:{i%60:02d} escape-core {comp}[{pid}]: [CRITICAL] Quarantine override token detected: {b64_payload}"
                )
            else:
                log_lines.append(
                    f"2026-10-01 10:14:{i%60:02d} escape-core {comp}[{pid}]: [INFO] Normal transaction heartbeat verified"
                )

        (room3_dir / "system_audit.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    def generate_door_4(self):
        """
        DOOR 4 — Linux File Permissions Audit
        Learning objectives: ls -l, permissions (0755 vs 0644), running executables
        """
        d4_token = self.rng.randbytes(4).hex().upper()
        door4_flag = f"ESCAPE{{DOOR4_EXEC_{d4_token}}}"

        bin_names = ["net_sync", "disk_probe", "key_emitter", "firewall_ctl", "mem_alloc", "log_rotate", "sensor_read"]
        self.rng.shuffle(bin_names)
        target_bin = bin_names[0]
        decoys = bin_names[1:]

        self.answers["door4"] = {
            "flag": door4_flag,
            "token": d4_token,
            "executable": f"/escape/room4/bin/{target_bin}"
        }

        if not self.write_files:
            return

        bin_dir = self.escape_dir / "room4" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        # Write executable target script
        target_script = bin_dir / target_bin
        script_code = f"#!/bin/bash\necho '=== DOOR 4 GENERATION COMPLETE ==='\necho 'ACCESS KEY: {door4_flag}'\n"
        target_script.write_text(script_code, encoding="utf-8")
        try:
            os.chmod(target_script, 0o755)
        except Exception:
            pass

        # Write non-executable decoys
        for d in decoys:
            decoy_script = bin_dir / d
            decoy_script.write_text("#!/bin/bash\necho 'Decoy utility: Permission denied'\n", encoding="utf-8")
            try:
                os.chmod(decoy_script, 0o644)
            except Exception:
                pass

    def generate_door_5(self):
        """
        DOOR 5 — Process & Environment Forensics
        Learning objectives: env, export, configuration parsing
        """
        d5_token = self.rng.randbytes(6).hex().upper()
        door5_flag = f"ESCAPE{{DOOR5_ENV_{d5_token}}}"

        self.answers["door5"] = {
            "flag": door5_flag,
            "token": d5_token,
            "target_file": "/escape/room5/runtime.env"
        }

        if not self.write_files:
            return

        room5_dir = self.escape_dir / "room5"
        room5_dir.mkdir(parents=True, exist_ok=True)

        env_lines = [
            "# Escape Environment Runtime Config",
            "ESCAPE_MODE=STRICT",
            "ESCAPE_NODE=CLUSTER_LAN_01",
            f"ESCAPE_CHAMBER_KEY={door5_flag}",
            "DEBUG=FALSE",
            "COMPETITION_SEASON=2026"
        ]
        (room5_dir / "runtime.env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    def generate_door_6(self):
        """
        DOOR 6 — Forensic Timestamp & SHA-256 Checksum Audit
        Learning objectives: ls -lt, find -mtime, sha256sum
        """
        d6_token = self.rng.randbytes(6).hex().upper()
        door6_flag = f"ESCAPE{{DOOR6_HASH_{d6_token}}}"

        self.answers["door6"] = {
            "flag": door6_flag,
            "token": d6_token,
            "target_file": "/escape/room6/critical.conf"
        }

        if not self.write_files:
            return

        room6_dir = self.escape_dir / "room6"
        room6_dir.mkdir(parents=True, exist_ok=True)

        # Write 10 decoy config files
        for i in range(1, 11):
            (room6_dir / f"service_{i:02d}.conf").write_text(f"service_id={i}\nstatus=verified\n", encoding="utf-8")

        # Write target critical configuration with the final key
        (room6_dir / "critical.conf").write_text(
            f"=== ESCAPE POD CONTROL OVERRIDE ===\n"
            f"POD_STATUS: READY FOR LAUNCH\n"
            f"FINAL_FLAG: {door6_flag}\n",
            encoding="utf-8"
        )

    def write_answers(self, output_path: Path):
        """Write metadata / answers to a secure file outside player reach."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "team_id": self.team_id,
                "seed": self.seed,
                "answers": self.answers
            }, f, indent=2)

    def generate_all(self, answers_file: Path = None):
        """Execute complete filesystem generation for Doors 1 through 6."""
        self.init_directories()
        self.generate_door_1()
        self.generate_door_2()
        self.generate_door_3()
        self.generate_door_4()
        self.generate_door_5()
        self.generate_door_6()
        if answers_file:
            self.write_answers(answers_file)
        return self.answers


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic escape room filesystem for a team.")
    parser.add_argument("--team-id", type=int, required=True, help="CTFd Team ID (integer)")
    parser.add_argument("--root-dir", type=str, default="/", help="Root directory to generate files into")
    parser.add_argument("--secret", type=str, default="escape_master_secret_lan", help="Server master secret")
    parser.add_argument("--answers-file", type=str, default=None, help="Path to write JSON answer metadata")
    args = parser.parse_args()

    generator = ChallengeGenerator(
        team_id=args.team_id,
        root_dir=Path(args.root_dir),
        server_secret=args.secret
    )
    answers = generator.generate_all(answers_file=Path(args.answers_file) if args.answers_file else None)
    print(json.dumps(answers, indent=2))


if __name__ == "__main__":
    main()
