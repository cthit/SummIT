"""Send emails through Gotify service."""

import os
import requests


GOTIFY_URL = os.getenv("GOTIFY_URL", "http://localhost:8080")
GOTIFY_KEY = os.getenv("GOTIFY_PRE_SHARED_KEY") or os.getenv("GOTIFY_PRE-SHARED-KEY", "123abc")


def send_mail(to: str, subject: str, body: str, from_address: str = "admin@chalmers.it"):
    """Send an email through Gotify.
    
    Args:
        to: Recipient email address
        subject: Email subject  
        body: Email body (plain text or HTML)
        from_address: Sender email (default: admin@chalmers.it)
        
    Returns:
        Response dict from Gotify API
        
    Raises:
        requests.exceptions.RequestException: If request fails
    """
    response = requests.post(
        f"{GOTIFY_URL.rstrip('/')}/mail",
        json={"to": to, "from": from_address, "subject": subject, "body": body},
        headers={"Authorization": f"pre-shared: {GOTIFY_KEY}", "Content-Type": "application/json"},
        timeout=30
    )
    response.raise_for_status()
    return response.json()
