from flask import (
    Blueprint,
    flash,
    redirect,
    url_for,
)

from .auth import login_as_admin_required
from .mail_example import example_simple_mail
from .data_handler import get_document_requires, fetch_meeting
from .mail_handler import send_mail, send_mail_config
from .gamma import GammaService as gs
from pathlib import Path


mail = Blueprint("mail", __name__)


@mail.route("/admin/mail/send/<int:meeting_id>", methods=["POST"])
@login_as_admin_required
def send_mail_route(meeting_id):
    doc_req = get_document_requires(meeting_id)  # databased call B)
    meeting_obj = fetch_meeting(meeting_id)
    if meeting_obj is None:
        flash("Meeting not found.", "error")
        return redirect(url_for("main.admin"))

    dr = {
        gs.get_super_group(gid): v for gid, v in doc_req.items()
    }  # dict[GammaSuperGroup, str[documents=task_list]]

    date = meeting_obj.date
    lp = meeting_obj.study_period.lp
    year = meeting_obj.study_period.year

    deadline = meeting_obj.deadline
    for group, requirements in dr.items():
        vars = {
            "group_name": group.pretty_name,
            "task_list": requirements,
            "meeting_date": date,
            "deadline_date": deadline.strftime("%Y-%m-%d") if deadline else "TBD",
            "deadline_time": deadline.strftime("%H:%M") if deadline else "",
        }

        send_mail_config(
            [f"{group.name}@chalmers.it"],
            f"Meeting Anouncement {"Summer" if lp==5 else f"lp{lp}"} {year}",
            Path("project/mail_config/meeting_announcement.txt"),
            vars,
        )

    return redirect(url_for("main.admin"))
