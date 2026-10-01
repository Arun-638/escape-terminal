"""
Escape The Terminal — CTFd Integration Plugin
=============================================
Extends CTFd to bind authenticated teams directly to their isolated Linux sandbox.
Provides:
- /terminal route delivering the browser-based Linux terminal.
- Team validation ensuring only authenticated team members can access their sandbox.
- Team ID to Container binding (Team 27 -> escape-team-27).
- Seamless navigation integration.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from CTFd.utils.user import authed, get_current_user, get_current_team
from CTFd.utils.decorators import authed_only
from CTFd.utils.decorators.modes import require_team_mode
from CTFd.plugins import register_user_page_menu_bar


def load(app):
    register_user_page_menu_bar("🐧 Terminal", "/terminal")

    escape_bp = Blueprint(
        "escape_terminal",
        __name__,
        template_folder="templates",
        static_folder="static",
        url_prefix=""
    )

    @escape_bp.route("/terminal", methods=["GET"])
    @authed_only
    @require_team_mode
    def terminal_view():
        """
        Directly loads the team's terminal sandbox.
        Derives identity strictly from authenticated CTFd session context.
        """
        team = get_current_team()
        if not team:
            flash("Please join or create a team before accessing the Escape Terminal.", "warning")
            return redirect(url_for("teams.private"))

        return render_template("terminal.html", team=team)

    @escape_bp.route("/api/v1/escape/team-status", methods=["GET"])
    @authed_only
    @require_team_mode
    def team_status():
        """API returning authenticated team's sandbox metadata."""
        team = get_current_team()
        if not team:
            return jsonify({"success": False, "error": "No team associated"}), 400

        container_name = f"escape-team-{team.id:02d}"
        return jsonify({
            "success": True,
            "data": {
                "team_id": team.id,
                "team_name": team.name,
                "container_name": container_name,
                "score": team.score,
                "members_count": len(team.members)
            }
        })

    app.register_blueprint(escape_bp)
