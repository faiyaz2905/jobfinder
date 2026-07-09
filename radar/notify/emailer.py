from __future__ import annotations

import html
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from radar.models import Posting


@dataclass(frozen=True)
class EmailSettings:
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    sender: str
    recipients: tuple[str, ...]
    use_tls: bool = True


DEFAULT_RECIPIENTS: tuple[str, ...] = ()


def load_email_settings() -> EmailSettings:
    username = os.environ.get("RADAR_SMTP_USERNAME", "").strip()
    sender = os.environ.get("RADAR_EMAIL_FROM", "").strip() or username
    recipients = merge_recipients(os.environ.get("RADAR_EMAIL_TO", ""))

    return EmailSettings(
        smtp_host=os.environ.get("RADAR_SMTP_HOST", "smtp.gmail.com").strip(),
        smtp_port=int(os.environ.get("RADAR_SMTP_PORT", "587")),
        username=username,
        password=os.environ.get("RADAR_SMTP_PASSWORD", ""),
        sender=sender,
        recipients=recipients,
        use_tls=os.environ.get("RADAR_SMTP_TLS", "1").strip().lower() not in {"0", "false", "no"},
    )


def merge_recipients(extra_recipients: str) -> tuple[str, ...]:
    recipients: list[str] = []
    for email in [*DEFAULT_RECIPIENTS, *extra_recipients.replace(";", ",").split(",")]:
        cleaned = email.strip()
        if cleaned and cleaned.lower() not in {recipient.lower() for recipient in recipients}:
            recipients.append(cleaned)
    return tuple(recipients)


def missing_settings(settings: EmailSettings) -> list[str]:
    missing = []
    if not settings.smtp_host:
        missing.append("RADAR_SMTP_HOST")
    if not settings.username:
        missing.append("RADAR_SMTP_USERNAME")
    if not settings.password:
        missing.append("RADAR_SMTP_PASSWORD")
    if not settings.sender:
        missing.append("RADAR_EMAIL_FROM")
    if not settings.recipients:
        missing.append("RADAR_EMAIL_TO")
    return missing


def send_new_postings(
    new_postings: list[tuple[str, Posting]],
    settings: EmailSettings | None = None,
) -> None:
    if not new_postings:
        return

    settings = settings or load_email_settings()
    missing = missing_settings(settings)
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing email settings: {names}")

    message = build_message(new_postings, settings)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.use_tls:
            smtp.starttls()
        smtp.login(settings.username, settings.password)
        smtp.send_message(message)


def build_message(new_postings: list[tuple[str, Posting]], settings: EmailSettings) -> EmailMessage:
    count = len(new_postings)
    message = EmailMessage()
    message["Subject"] = f"Internship Radar: {count} new posting{'s' if count != 1 else ''}"
    message["From"] = settings.sender
    message["To"] = ", ".join(settings.recipients)
    message.set_content(build_text_body(new_postings))
    message.add_alternative(build_html_body(new_postings), subtype="html")
    return message


def build_text_body(new_postings: list[tuple[str, Posting]]) -> str:
    lines = ["Internship Radar found new postings:", ""]
    for posting_id, posting in new_postings:
        lines.append(f"{posting_id} | {posting.company} | {posting.role}")
        lines.append(f"Apply: {posting.apply_action}")
        lines.append(f"Source: {posting.source_url}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_html_body(new_postings: list[tuple[str, Posting]]) -> str:
    rows = []
    for posting_id, posting in new_postings:
        rows.append(
            "<tr>"
            f"<td>{escape(posting_id)}</td>"
            f"<td>{escape(posting.company)}</td>"
            f"<td>{escape(posting.role)}</td>"
            f"<td>{escape(posting.source)}</td>"
            f'<td><a href="{escape_attr(posting.apply_action)}">Apply</a></td>'
            "</tr>"
        )

    return f"""\
<!doctype html>
<html>
  <body style="font-family: Arial, sans-serif; color: #202124;">
    <h2 style="margin-bottom: 8px;">Internship Radar found new postings</h2>
    <table cellpadding="8" cellspacing="0" border="1" style="border-collapse: collapse; border-color: #d0d7de;">
      <thead>
        <tr style="background: #f6f8fa;">
          <th align="left">ID</th>
          <th align="left">Company</th>
          <th align="left">Role</th>
          <th align="left">Source</th>
          <th align="left">Action</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </body>
</html>
"""


def escape(value: str) -> str:
    return html.escape(value, quote=False)


def escape_attr(value: str) -> str:
    return html.escape(value, quote=True)
