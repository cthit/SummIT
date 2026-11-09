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
from .i18n import t


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
        flash(t("flash.meeting_not_found"), "error")
        return redirect(url_for("main.admin"))

    doc_req = get_document_requires(meeting_id)
    if not doc_req:
        flash(t("flash.mail_no_requirements"), "error")
        return redirect(url_for("main.admin"))

    try:
        groups = _super_group_map()
    except Exception:
        current_app.logger.exception("Could not fetch groups from Gamma")
        flash(t("flash.mail_gamma_failed"), "error")
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
            flash(t("flash.mail_announce_failed", group=pretty_name), "error")
            return redirect(url_for("main.admin"))
        sent += 1

    if skipped:
        flash(t("flash.mail_groups_skipped", count=skipped), "error")
    flash(t("flash.mail_announce_sent", count=sent), "success")
    return redirect(url_for("main.admin"))


@mail.route("/admin/mail/liberation", methods=["POST"])
@login_as_admin_required
def send_liberation_mail_route():
    """Mail each group with missing duty liberation documents.

    Each requirement names the specific responsible group instance
    (prit25, digit25, ...), which is the mail recipient. Manual admin
    trigger; deduped per calendar year via SentMails, so it is safe to
    press the button twice and re-sends automatically next year.
    """
    mail_type = f"duty_retirement_{date.today().year}"
    sent = 0
    for entry in get_missing_liberation_documents():
        if has_sent_mail(mail_type, None, entry["group_name"]):
            continue
        try:
            send_mail_config(
                [f"{entry['group_name']}@chalmers.it"],
                f"Duty liberation documents {date.today().year}",
                "duty_retirement.txt",
                {
                    "group_name": entry["group_pretty_name"],
                    "task_list": entry["missing"],
                },
            )
        except Exception:
            current_app.logger.exception(
                "Liberation mail to %s failed", entry["group_name"]
            )
            flash(
                t("flash.mail_liberation_failed", group=entry["group_pretty_name"]),
                "error",
            )
            return redirect(url_for("main.liberation_admin"))
        record_sent_mail(mail_type, None, entry["group_name"])
        sent += 1

    if sent:
        flash(t("flash.mail_liberation_sent", count=sent), "success")
    else:
        flash(t("flash.mail_liberation_none"), "success")
    return redirect(url_for("main.liberation_admin"))
