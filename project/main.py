from flask import Blueprint, render_template, g

from .auth import login_required, login_as_admin_required

main = Blueprint("main", __name__)

meetings = ["2024 LP4", "2025 LP1", "2025 LP2", "2025 LP3"]


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=g.get("user"))


@main.route("/documents")
@login_required
def doc():
    user = g.get("user")
    user_roles = [
        (group.get("name", ""), group.get("post", ""))
        for group in user.get("groups", [])
        if group.get("post", "") in ["Chairman", "Treasurer"]
    ]
    return render_template(
        "doc.html", user=user, user_roles=user_roles, meetings=meetings
    )


@main.route("/admin")
@login_as_admin_required
def admin():
    return render_template("admin.html")
