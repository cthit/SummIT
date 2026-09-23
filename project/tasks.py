"""Scheduled mail jobs, run via `flask send-due-mails`.

The command is invoked by the summit_mailer docker-compose sidecar on a
fixed tick, as ONE short-lived process per tick. get_db()'s pooled
connection is only returned when the process exits, so do not convert
this into a long-running in-process loop without adding connection
handling. SentMails makes every tick idempotent, so restarts and
overlapping ticks never double-send.
"""

import os
import logging
from datetime import datetime, timedelta

from flask import Flask

from .data_handler import (
    fetch_upcoming_meetings_with_deadline,
    get_missing_document_requires,
    has_sent_mail,
    record_sent_mail,
)
from .mail_handler import send_mail_config
from .mail_config.variables import get_static_values
from .gamma import GammaService as gs

logger = logging.getLogger(__name__)


def _super_group_map() -> dict[str, tuple[str, str]]:
    """id -> (name, pretty_name) for all super-groups, fetched once per run.

    Returns {} when Gamma is unavailable: callers skip those groups without
    recording anything, so the next tick simply retries.
    """
    try:
        return {
            entry.super_group.id: (
                entry.super_group.name,
                entry.super_group.pretty_name,
            )
            for entry in gs.get_all_super_groups()
        }
    except Exception:
        logger.exception("Could not fetch super groups from Gamma")
        return {}


def _send_reminders(meeting, missing, groups, now):
    """Mail each group its missing documents shortly before the deadline (#4)."""
    reminder_days = int(os.getenv("MAIL_REMINDER_DAYS_BEFORE", "3"))
    deadline = meeting.deadline
    if not (deadline - timedelta(days=reminder_days) <= now < deadline):
        return

    for group_id, task_list in missing.items():
        if group_id not in groups:
            logger.warning("Group %s unknown to Gamma; skipping reminder", group_id)
            continue
        if has_sent_mail("deadline_reminder", meeting.id, group_id):
            continue
        name, pretty_name = groups[group_id]
        try:
            send_mail_config(
                [f"{name}@chalmers.it"],
                f"Reminder: document deadline {deadline:%Y-%m-%d}",
                "deadline_reminder.txt",
                {
                    "group_name": pretty_name,
                    "task_list": task_list,
                    "meeting_date": str(meeting.date),
                    "deadline_date": deadline.strftime("%Y-%m-%d"),
                    "deadline_time": deadline.strftime("%H:%M"),
                },
            )
        except Exception:
            # Not recorded, so the next tick retries this one mail
            logger.exception("Reminder mail to %s failed", name)
            continue
        record_sent_mail("deadline_reminder", meeting.id, group_id)
        logger.info("Sent deadline reminder to %s for meeting %s", name, meeting.id)


def _send_deadline_reached(meeting, missing, groups, now):
    """Mail the meeting admins once the deadline has passed (#8)."""
    deadline = meeting.deadline
    if now < deadline or has_sent_mail("deadline_reached", meeting.id, None):
        return

    static = get_static_values()
    missing_lines = [
        f"{groups.get(group_id, (group_id, group_id))[1]}: {doc_type}"
        for group_id, task_list in sorted(missing.items())
        for doc_type in task_list
    ]
    # "Meeting admins" is both the board and the secretary group
    recipients = sorted({static["board_email"], static["secretary_email"]})
    try:
        send_mail_config(
            recipients,
            f"Document deadline reached for meeting {meeting.date}",
            "deadline_reached.txt",
            {
                "missing": missing_lines,
                "meeting_date": str(meeting.date),
                "deadline_date": deadline.strftime("%Y-%m-%d"),
                "deadline_time": deadline.strftime("%H:%M"),
            },
        )
    except Exception:
        logger.exception("Deadline-reached mail for meeting %s failed", meeting.id)
        return
    record_sent_mail("deadline_reached", meeting.id, None)
    logger.info("Sent deadline-reached mail for meeting %s", meeting.id)


def register_cli(app: Flask):
    @app.cli.command("send-due-mails")
    def send_due_mails():
        """Send due deadline reminder (#4) and deadline reached (#8) mails."""
        now = datetime.now()
        meetings = fetch_upcoming_meetings_with_deadline()
        if not meetings:
            logger.info("No upcoming meetings with a deadline")
            return

        groups = _super_group_map()
        for meeting in meetings:
            missing = get_missing_document_requires(meeting.id)
            _send_reminders(meeting, missing, groups, now)
            _send_deadline_reached(meeting, missing, groups, now)
