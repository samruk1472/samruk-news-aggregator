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

SOURCE_RANK = {
    "Tengrinews (EN)": "⭐⭐⭐⭐⭐",
    "Kursiv.kz": "⭐⭐⭐⭐⭐",
    "Vlast.kz": "⭐⭐⭐⭐",
    "The Astana Times": "⭐⭐⭐⭐",
    "Time.kz": "⭐⭐⭐",
    "Caravan.kz": "⭐⭐⭐",
    "Profit.kz": "⭐⭐⭐",
    "Egemen.kz": "⭐⭐",
}


def _format_time_label(iso) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(iso)[:16]


def _date_key(iso) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return str(iso)[:10]


def _views_label(a: dict) -> str:
    views = a.get("views")
    if views and views > 0:
        return f"{views:,}".replace(",", " ")
    return ""


def render_digest(articles: list, period_from: datetime, period_to: datetime) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    tmpl = env.get_template("digest.html")

    def sort_key(a):
        return -(a.get("views") or 0)

    negative = sorted([a for a in articles if a.get("sentiment") == "negative"], key=sort_key)
    neutral  = sorted([a for a in articles if a.get("sentiment") == "neutral"],  key=sort_key)
    positive = sorted([a for a in articles if a.get("sentiment") == "positive"], key=sort_key)

    for group in (negative, neutral, positive):
        for a in group:
            pub = a.get("published_at") or a.get("collected_at")
            a["time_label"]  = _format_time_label(pub)
            a["date_key"]    = _date_key(pub)
            a["views_label"] = _views_label(a)

    all_dates = [
        a["date_key"] for a in (negative + neutral + positive) if a.get("date_key")
    ]
    date_min = min(all_dates) if all_dates else period_from.strftime("%Y-%m-%d")
    date_max = max(all_dates) if all_dates else period_to.strftime("%Y-%m-%d")

    companies = sorted({a.get("company", "") for a in articles if a.get("company")})
    sources   = {a.get("source", "") for a in articles if a.get("source")}

    return tmpl.render(
        updated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        source_count=len(sources),
        date_min=date_min,
        date_max=date_max,
        companies=companies,
        total=len(articles),
        negative_count=len(negative),
        neutral_count=len(neutral),
        positive_count=len(positive),
        negative=negative,
        neutral=neutral,
        positive=positive,
    )


def send_email(html_body: str, period_to: datetime):
    gmail_user     = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient      = os.environ.get("EMAIL_RECIPIENT", "n.zhakupov@sk.kz")
    subject_prefix = os.environ.get("EMAIL_SUBJECT_PREFIX", "[Самрук-Казына] Дайджест новостей")

    subject = f"{subject_prefix} — {period_to.strftime('%H:%M %d.%m.%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_user
    msg["To"]      = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, [recipient], msg.as_string())

    logger.info("Email sent to %s: %s", recipient, subject)


def save_last_digest(html_body: str):
    path = Path(__file__).parent / "data" / "last_digest.html"
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_body)
