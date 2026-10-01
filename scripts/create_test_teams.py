#!/usr/bin/env python3
"""
ESCAPE THE TERMINAL — Test Team Generator
=========================================
Generates competition teams in CTFd and provisions their deterministic challenge state.
Usage:
    python scripts/create_test_teams.py --teams 10
    python scripts/create_test_teams.py --count 30 --print-table
"""

import sys
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add paths
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "ctfd"))
sys.path.insert(0, str(repo_root / "challenge-environment" / "scripts"))

from CTFd import create_app
from CTFd.models import db, Users, Teams, Configs
from CTFd.utils.config import is_setup
from CTFd.utils import set_config
from generate_challenges import ChallengeGenerator


def create_teams(count: int = 10, default_password: str = "EscapePass123!", print_table: bool = True):
    app = create_app()
    with app.app_context():
        # Ensure database tables exist
        db.create_all()

        # If CTFd hasn't been set up yet, perform initial minimal setup automatically
        if not is_setup():
            print("[*] CTFd is not set up yet. Initializing basic competition config...")
            set_config("ctf_name", "🐧 ESCAPE THE TERMINAL")
            set_config("ctf_description", "Zero-Cost College LAN Linux Escape Room")
            set_config("user_mode", "teams")
            set_config("setup", "true")

            # Create default admin if missing
            admin_user = Users.query.filter_by(type="admin").first()
            if not admin_user:
                admin_user = Users(name="admin", email="admin@escape.lan", password="AdminPassword123!", type="admin")
                db.session.add(admin_user)
                db.session.commit()
                print("  [+] Created default Admin account: Username='admin' / Password='AdminPassword123!'")

        print(f"[*] Provisioning {count} competition teams in CTFd database...")
        generated_teams = []

        for i in range(1, count + 1):
            team_name = f"Team {i:02d}"
            captain_name = f"captain_t{i:02d}"
            captain_email = f"captain_t{i:02d}@escape.lan"

            # Check if team already exists
            existing_team = Teams.query.filter_by(name=team_name).first()
            if existing_team:
                team = existing_team
            else:
                # Create captain user
                captain = Users.query.filter_by(name=captain_name).first()
                if not captain:
                    captain = Users(name=captain_name, email=captain_email, password=default_password)
                    db.session.add(captain)
                    db.session.commit()

                # Create team
                team = Teams(name=team_name, password=default_password, captain_id=captain.id)
                team.members.append(captain)
                captain.team_id = team.id
                db.session.add(team)
                db.session.commit()

                # Add teammate
                member_name = f"player_t{i:02d}"
                member_email = f"player_t{i:02d}@escape.lan"
                member = Users(name=member_name, email=member_email, password=default_password, team_id=team.id)
                team.members.append(member)
                db.session.add(member)
                db.session.commit()

            # Derive deterministic puzzle answers for all 6 doors
            generator = ChallengeGenerator(
                team_id=team.id,
                root_dir=Path("/tmp"),
                write_files=False
            )
            generator.generate_all()

            generated_teams.append({
                "team_id": team.id,
                "team_name": team.name,
                "captain": captain_name,
                "password": default_password,
                "door1_flag": generator.answers["door1"]["flag"],
                "door2_flag": generator.answers["door2"]["flag"],
            })

        print(f"[+] Successfully provisioned {len(generated_teams)} teams!")

        if print_table:
            print("\n" + "=" * 90)
            print(f"{'TEAM ID':<8} | {'TEAM NAME':<12} | {'USERNAME / CAPTAIN':<20} | {'PASSWORD':<16} | {'DOOR 1 FLAG'}")
            print("-" * 90)
            for t in generated_teams:
                print(f"Team {t['team_id']:<3} | {t['team_name']:<12} | {t['captain']:<20} | {t['password']:<16} | {t['door1_flag']}")
            print("=" * 90 + "\n")
            print("💡 Tip: Distribute the Username and Password to participants for login.")

        return generated_teams


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate competition test teams.")
    parser.add_argument("--count", "--teams", dest="count", type=int, default=10, help="Number of teams to create")
    parser.add_argument("--password", type=str, default="EscapePass123!", help="Default password for generated teams")
    parser.add_argument("--print-table", action="store_true", default=True, help="Print formatted credentials table")
    args = parser.parse_args()

    create_teams(count=args.count, default_password=args.password, print_table=args.print_table)
