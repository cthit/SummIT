import logging

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
from datetime import date, datetime
from pathlib import Path
import os
import io
import zipfile
from werkzeug.utils import secure_filename
from .auth import login_required, login_as_admin_required, is_admin
from .data_handler import (
    LP,
    infer_study_period_from_date,
    create_meeting,
    fetch_meetings,
    lookup_study_period,
    create_study_period,
    upload_document,
    DocumentOwner,
    DocumentType,
    fetch_documents_for_meeting,
    fetch_downloadable_documents_for_meeting,
    DivisionDocumentTypes,
    MeetingDocumentTypes,
    LiberationDocumentTypes,
    get_document_requires,
    set_document_require,
    fetch_document_by_id,
    delete_document,
    delete_meeting_and_documents,
    remove_document_require,
    update_meeting_deadline,
)
from .gamma import GammaService as gs

logger = logging.getLogger(__name__)


# Allowed upload types: extension plus the file signature it must carry
ALLOWED_UPLOAD_TYPES = {".pdf": b"%PDF-"}

_FALLBACK_GROUPS = [
    ("dev-group-id-styrit", "styrit", "styrIT"),
    ("dev-group-id-digit", "digit", "digIT"),
    ("dev-group-id-devit", "devit", "DevIT"),
]


def _meeting_label(meeting):
    lp_int = int(meeting.study_period.lp)
    lp_label = "Summer" if lp_int == 5 else f"Study Period {lp_int}"
    return f"{meeting.date} - {lp_label}"


def _get_groups():
    whitelist_str = os.getenv("ACTIVE_GROUPS_WHITELIST", "").strip()
    whitelist = (
        {group_id.strip() for group_id in whitelist_str.split(",") if group_id.strip()}
        if whitelist_str
        else None
    )

    if not whitelist:
        return _FALLBACK_GROUPS

    try:
        entries = gs.get_all_super_groups()

        if not entries:
            raise ValueError("No super groups returned from Gamma blob endpoint")

        filtered_groups = [
            (
                entry.super_group.id,
                entry.super_group.name,
                entry.super_group.pretty_name,
            )
            for entry in entries
            if entry.super_group.id in whitelist
        ]

        if not filtered_groups:
            available_ids = [entry.super_group.id for entry in entries]
            logger.error(
                "No groups matched whitelist. Available group IDs: %s", available_ids
            )
            raise ValueError("No matching groups found in whitelist")

        return filtered_groups

    except Exception:
        logger.exception("Failed to fetch groups from Gamma")

    logger.warning("Using fallback groups")
    return _FALLBACK_GROUPS


def _get_meeting_form_data():
    groups = _get_groups()
    return {
        "groups": [
            {"id": group_id, "name": group_name, "pretty_name": group_pretty_name}
            for group_id, group_name, group_pretty_name in groups
        ],
        "division_doc_types": [
            document_type for document_type in DivisionDocumentTypes
        ],
    }


def _get_group_id_to_name_map():
    """Create a mapping of group IDs to group names."""
    groups = _get_groups()
    return {group_id: group_name for group_id, group_name, _ in groups}


def _abbreviate_doc_type(doc_type: str) -> str:
    """Abbreviate document type names for file naming."""
    abbrev_map = {
        "kvartal verksamhetsrapport": "kvrapport",
        "kvartal ekonomiskrapport": "kerapport",
        "budget": "budget",
        "verksamhetsplan": "vplan",
        "verksamhetsberattelse": "vberettelse",
        "ekonomiskberattelse": "eberettelse",
    }
    return abbrev_map.get(doc_type.lower(), doc_type[:8])


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


@main.route("/admin/download-meeting/<int:meeting_id>")
@login_as_admin_required
def download_meeting_documents(meeting_id):
    # Get the meeting
    meetings = fetch_meetings()
    meeting = next((m for m in meetings if m.id == meeting_id), None)
    if not meeting:
        abort(404)

    # Get whitelist groups
    whitelist_str = os.getenv("ACTIVE_GROUPS_WHITELIST", "").strip()
    whitelist_group_ids = (
        [id.strip() for id in whitelist_str.split(",") if id.strip()]
        if whitelist_str
        else []
    )

    # Fallback to fallback groups if no whitelist
    if not whitelist_group_ids:
        whitelist_group_ids = [group_id for group_id, _, _ in _FALLBACK_GROUPS]

    # Fetch downloadable documents
    documents = fetch_downloadable_documents_for_meeting(
        meeting_id, whitelist_group_ids
    )

    if not documents:
        flash("No documents have been uploaded for this meeting yet.", "error")
        return redirect(url_for("main.admin"))

    # Create zip file
    group_id_to_name = _get_group_id_to_name_map()

    # Generate zip filename
    lp_name = (
        "summer" if meeting.study_period.lp == 5 else f"lp{meeting.study_period.lp}"
    )
    date_str = meeting.date.strftime("%Y%m%d")
    zip_filename = f"meeting_{lp_name}_{date_str}.zip"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for doc_id, file_path, owner_id, doc_type, doc_subtype in documents:
            file_obj = file_path
            if isinstance(file_path, str):
                file_obj = file_path
            else:
                file_obj = str(file_path)

            # Generate filename inside zip
            doc_type_abbr = _abbreviate_doc_type(doc_subtype)
            group_name = group_id_to_name.get(owner_id, "unknown").lower()
            year_short = meeting.study_period.year % 100
            filename_inside_zip = f"{doc_type_abbr}_{group_name}{year_short}_{lp_name}_{meeting.study_period.year}"

            # Add file extension
            if Path(file_obj).exists():
                file_ext = Path(file_obj).suffix
                filename_inside_zip += file_ext

                with open(file_obj, "rb") as f:
                    zip_file.writestr(filename_inside_zip, f.read())
            else:
                logger.warning(
                    "Document %s skipped from zip: file missing on disk (%s)",
                    doc_id,
                    file_obj,
                )

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_filename,
    )


@main.route("/admin/meeting-requirements/<int:meeting_id>")
@login_as_admin_required
def get_meeting_requirements_json(meeting_id):
    form_data = _get_meeting_form_data()
    return jsonify(
        {
            "groups": form_data["groups"],
            "doc_types": [
                [dt.value, dt.name.replace("_", " ").title()]
                for dt in form_data["division_doc_types"]
            ],
            "requires": get_document_requires(meeting_id),
        }
    )


@main.route("/admin/infer-study-period")
@login_as_admin_required
def infer_study_period_json():
    """Preview endpoint so the create-meeting form can show the inferred
    study period without duplicating the boundary rules in JS."""
    date_str = request.args.get("date", "")
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    year, lp = infer_study_period_from_date(d)
    label = "Summer" if lp == LP.SUMMER else f"LP{int(lp)}"
    return jsonify({"year": year, "lp": int(lp), "label": f"{label} {year}"})


@main.route("/admin/create-meeting", methods=["GET", "POST"])
@login_as_admin_required
def create_meeting_page():
    form_data = _get_meeting_form_data()

    if request.method == "GET":
        return render_template("create_meeting.html", **form_data, current_requires={})

    meeting_date_str = request.form.get("meeting_date")
    deadline_str = request.form.get("deadline")

    if not meeting_date_str or not deadline_str:
        flash("Meeting date and upload deadline are required.", "error")
        return redirect(url_for("main.admin"))

    try:
        meeting_date = date.fromisoformat(meeting_date_str)
        deadline = datetime.fromisoformat(deadline_str)
    except ValueError:
        flash("Invalid meeting date or deadline.", "error")
        return redirect(url_for("main.admin"))

    if deadline.date() > meeting_date:
        flash("Deadline must be on or before the meeting date.", "error")
        return redirect(url_for("main.admin"))

    # Year and study period are derived from the date (issues #6/#7)
    y, lp = infer_study_period_from_date(meeting_date)

    sp = lookup_study_period(y, lp)
    if sp is None:
        sp = create_study_period(y, lp)
        if sp is None:
            flash("Failed to create study period.", "error")
            return redirect(url_for("main.admin"))

    meeting = create_meeting(meeting_date, sp, deadline)
    if not meeting:
        # create_meeting returns None only on a duplicate meeting date
        flash(f"A meeting already exists on {meeting_date}.", "error")
        return redirect(url_for("main.admin"))

    # Save requirements
    for group in form_data["groups"]:
        for doc_type in DivisionDocumentTypes:
            checkbox_name = f"{group['id']}_{doc_type.value}"
            if request.form.get(checkbox_name):
                set_document_require(meeting.id, group["id"], doc_type.value)

    flash("Meeting created successfully.", "success")
    return redirect(url_for("main.admin"))


def _render_upload_form(meetings=None, selected_meeting=None):
    if meetings is None:
        meetings = fetch_meetings()
    requires = get_document_requires(selected_meeting.id) if selected_meeting else {}
    deadline_passed = bool(
        selected_meeting
        and selected_meeting.deadline
        and datetime.now() > selected_meeting.deadline
    )
    return render_template(
        "upload.html",
        meetings=meetings,
        selected_meeting=selected_meeting,
        user=g.user,
        meeting_doc_types=MeetingDocumentTypes,
        division_doc_types=DivisionDocumentTypes,
        liberation_doc_types=LiberationDocumentTypes,
        requires=requires,
        deadline_passed=deadline_passed,
    )


def _upload_error(message, meetings=None, selected_meeting=None):
    flash(message, "error")
    return _render_upload_form(meetings, selected_meeting)


@main.route("/documents/upload", methods=["POST", "GET"])
@login_required
def document_upload():
    if request.method == "GET":
        meetings = fetch_meetings()
        selected_id = request.args.get("meeting_id", type=int)
        selected_meeting = next((m for m in meetings if m.id == selected_id), None)
        return _render_upload_form(meetings, selected_meeting)

    uploaded_file = request.files.get("file")
    meeting_id = request.form.get("meeting_id", type=int)
    document_type_str = request.form.get("document_type")
    owner_id = request.form.get("owner_id")
    document_subtype_str = (
        request.form.get("meeting_document_subtype")
        if document_type_str == "meeting"
        else (
            request.form.get("liberation_document_subtype")
            if document_type_str == "liberation"
            else request.form.get("division_document_subtype")
        )
    )

    meetings = fetch_meetings()
    selected_meeting = (
        next((m for m in meetings if m.id == meeting_id), None) if meeting_id else None
    )

    if not uploaded_file:
        return _upload_error("No file selected.", meetings, selected_meeting)

    # Meeting is only required for meeting and division documents.
    # Validate that the submitted id refers to a real meeting: a forged or
    # stale id would otherwise crash upload_document further down.
    if document_type_str != "liberation" and not selected_meeting:
        return _upload_error("Please select a valid meeting.", meetings)

    if not owner_id:
        return _upload_error(
            "Please select who to upload as.", meetings, selected_meeting
        )

    try:
        document_type = DocumentType(document_type_str)
    except ValueError:
        return _upload_error(
            "Please select a document type.", meetings, selected_meeting
        )

    # Enforce the upload deadline server-side. Meeting admins may still
    # upload late (e.g. the agenda is finalized after the doc deadline);
    # liberation documents are meeting-independent and unaffected.
    if (
        document_type != DocumentType.LIBERATION
        and selected_meeting.deadline
        and datetime.now() > selected_meeting.deadline
        and not is_admin()
    ):
        return _upload_error(
            "The upload deadline for this meeting has passed.",
            meetings,
            selected_meeting,
        )

    # Validate that personal (self) uploads are only meeting documents
    if owner_id == "self" and document_type != DocumentType.MEETING:
        return _upload_error(
            "You can only upload meeting documents as yourself.",
            meetings,
            selected_meeting,
        )

    # Validate that personal (self) uploads are only motion or other subtypes
    if owner_id == "self" and document_subtype_str not in ["motion", "other"]:
        return _upload_error(
            "You can only upload motions or other documents as yourself.",
            meetings,
            selected_meeting,
        )

    if not document_subtype_str:
        return _upload_error(
            "Please select a document subtype.", meetings, selected_meeting
        )

    # Validate the subtype against the known types - upload_document inserts
    # the value into the *DocumentTypes tables, so a raw form string would
    # let form tampering pollute them.
    subtype_enum = {
        DocumentType.MEETING: MeetingDocumentTypes,
        DocumentType.DIVISION: DivisionDocumentTypes,
        DocumentType.LIBERATION: LiberationDocumentTypes,
    }[document_type]
    try:
        document_subtype = subtype_enum(document_subtype_str)
    except ValueError:
        return _upload_error(
            "Please select a valid document subtype.", meetings, selected_meeting
        )

    # Determine the actual owner ID (self or group). A user may only
    # upload on behalf of groups they are actually a member of - the
    # form value cannot be trusted.
    if owner_id == "self":
        actual_owner_id = g.user["id"]
        is_group = False
    else:
        allowed_group_ids = {grp.get("id") for grp in g.user.get("groups", [])}
        if owner_id not in allowed_group_ids:
            return _upload_error(
                "You are not a member of that group.", meetings, selected_meeting
            )
        actual_owner_id = owner_id
        is_group = True

    # Only PDF files are accepted (#13): check both the extension and the
    # file signature, and sanitize the name before it becomes part of a
    # filesystem path.
    data = uploaded_file.stream.read()
    extension = Path(uploaded_file.filename or "").suffix.lower()
    expected_signature = ALLOWED_UPLOAD_TYPES.get(extension)
    if expected_signature is None or not data.startswith(expected_signature):
        return _upload_error(
            "Only PDF files are allowed.", meetings, selected_meeting
        )
    file_name = secure_filename(uploaded_file.filename) or "document.pdf"

    try:
        upload_document(
            data,
            file_name,
            DocumentOwner(actual_owner_id),
            meeting_id if document_type != DocumentType.LIBERATION else None,
            document_type,
            document_subtype.value,
            is_group,
        )
    except ValueError as e:
        # DuplicateDocumentError and "Meeting does not exist." from
        # upload_document both carry a user-appropriate message
        return _upload_error(str(e), meetings, selected_meeting)
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

    if not Path(doc["file_path"]).is_file():
        logger.error("File missing on disk for document %s", document_id)
        flash(
            "The file for this document is missing on the server. "
            "Please contact the meeting admins.",
            "error",
        )
        return redirect(url_for("main.doc"))

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
        flash(
            "Document not found, or you do not have permission to delete it.",
            "error",
        )

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
        # Update the deadline (an empty field clears it)
        deadline_str = request.form.get("deadline")
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str)
            except ValueError:
                flash("Invalid deadline.", "error")
                return redirect(url_for("main.manage_meeting", meeting_id=meeting_id))
            if deadline.date() > meeting.date:
                flash("Deadline must be on or before the meeting date.", "error")
                return redirect(url_for("main.manage_meeting", meeting_id=meeting_id))
        if not update_meeting_deadline(meeting_id, deadline):
            flash("Failed to update deadline.", "error")
            return redirect(url_for("main.admin"))

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


# @main.route("/admin/mail")
# @login_as_admin_required
# def mail():
#     return render_template("mail.html")
