"""Example usage of the mail_handler module."""

from mail_handler import send_mail


def example_simple_mail():
    """Send a simple text email."""
    print("Sending email...")
    
    response = send_mail(
        to="napster@chalmers.it",
        subject="Test Email",
        body="It worked B)"
    )
    
    print(f"Email sent! Response: {response}")


if __name__ == "__main__":
    example_simple_mail()
