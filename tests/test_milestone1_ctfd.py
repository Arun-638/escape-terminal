"""
Milestone 1 Verification Test Suite: CTFd Foundation
=====================================================
Validates all requirements for Milestone 1:
1. CTFd initialization & startup
2. Admin login and permissions
3. Player user registration
4. Team creation and member association
5. Challenge and flag creation
6. Challenge solving & scoring
7. Leaderboard and scoreboard verification
"""

import sys
from pathlib import Path

# Add ctfd to Python path
ctfd_root = Path(__file__).resolve().parent.parent / "ctfd"
sys.path.insert(0, str(ctfd_root))

import pytest
from CTFd.models import Users, Teams, Challenges, Flags, Solves
from CTFd.utils.scores import get_standings
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    register_user,
    login_as_user,
    gen_challenge,
    gen_flag,
)


@pytest.fixture(scope="module")
def ctf_app():
    """Create and configure a clean CTFd instance in team mode."""
    app = create_ctfd(
        ctf_name="🐧 ESCAPE THE TERMINAL",
        ctf_description="Zero-Cost Self-Hosted Linux Escape Room",
        name="admin",
        email="admin@escapetheterminal.lan",
        password="AdminSecurePassword123!",
        user_mode="teams",
    )
    yield app
    destroy_ctfd(app)


def test_01_ctfd_starts(ctf_app):
    """Confirm CTFd starts and serves index page."""
    with ctf_app.app_context():
        with ctf_app.test_client() as client:
            res = client.get("/")
            assert res.status_code in (200, 302), f"Unexpected status: {res.status_code}"
            assert ctf_app.name == "CTFd"
    print("\n[VERIFIED] 1. CTFd starts successfully and responds to HTTP requests")


def test_02_admin_login(ctf_app):
    """Confirm admin authentication and privileges."""
    with ctf_app.app_context():
        with login_as_user(ctf_app, name="admin", password="AdminSecurePassword123!") as client:
            res = client.get("/admin")
            assert res.status_code in (200, 302)
            admin_user = Users.query.filter_by(name="admin").first()
            assert admin_user is not None
            assert admin_user.type == "admin"
            assert admin_user.email == "admin@escapetheterminal.lan"
    print("[VERIFIED] 2. Admin login works and admin privileges are confirmed")


def test_03_player_registration(ctf_app):
    """Confirm player registration works for participants."""
    with ctf_app.app_context():
        register_user(ctf_app, name="alice", email="alice@college.lan", password="AlicePassword123!")
        register_user(ctf_app, name="bob", email="bob@college.lan", password="BobPassword123!")
        register_user(ctf_app, name="charlie", email="charlie@college.lan", password="CharliePassword123!")

        alice = Users.query.filter_by(name="alice").first()
        bob = Users.query.filter_by(name="bob").first()
        charlie = Users.query.filter_by(name="charlie").first()

        assert alice is not None and alice.type == "user"
        assert bob is not None and bob.type == "user"
        assert charlie is not None and charlie.type == "user"
    print("[VERIFIED] 3. Player registration works (Alice, Bob, Charlie registered)")


def test_04_team_creation(ctf_app):
    """Confirm team creation and player team assignment."""
    with ctf_app.app_context():
        # Alice creates Team 01 via CTFd interface
        with login_as_user(ctf_app, name="alice", password="AlicePassword123!") as client:
            client.get("/teams/new")
            with client.session_transaction() as sess:
                data = {
                    "name": "Team 01 - Kernel Panic",
                    "password": "TeamPassword123!",
                    "nonce": sess.get("nonce"),
                }
            res = client.post("/teams/new", data=data)
            assert res.status_code in (200, 302)

        team1 = Teams.query.filter_by(name="Team 01 - Kernel Panic").first()
        assert team1 is not None

        # Charlie creates Team 02 via CTFd interface
        with login_as_user(ctf_app, name="charlie", password="CharliePassword123!") as client:
            client.get("/teams/new")
            with client.session_transaction() as sess:
                data = {
                    "name": "Team 02 - Ctrl Alt Elite",
                    "password": "TeamPassword456!",
                    "nonce": sess.get("nonce"),
                }
            res = client.post("/teams/new", data=data)
            assert res.status_code in (200, 302)

        team2 = Teams.query.filter_by(name="Team 02 - Ctrl Alt Elite").first()
        assert team2 is not None

        # Add Bob to Team 01 (verifying multi-user team association)
        bob = Users.query.filter_by(name="bob").first()
        bob.team_id = team1.id
        team1.members.append(bob)
        ctf_app.db.session.commit()

        # Verify team members
        alice = Users.query.filter_by(name="alice").first()
        assert alice.team_id == team1.id
        assert bob.team_id == team1.id
        assert len(team1.members) == 2
        assert len(team2.members) == 1
    print("[VERIFIED] 4. Team creation works (Team 01 with Alice & Bob, Team 02 with Charlie)")


def test_05_challenge_creation(ctf_app):
    """Confirm challenge creation works."""
    with ctf_app.app_context():
        # Create Door 1 and Door 2 challenges
        chal1 = gen_challenge(
            ctf_app.db,
            name="Door 1 — Filesystem Investigation",
            description="Investigate the compromised Linux filesystem and find the hidden emergency clue.",
            value=100,
            category="Linux Escape",
            state="visible",
        )
        gen_flag(
            ctf_app.db,
            challenge_id=chal1.id,
            content="ESCAPE{DOOR1_SECTOR_C_UNLOCKED}",
        )

        chal2 = gen_challenge(
            ctf_app.db,
            name="Door 2 — Hidden Files",
            description="Inspect hidden dotfiles to recover the security token.",
            value=125,
            category="Linux Escape",
            state="visible",
        )
        gen_flag(
            ctf_app.db,
            challenge_id=chal2.id,
            content="ESCAPE{DOOR2_HEX_TOKEN_SOLVED}",
        )

        challenges = Challenges.query.all()
        flags = Flags.query.all()
        assert len(challenges) >= 2
        assert len(flags) >= 2
    print("[VERIFIED] 5. Challenge creation works (Door 1: 100 pts, Door 2: 125 pts)")


def test_06_scoring_and_solving(ctf_app):
    """Confirm challenge solving and team score calculation."""
    with ctf_app.app_context():
        chal1 = Challenges.query.filter_by(name="Door 1 — Filesystem Investigation").first()
        team1 = Teams.query.filter_by(name="Team 01 - Kernel Panic").first()

        # Alice solves Door 1 for Team 01 using official CTFd client
        with login_as_user(ctf_app, name="alice", password="AlicePassword123!") as client:
            res = client.post(
                "/api/v1/challenges/attempt",
                json={
                    "challenge_id": chal1.id,
                    "submission": "ESCAPE{DOOR1_SECTOR_C_UNLOCKED}",
                },
            )
            assert res.status_code == 200
            data = res.get_json()
            assert data["data"]["status"] == "correct"

        # Check solve recorded in DB
        solve = Solves.query.filter_by(challenge_id=chal1.id, team_id=team1.id).first()
        assert solve is not None
        assert team1.score == 100
    print("[VERIFIED] 6. Scoring works (Team 01 solved Door 1, earned 100 points)")


def test_07_leaderboard(ctf_app):
    """Confirm leaderboard rankings and scoreboard API."""
    with ctf_app.app_context():
        standings = get_standings(count=10, admin=True)
        assert len(standings) >= 1
        assert standings[0].name == "Team 01 - Kernel Panic"
        assert standings[0].score == 100

        with ctf_app.test_client() as client:
            res = client.get("/api/v1/scoreboard")
            assert res.status_code == 200
            data = res.get_json()
            assert len(data["data"]) >= 1
            assert data["data"][0]["name"] == "Team 01 - Kernel Panic"
            assert data["data"][0]["score"] == 100
            assert data["data"][0]["pos"] == 1
    print("[VERIFIED] 7. Leaderboard works (Team 01 ranked #1 with 100 points on Scoreboard)")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
