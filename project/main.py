from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from datetime import date
from .auth import login_required, login_as_admin_required
from .data_handler import LP, StudyPeriod, create_meeting, fetch_meetings, lookup_study_period, create_study_period, upload_document, DocumentOwner

def _meeting_label(meeting):
    lp_int = int(meeting.study_period.lp)
    lp_label = "Summer" if lp_int == 5 else f"Study Period {lp_int}"
    return f"{meeting.date} - {lp_label}"

main = Blueprint("main", __name__)

#meetings = ["2024 LP4", "2025 LP1", "2025 LP2", "2025 LP3"] -- legacy code

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

    meetings = fetch_meetings()
    selected_id = request.args.get("meeting_id", type=int)
    selected_meeting = next((m for m in meetings if m.id == selected_id), None)
    label = _meeting_label(selected_meeting) if selected_meeting else ""

    return render_template(
        "doc.html",
        user=user,
        user_roles=user_roles,
        meetings=meetings,
        selected_meeting=selected_meeting,
        label=label,
    )


@main.route("/admin")
@login_as_admin_required
def admin():
    years = list(range(date.today().year - 1, date.today().year + 2))
    lps = [(lp.value, lp.name) for lp in LP]
    current_year = date.today().year
    return render_template("admin.html", years=years, lps=lps, current_year=current_year, meetings=fetch_meetings())


@main.route("/admin/create-meeting", methods=["POST"])
@login_as_admin_required
def admin_create_meeting():
    meeting_date_str = request.form.get("meeting_date")
    year_str = request.form.get("year")
    lp_str = request.form.get("lp")

    if not meeting_date_str or not year_str or not lp_str:
        flash("All fields are required.", "error")
        return redirect(url_for("main.admin"))

    try:
        y = int(year_str)
        lp = LP(int(lp_str))
        meeting_date = date.fromisoformat(meeting_date_str)
    except Exception:
        flash("Invalid input.", "error")
        return redirect(url_for("main.admin"))

    sp = lookup_study_period(y, lp)
    if sp is None:
        sp = create_study_period(y, lp)
        if sp is None:
            flash("Failed to create study period.", "error")
            return redirect(url_for("main.admin"))
        # StudyPeriod was created successfully
        flash(f"Study period {y} {lp.name} created.", "success")

    created = create_meeting(meeting_date, sp)
    flash("Meeting created." if created else "Failed to create meeting.", "success" if created else "error")
    return redirect(url_for("main.admin"))

@main.route("/documents/upload", methods=["POST","GET"])
@login_required
def document_upload():
    if request.method == "GET":
        return render_template("upload.html")
    
    uploaded_file = request.files.get("file")
    if not uploaded_file:
        flash("No file selected.", "error")
        return render_template("upload.html")
    success = upload_document(uploaded_file.stream.read(), uploaded_file.filename, DocumentOwner(g.user["id"]))
    flash("Document uploaded successfully.", "success")
    return redirect(url_for("main.doc"))
