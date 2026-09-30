import smtplib
import ssl
from email.message import EmailMessage
from .config import settings


def send_email(to: str, subject: str, body: str) -> None:
    """
    Sends via SMTP if configured; otherwise prints to the console. This means
    password reset works out of the box for local testing with zero setup —
    just watch the terminal for the link — and you only need to touch
    SMTP_* in .env once you're ready to actually deliver real emails.
    """
    if not settings.SMTP_HOST:
        print("\n" + "=" * 70)
        print(f"[DEV MODE — no SMTP configured] Email to: {to}")
        print(f"Subject: {subject}")
        print(body)
        print("=" * 70 + "\n")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
