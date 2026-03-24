"""Email template variables - both static config and dynamic meeting data."""

import os


class Variable:
    def __init__(self, name, description):
        self.name = name
        self.description = description


STATIC_VARIABLES = [
    Variable("frontend_url", "URL to the SummIT application frontend"),
    Variable("template_url", "URL to the document template (e.g., Overleaf)"),
    Variable("secretary_email", "Email address of the secretary"),
    Variable("secretary_display_name", "The name of the secretary committee"),
    Variable("board_display_name", "Display name of the board (e.g., 'styrIT Board')"),
    Variable("board_email", "Email address of the board"),
]

DYNAMIC_VARIABLES = [
    Variable("meeting_day", "Day of the week for the meeting (e.g., 'Monday')"),
    Variable("meeting_month", "Month name of the meeting (e.g., 'March')"),
    Variable("meeting_date", "Full date of the meeting (e.g., '2026-03-15')"),
    Variable("deadline_time", "Time when documents are due (e.g., '23:59')"),
    Variable("deadline_date", "Date when documents are due (e.g., '2026-03-10')"),
    Variable("group_name", "Full name of the group receiving the email"),
    Variable("task_list", "List of required documents/tasks"),
]


def get_static_values():
    """Returns a dictionary of static variable values from environment."""
    return {
        "frontend_url": os.getenv("FRONTEND_URL", "https://summit.chalmers.it"),
        "template_url": os.getenv("TEMPLATE_URL", "https://overleaf.com/read/template"),
        "secretary_email": os.getenv("SECRETARY_EMAIL", "motespresidit@chalmers.it"),
        "secretary_display_name": os.getenv("SECRETARY_DISPLAY_NAME", "MötespresidIT"),
        "board_display_name": os.getenv("BOARD_DISPLAY_NAME", "styrIT Board"),
        "board_email": os.getenv("BOARD_EMAIL", "board@chalmers.it"),
    }
