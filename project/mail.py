from datetime import date

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    url_for,
)

from .auth import login_as_admin_required
from .data_handler import (
    fetch_meeting,
    get_document_requires,
    get_missing_liberation_documents,
    has_sent_mail,
    record_sent_mail,
)
from .mail_handler import send_mail_config
from .gamma import GammaService as gs


mail = Blueprint("mail", __name__)


def _super_group_map() -> dict[str, tuple[str, str]]:
    """id -> (name, pretty_name) for all super-groups.

    One blob fetch per request - get_super_group() re-downloads the whole
    blob per call.
    """
    return {
        entry.super_group.id: (
            entry.super_group.name,
            entry.super_group.pretty_name,
        )
        for entry in gs.get_all_super_groups()
    }


@mail.route("/admin/mail/send/<int:meeting_id>", methods=["POST"])
@login_as_admin_required
def send_mail_route(meeting_id):
    meeting_obj = fetch_meeting(meeting_id)
    if meeting_obj is None:
        flash("Meeting not found.", "error")
        return redirect(url_for("main.admin"))

    doc_req = get_document_requires(meeting_id)
    if not doc_req:
        flash("This meeting has no document requirements - no mail sent.", "error")
        return redirect(url_for("main.admin"))

    try:
        groups = _super_group_map()
    except Exception:
        current_app.logger.exception("Could not fetch groups from Gamma")
        flash("Could not fetch groups from Gamma - no mail sent.", "error")
        return redirect(url_for("main.admin"))

    lp = meeting_obj.study_period.lp
    year = meeting_obj.study_period.year
    deadline = meeting_obj.deadline

    sent = 0
    skipped = 0
    for group_id, requirements in doc_req.items():
        if group_id not in groups:
            current_app.logger.warning(
                "Group %s unknown to Gamma; announcement skipped", group_id
            )
            skipped += 1
            continue
        name, pretty_name = groups[group_id]
        vars = {
            "group_name": pretty_name,
            "task_list": requirements,
            "meeting_date": meeting_obj.date,
            "deadline_date": deadline.strftime("%Y-%m-%d") if deadline else "TBD",
            "deadline_time": deadline.strftime("%H:%M") if deadline else "",
        }

        try:
            send_mail_config(
                [f"{name}@chalmers.it"],
                f"Meeting Announcement {"Summer" if lp == 5 else f"lp{lp}"} {year}",
                "meeting_announcement.txt",
                vars,
            )
        except Exception:
            current_app.logger.exception("Announcement mail to %s failed", name)
            flash(
                f"Failed to send announcement to {pretty_name}. "
                "Check that the mail service is running.",
                "error",
            )
            return redirect(url_for("main.admin"))
        sent += 1

    if skipped:
        flash(f"{skipped} group(s) were unknown to Gamma and skipped.", "error")
    flash(f"Announcement mail sent to {sent} group(s).", "success")
    return redirect(url_for("main.admin"))


@mail.route("/admin/mail/liberation", methods=["POST"])
@login_as_admin_required
def send_liberation_mail_route():
    """Mail each whitelisted group its missing duty liberation documents.

    Manual admin trigger; deduped per calendar year via SentMails, so it is
    safe to press the button twice and re-sends automatically next year.
    """
    # Imported here to avoid an import cycle at module load
    from .main import _get_groups

    groups = _get_groups()
    missing = get_missing_liberation_documents()

    mail_type = f"duty_retirement_{date.today().year}"
    sent = 0
    for group_id, group_name, pretty_name in groups:
        task_list = missing.get(group_id)
        if not task_list:
            continue
        if has_sent_mail(mail_type, None, group_id):
            continue
        try:
            send_mail_config(
                [f"{group_name}@chalmers.it"],
                f"Duty liberation documents {date.today().year}",
                "duty_retirement.txt",
                {"group_name": pretty_name, "task_list": task_list},
            )
        except Exception:
            current_app.logger.exception("Liberation mail to %s failed", group_name)
            flash(f"Failed to send liberation mail to {pretty_name}.", "error")
            return redirect(url_for("main.admin"))
        record_sent_mail(mail_type, None, group_id)
        sent += 1

    if sent:
        flash(f"Liberation reminder sent to {sent} group(s).", "success")
    else:
        flash(
            "No liberation reminders to send - nothing missing, or already "
            "sent this year.",
            "success",
        )
    return redirect(url_for("main.admin"))
