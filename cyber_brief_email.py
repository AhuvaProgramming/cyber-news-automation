import feedparser
import os
import smtplib
import re
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://krebsonsecurity.com/feed/",
]

seen = set()


# ----------------------------
# CLASSIFICATION
# ----------------------------
def classify(title):
    t = title.lower()

    breach_score = sum(x in t for x in [
        "breach", "data breach", "leak", "data leak",
        "exposed", "compromised", "database",
        "credentials", "records", "dump"
    ])

    threat_score = sum(x in t for x in [
        "ransomware", "zero-day", "0day", "cve-", "exploit",
        "malware", "botnet", "phishing", "attack"
    ])

    advisory_score = sum(x in t for x in [
        "patch", "update", "advisory", "security update", "fix"
    ])

    if breach_score >= max(threat_score, advisory_score):
        return "BREACHES"

    if advisory_score > threat_score:
        return "ADVISORIES"

    return "THREATS"


# ----------------------------
# SEVERITY + CVE DETECTION
# ----------------------------
def extract_severity(title):
    t = title.lower()

    cve = re.findall(r"cve-\d{4}-\d+", t)

    if cve:
        return "CRITICAL", cve[0].upper()

    if any(x in t for x in ["ransomware", "zero-day", "0day", "exploit"]):
        return "CRITICAL", None

    if any(x in t for x in ["breach", "leak", "compromised"]):
        return "HIGH", None

    if any(x in t for x in ["patch", "update", "advisory"]):
        return "MEDIUM", None

    return "LOW", None


# ----------------------------
# FETCH ARTICLES
# ----------------------------
def get_articles():
    articles = []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)

    for url in FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries:
            title = entry.title.strip()

            if title in seen:
                continue
            seen.add(title)

            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            else:
                continue

            if published < cutoff:
                continue

            category = classify(title)
            severity, cve = extract_severity(title)

            articles.append({
                "title": title,
                "link": entry.link,
                "category": category,
                "severity": severity,
                "cve": cve,
                "source": url
            })

    return articles


# ----------------------------
# TOP CRITICAL THREATS
# ----------------------------
def top_critical(articles):
    return [a for a in articles if a["severity"] == "CRITICAL"][:3]


# ----------------------------
# BUILD EMAIL
# ----------------------------
def build_brief(articles):
    html = f"""
    <h2>🛡️ Cyber Intelligence Brief</h2>
    <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}</p>
    <hr>
    """

    top = top_critical(articles)

    if top:
        html += "<h3>🔥 Top 3 Critical Threats</h3><ul>"
        for a in top:
            html += f"""
            <li>
                <b>{a['title']}</b>
                <br><a href="{a['link']}">Read more</a>
            </li>
            """
        html += "</ul><hr>"

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
            cve_text = f" ({a['cve']})" if a["cve"] else ""

            html += f"""
            <li>
                <b>{a['severity']}</b> — {a['title']}{cve_text}
                <br><a href="{a['link']}">Source</a>
            </li>
            """

        html += "</ul>"

    return html


# ----------------------------
# SEND EMAIL
# ----------------------------
def send_email(content):
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    msg = MIMEText(content, "html")
    msg["Subject"] = "🛡️ Cyber Intelligence Brief"
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

    print("Email sent successfully")


# ----------------------------
# MAIN
# ----------------------------
def main():
    articles = get_articles()

    print(f"Collected {len(articles)} articles")

    brief = build_brief(articles)

    send_email(brief)


if __name__ == "__main__":
    main()