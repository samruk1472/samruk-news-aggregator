import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _format_time_label(iso) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%H:%M")
    except Exception:
        return iso[:16]


def render_digest(articles: list[dict], period_from: datetime, period_to: datetime) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    tmpl = env.get_template("digest.html")

    def sort_key(a):
        return -(a.get("views") or 0)

    negative = sorted([a for a in articles if a.get("sentiment") == "negative"], key=sort_key)
    neutral = sorted([a for a in articles if a.get("sentiment") == "neutral"], key=sort_key)
    positive = sorted([a for a in articles if a.get("sentiment") == "positive"], key=sort_key)

    for group in (negative, neutral, positive):
        for a in group:
            a["time_label"] = _format_time_label(a.get("published_at") or a.get("collected_at"))

    now_label = period_to.strftime("%H:%M %d.%m.%Y")

    return tmpl.render(
        period_label=now_label,
        period_from=period_from.strftime("%H:%M"),
        period_to=period_to.strftime("%H:%M"),
        total=len(articles),
        negative_count=len(negative),
        neutral_count=len(neutral),
        positive_count=len(positive),
        negative=negative,
        neutral=neutral,
        positive=positive,
    )


def send_email(html_body: str, period_to: datetime):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("EMAIL_RECIPIENT", "n.zhakupov@sk.kz")
    subject_prefix = os.environ.get("EMAIL_SUBJECT_PREFIX", "[Самрук-Казына] Дайджест новостей")

    subject = f"{subject_prefix} — {period_to.strftime('%H:%M %d.%m.%Y')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, [recipient], msg.as_string())

    logger.info("Email sent to %s: %s", recipient, subject)
