import feedparser
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://krebsonsecurity.com/feed/",
]

import re
from datetime import datetime, timezone, timedelta

def classify(title):
    t = title.lower()

    # Categories + severity heuristics
    if any(x in t for x in ["ransomware", "zero-day", "0day", "cve-", "exploit"]):
        category = "Vulnerability / Exploit"
        severity = "CRITICAL"

    elif any(x in t for x in ["breach", "leak", "stolen", "exposed"]):
        category = "Data Breach"
        severity = "HIGH"

    elif any(x in t for x in ["malware", "trojan", "botnet", "virus"]):
        category = "Malware"
        severity = "HIGH"

    elif any(x in t for x in ["update", "patch", "advisory"]):
        category = "Security Advisory"
        severity = "MEDIUM"

    else:
        category = "General Cyber News"
        severity = "LOW"

    return category, severity


def get_articles():
    articles = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)

    for url in FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries:
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            else:
                continue

            if published >= cutoff:
                category, severity = classify(entry.title)

                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "category": category,
                    "severity": severity,
                    "source": url
                })

    return articles[:10]
def build_brief(articles):
    html = f"""
    <h2>🛡️ Daily Cyber Security Brief</h2>
    <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}</p>
    <hr>
    """

    # Group by severity
    order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    for level in order:
        section = [a for a in articles if a["severity"] == level]

        if not section:
            continue

        html += f"<h3>⚠️ {level}</h3><ul>"

        for a in section:
            html += f"""
            <li>
                <b>[{a['category']}]</b>
                <a href="{a['link']}">{a['title']}</a>
                <br><small>{a['source']}</small>
            </li>
            """

        html += "</ul>"

    return html


def send_email(content):
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    msg = MIMEText(content, "html")  # IMPORTANT CHANGE
    msg["Subject"] = "🛡️ Daily Cyber Intelligence Brief"
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

    print("Email sent successfully")

def main():
    headlines = get_articles()
    brief = build_brief(headlines)

    print(brief)
    send_email(brief)


if __name__ == "__main__":
    main()