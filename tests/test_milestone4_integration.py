"""
Milestone 4 Verification Test Suite: CTFd Integration & Team Context Binding
============================================================================
Validates:
1. Custom plugin registration and loading in CTFd.
2. Authentication enforcement: unauthenticated users redirected to login.
3. Team membership requirement: users without a team redirected to team setup.
4. Team-to-Container context binding:
   - Team 01 -> escape-team-01
   - Team 02 -> escape-team-02
5. Derivation of identity strictly from authenticated session context (anti-IDOR).
6. Plugin API endpoint (/api/v1/escape/team-status) correctness.
"""

import sys
from pathlib import Path

# Add ctfd to Python path
ctfd_root = Path(__file__).resolve().parent.parent / "ctfd"
sys.path.insert(0, str(ctfd_root))

import pytest
from CTFd.models import Users, Teams
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    register_user,
    login_as_user,
)


@pytest.fixture(scope="module")
def ctf_app():
    """Create and configure CTFd with escape_terminal plugin loaded."""
    from tests.helpers import setup_ctfd
    from CTFd.plugins.escape_terminal import load as load_escape_plugin

    app = create_ctfd(
        setup=False,
        user_mode="teams",
    )
    # Register plugin before first request is handled
    load_escape_plugin(app)

    # Now execute CTFd setup
    setup_ctfd(
        app,
        ctf_name="🐧 ESCAPE THE TERMINAL",
        ctf_description="Zero-Cost Self-Hosted Linux Escape Room",
        name="admin",
        email="admin@escapetheterminal.lan",
        password="AdminSecurePassword123!",
        user_mode="teams",
    )
    yield app
    destroy_ctfd(app)


def test_01_plugin_registered(ctf_app):
    """Verify that escape_terminal blueprint and routes are registered."""
    rules = [rule.rule for rule in ctf_app.url_map.iter_rules()]
    assert "/terminal" in rules, "Route /terminal was not registered by plugin!"
    assert "/api/v1/escape/team-status" in rules, "Route /api/v1/escape/team-status was not registered!"
    print("\n[VERIFIED] 1. Escape Terminal CTFd plugin is active and routes are mapped.")


def test_02_unauthenticated_access_redirect(ctf_app):
    """Verify that unauthenticated access to /terminal redirects to login."""
    with ctf_app.test_client() as client:
        res = client.get("/terminal")
        assert res.status_code == 302
        assert "/login" in res.headers.get("Location", "")
    print("[VERIFIED] 2. Unauthenticated requests are redirected to /login.")


def test_03_authenticated_user_without_team(ctf_app):
    """Verify that a user without a team is redirected to team management."""
    with ctf_app.app_context():
        register_user(ctf_app, name="solo_player", email="solo@college.lan", password="SoloPassword123!")
        with login_as_user(ctf_app, name="solo_player", password="SoloPassword123!") as client:
            res = client.get("/terminal")
            assert res.status_code == 302
            assert "/team" in res.headers.get("Location", "")
    print("[VERIFIED] 3. Users without a team are redirected to team management.")


def test_04_team_context_binding(ctf_app):
    """
    Verify authenticated team members receive access to their specific sandbox.
    Team 01 -> escape-team-01
    Team 02 -> escape-team-02
    """
    with ctf_app.app_context():
        # Setup Team 01
        register_user(ctf_app, name="t1_player", email="t1@college.lan", password="T1Password123!")
        with login_as_user(ctf_app, name="t1_player", password="T1Password123!") as client:
            client.get("/teams/new")
            with client.session_transaction() as sess:
                data = {
                    "name": "Team 01 Alpha",
                    "password": "AlphaPassword123!",
                    "nonce": sess.get("nonce"),
                }
            client.post("/teams/new", data=data)

        # Setup Team 02
        register_user(ctf_app, name="t2_player", email="t2@college.lan", password="T2Password123!")
        with login_as_user(ctf_app, name="t2_player", password="T2Password123!") as client:
            client.get("/teams/new")
            with client.session_transaction() as sess:
                data = {
                    "name": "Team 02 Beta",
                    "password": "BetaPassword123!",
                    "nonce": sess.get("nonce"),
                }
            client.post("/teams/new", data=data)

        team1 = Teams.query.filter_by(name="Team 01 Alpha").first()
        team2 = Teams.query.filter_by(name="Team 02 Beta").first()
        assert team1 is not None and team2 is not None

        # Verify Team 01 player gets Team 01 container context
        with login_as_user(ctf_app, name="t1_player", password="T1Password123!") as client:
            res = client.get("/terminal")
            assert res.status_code == 200
            html = res.get_data(as_text=True)
            assert f"escape-team-{team1.id:02d}" in html
            assert team1.name in html

            # Verify API returns correct container name
            api_res = client.get("/api/v1/escape/team-status")
            assert api_res.status_code == 200
            json_data = api_res.get_json()["data"]
            assert json_data["team_id"] == team1.id
            assert json_data["container_name"] == f"escape-team-{team1.id:02d}"

        # Verify Team 02 player gets Team 02 container context
        with login_as_user(ctf_app, name="t2_player", password="T2Password123!") as client:
            res = client.get("/terminal")
            assert res.status_code == 200
            html = res.get_data(as_text=True)
            assert f"escape-team-{team2.id:02d}" in html
            assert team2.name in html

            api_res = client.get("/api/v1/escape/team-status")
            assert api_res.status_code == 200
            json_data = api_res.get_json()["data"]
            assert json_data["team_id"] == team2.id
            assert json_data["container_name"] == f"escape-team-{team2.id:02d}"

    print("[VERIFIED] 4. Team-to-Container context binding verified for Team 01 & Team 02.")


def test_05_anti_idor_session_authority(ctf_app):
    """
    Verify identity cannot be spoofed via client request parameters.
    The identity is derived exclusively from CTFd server-side session.
    """
    with ctf_app.app_context():
        team1 = Teams.query.filter_by(name="Team 01 Alpha").first()
        team2 = Teams.query.filter_by(name="Team 02 Beta").first()

        # Team 1 player tries passing team=2 in query parameters
        with login_as_user(ctf_app, name="t1_player", password="T1Password123!") as client:
            res = client.get(f"/terminal?team={team2.id}")
            assert res.status_code == 200
            html = res.get_data(as_text=True)
            # Must STILL bind to team 1, completely ignoring client override
            assert f"escape-team-{team1.id:02d}" in html
            assert f"escape-team-{team2.id:02d}" not in html
    print("[VERIFIED] 5. Anti-IDOR server-side authority verified (query overrides ignored).")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
