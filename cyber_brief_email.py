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

    breach_score = sum(x in t for x in [
        "breach", "leak", "exposed", "compromised",
        "database", "credentials", "records", "dump"
    ])

    threat_score = sum(x in t for x in [
        "ransomware", "zero-day", "0day", "cve-", "exploit", "malware"
    ])

    advisory_score = sum(x in t for x in [
        "patch", "update", "advisory", "fix"
    ])

    if breach_score > max(threat_score, advisory_score):
        return "BREACHES"

    if advisory_score > threat_score:
        return "ADVISORIES"

    return "THREATS"


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
                category = classify(entry.title)

                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "category": category,
                    "source": url
                })

    return articles[:10]
def build_brief(articles):
    html = f"""
    <h2>🛡️ Cyber Security Intelligence Brief</h2>
    <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}</p>
    <hr>
    """

    groups = {
        "THREATS": [],
        "BREACHES": [],
        "ADVISORIES": []
    }

    for a in articles:
        groups[a["category"]].append(a)

    order = [
        ("THREATS", "🚨"),
        ("BREACHES", "🧨"),
        ("ADVISORIES", "🛠️")
    ]

    for section, icon in order:
        items = groups[section]

        if not items:
            continue

        html += f"<h3>{icon} {section}</h3><ul>"

        for a in items:
            html += f"""
            <li>
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