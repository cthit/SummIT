from flask import Blueprint, render_template, request, redirect, url_for, flash, g, send_file, abort
from datetime import date
from .auth import login_required, login_as_admin_required
from .data_handler import LP, StudyPeriod, create_meeting, fetch_meetings, lookup_study_period, create_study_period, upload_document, DocumentOwner, DocumentType, fetch_documents_for_meeting

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
    
    meetings = fetch_meetings()
    selected_id = request.args.get("meeting_id", type=int)
    selected_meeting = next((m for m in meetings if m.id == selected_id), None)
    label = _meeting_label(selected_meeting) if selected_meeting else ""
    
    # Fetch documents if a meeting is selected
    documents_by_owner = {}
    owner_names = {user["id"]: "My Documents"}
    if selected_meeting:
        group_ids = [g.get("id") for g in user.get("groups", [])]
        documents_by_owner = fetch_documents_for_meeting(selected_meeting.id, user["id"], group_ids)
        # Create mapping of group IDs to prettyNames
        for group in user.get("groups", []):
            owner_names[group["id"]] = group["prettyName"]
    
    return render_template(
        "doc.html",
        user=user,
        meetings=meetings,
        selected_meeting=selected_meeting,
        label=label,
        documents_by_owner=documents_by_owner,
        owner_names=owner_names,
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
        meetings = fetch_meetings()
        selected_id = request.args.get("meeting_id", type=int)
        selected_meeting = next((m for m in meetings if m.id == selected_id), None)
        return render_template("upload.html", meetings=meetings, selected_meeting=selected_meeting, user=g.user)
    
    uploaded_file = request.files.get("file")
    meeting_id = request.form.get("meeting_id", type=int)
    document_type_str = request.form.get("document_type")
    owner_id = request.form.get("owner_id")
    
    if not uploaded_file:
        flash("No file selected.", "error")
        meetings = fetch_meetings()
        return render_template("upload.html", meetings=meetings, user=g.user)
    if not meeting_id:
        flash("Please select a meeting.", "error")
        meetings = fetch_meetings()
        return render_template("upload.html", meetings=meetings, selected_meeting=None, user=g.user)
    if not owner_id:
        flash("Please select who to upload as.", "error")
        meetings = fetch_meetings()
        selected_meeting = next((m for m in meetings if m.id == meeting_id), None)
        return render_template("upload.html", meetings=meetings, selected_meeting=selected_meeting, user=g.user)
    
    try:
        document_type = DocumentType(document_type_str)
    except ValueError:
        flash("Please select a document type.", "error")
        meetings = fetch_meetings()
        selected_meeting = next((m for m in meetings if m.id == meeting_id), None)
        return render_template("upload.html", meetings=meetings, selected_meeting=selected_meeting, user=g.user)
    
    # Determine the actual owner ID (self or group)
    if owner_id == "self":
        actual_owner_id = g.user["id"]
        is_group = False
    else:
        actual_owner_id = owner_id
        is_group = True
    
    upload_document(
        uploaded_file.stream.read(),
        uploaded_file.filename,
        DocumentOwner(actual_owner_id),
        meeting_id,
        document_type,
        is_group
    )
    flash("Document uploaded successfully.", "success")
    return redirect(url_for("main.doc"))

@main.route("/documents/download/<int:document_id>")
@login_required
def download_document(document_id):
    from .data_handler import fetch_document_by_id
    user = g.get("user")
    group_ids = [g.get("id") for g in user.get("groups", [])]
    all_owner_ids = [user["id"]] + group_ids
    
    doc = fetch_document_by_id(document_id, all_owner_ids)
    if not doc:
        abort(404)
    
    return send_file(doc["file_path"], as_attachment=True, download_name=doc["name"])
