from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
    send_file,
    abort,
    jsonify,
)
from datetime import date
import os
from .auth import login_required, login_as_admin_required
from .data_handler import (
    LP,
    StudyPeriod,
    create_meeting,
    fetch_meetings,
    lookup_study_period,
    create_study_period,
    upload_document,
    DocumentOwner,
    DocumentType,
    fetch_documents_for_meeting,
    DivisionDocumentTypes,
    get_document_requires,
    set_document_require,
    fetch_document_by_id,
    delete_document,
    delete_meeting_and_documents,
    remove_document_require,
)
from .gamma import GammaService as gs


_FALLBACK_GROUPS = [
    {"id": "dev-group-id-styrit", "name": "styrIT"},
    {"id": "dev-group-id-digit", "name": "digIT"},
    {"id": "dev-group-id-devit", "name": "DevIT"},
]


def _meeting_label(meeting):
    lp_int = int(meeting.study_period.lp)
    lp_label = "Summer" if lp_int == 5 else f"Study Period {lp_int}"
    return f"{meeting.date} - {lp_label}"


def _get_groups():
    whitelist_str = os.getenv("ACTIVE_GROUPS_WHITELIST", "").strip()
    whitelist = {group.strip() for group in whitelist_str.split(",") if group.strip()} if whitelist_str else None
    
    if not whitelist:
        return _FALLBACK_GROUPS
    
    try:
        return [group for group in gs.get_all_super_groups() if group.id in whitelist]

    except Exception as exc:
        print(f"Failed to fetch groups from Gamma: {exc}")
    
    return _FALLBACK_GROUPS
 

def _get_meeting_form_data():
    return {
        "years": list(range(date.today().year - 1, date.today().year + 3)),
        "lps": [(lp.value, lp.name) for lp in LP],
        "current_year": date.today().year,
        "groups": _get_groups(),
        "division_doc_types": [(dt.value, dt.name) for dt in DivisionDocumentTypes],
    }


main = Blueprint("main", __name__)


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
        documents_by_owner = fetch_documents_for_meeting(
            selected_meeting.id, user["id"], group_ids
        )
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
    return render_template("admin.html", meetings=fetch_meetings())


@main.route("/admin/meeting-requirements/<int:meeting_id>")
@login_as_admin_required
def get_meeting_requirements_json(meeting_id):
    form_data = _get_meeting_form_data()
    return jsonify(
        {
            "groups": form_data["groups"],
            "doc_types": form_data["division_doc_types"],
            "requires": get_document_requires(meeting_id),
        }
    )


@main.route("/admin/create-meeting", methods=["GET", "POST"])
@login_as_admin_required
def create_meeting_page():
    form_data = _get_meeting_form_data()

    if request.method == "GET":
        return render_template("create_meeting.html", **form_data, current_requires={})

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

    meeting = create_meeting(meeting_date, sp)
    if not meeting:
        flash("Failed to create meeting.", "error")
        return redirect(url_for("main.admin"))

    # Save requirements
    for group in form_data["groups"]:
        for doc_type in DivisionDocumentTypes:
            checkbox_name = f"{group['id']}_{doc_type.value}"
            if request.form.get(checkbox_name):
                set_document_require(meeting.id, group["id"], doc_type.value)

    flash("Meeting created successfully.", "success")
    return redirect(url_for("main.admin"))


@main.route("/documents/upload", methods=["POST", "GET"])
@login_required
def document_upload():
    if request.method == "GET":
        meetings = fetch_meetings()
        selected_id = request.args.get("meeting_id", type=int)
        selected_meeting = next((m for m in meetings if m.id == selected_id), None)
        return render_template(
            "upload.html",
            meetings=meetings,
            selected_meeting=selected_meeting,
            user=g.user,
        )

    uploaded_file = request.files.get("file")
    meeting_id = request.form.get("meeting_id", type=int)
    document_type_str = request.form.get("document_type")
    owner_id = request.form.get("owner_id")
    document_subtype_str = (
        request.form.get("meeting_document_subtype")
        if document_type_str == "meeting"
        else request.form.get("division_document_subtype")
    )

    if not uploaded_file:
        flash("No file selected.", "error")
        meetings = fetch_meetings()
        return render_template("upload.html", meetings=meetings, user=g.user)
    if not meeting_id:
        flash("Please select a meeting.", "error")
        meetings = fetch_meetings()
        return render_template(
            "upload.html", meetings=meetings, selected_meeting=None, user=g.user
        )
    if not owner_id:
        flash("Please select who to upload as.", "error")
        meetings = fetch_meetings()
        selected_meeting = next((m for m in meetings if m.id == meeting_id), None)
        return render_template(
            "upload.html",
            meetings=meetings,
            selected_meeting=selected_meeting,
            user=g.user,
        )

    try:
        document_type = DocumentType(document_type_str)
    except ValueError:
        flash("Please select a document type.", "error")
        meetings = fetch_meetings()
        selected_meeting = next((m for m in meetings if m.id == meeting_id), None)
        return render_template(
            "upload.html",
            meetings=meetings,
            selected_meeting=selected_meeting,
            user=g.user,
        )

    if not document_subtype_str:
        flash("Please select a document subtype.", "error")
        meetings = fetch_meetings()
        selected_meeting = next((m for m in meetings if m.id == meeting_id), None)
        return render_template(
            "upload.html",
            meetings=meetings,
            selected_meeting=selected_meeting,
            user=g.user,
        )

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
        document_subtype_str,
        is_group,
    )
    flash("Document uploaded successfully.", "success")
    return redirect(url_for("main.doc"))


@main.route("/documents/download/<int:document_id>")
@login_required
def download_document(document_id):
    user = g.get("user")
    group_ids = [g.get("id") for g in user.get("groups", [])]
    all_owner_ids = [user["id"]] + group_ids

    doc = fetch_document_by_id(document_id, all_owner_ids)
    if not doc:
        abort(404)

    return send_file(doc["file_path"], as_attachment=True, download_name=doc["name"])


@main.route("/documents/delete/<int:document_id>")
@login_required
def delete_document_view(document_id):
    user = g.get("user")
    group_ids = [g.get("id") for g in user.get("groups", [])]
    all_owner_ids = [user["id"]] + group_ids

    success = delete_document(document_id, all_owner_ids)
    if success:
        flash("Document deleted successfully.", "success")
    else:
        flash("Failed to delete document.", "error")

    return redirect(url_for("main.doc"))


@main.route("/admin/delete-meeting/<int:meeting_id>")
@login_as_admin_required
def delete_meeting(meeting_id):
    success = delete_meeting_and_documents(meeting_id)
    if success:
        flash("Meeting and associated documents deleted successfully.", "success")
    else:
        flash("Failed to delete meeting.", "error")

    return redirect(url_for("main.admin"))


@main.route("/admin/manage-meeting/<int:meeting_id>", methods=["GET", "POST"])
@login_as_admin_required
def manage_meeting(meeting_id):
    meetings = fetch_meetings()
    meeting = next((m for m in meetings if m.id == meeting_id), None)
    if not meeting:
        flash("Meeting not found.", "error")
        return redirect(url_for("main.admin"))

    form_data = _get_meeting_form_data()

    if request.method == "POST":
        # Clear all requirements for this meeting first
        existing = get_document_requires(meeting_id)
        for group_id, doc_types in existing.items():
            for doc_type in doc_types:
                remove_document_require(meeting_id, group_id, doc_type)

        # Add new requirements from form
        for group in form_data["groups"]:
            for doc_type in DivisionDocumentTypes:
                checkbox_name = f"{group['id']}_{doc_type.value}"
                if request.form.get(checkbox_name):
                    set_document_require(meeting_id, group["id"], doc_type.value)

        flash("Meeting updated successfully.", "success")
        return redirect(url_for("main.admin"))

    # GET request - show form
    current_requires = get_document_requires(meeting_id)

    return render_template(
        "create_meeting.html",
        meeting=meeting,
        **form_data,
        current_requires=current_requires,
    )


@main.route("/admin/mail")
@login_as_admin_required
def mail():
    return render_template("mail.html")
