"""Send emails through Gotify service."""

import os
import requests
import jinja2
from pathlib import Path

from .mail_config.variables import *


GOTIFY_URL = os.getenv("GOTIFY_URL", "http://localhost:8080")
GOTIFY_KEY = os.getenv("GOTIFY_PRE_SHARED_KEY") or os.getenv(
    "GOTIFY_PRE-SHARED-KEY", "123abc"
)


def send_mail(to: list[str], subject: str, body: str):
    """Send an email through Gotify.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text or HTML)

    Returns:
        Response dict from Gotify API

    Raises:
        requests.exceptions.RequestException: If request fails
    """
    response = requests.post(
        f"{GOTIFY_URL.rstrip('/')}/mail",
        json={
            "to": ",".join(to),
            "from": "admin@chalmers.it",
            "subject": subject,
            "body": body,
        },
        headers={
            "Authorization": f"pre-shared: {GOTIFY_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def send_mail_config(to: list[str], subject: str, config: Path, vars: dict[str, str]):
    """
    Based on given config, should populate the varaiables and send mail

    """
    with open(config) as f:
        c = f.read()

    body = jinja2.Template(c).render(**(get_static_values() | vars))

    send_mail(to, subject, body)
