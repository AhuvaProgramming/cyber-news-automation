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
# IMPACT SUMMARY
# ----------------------------
def summarize(title):
    t = title.lower()

    if "ransomware" in t:
        return "Potential operational disruption and data encryption risk."

    if "breach" in t or "leak" in t or "exposed" in t:
        return "Sensitive data exposure and credential compromise risk."

    if "zero-day" in t or "0day" in t or "exploit" in t:
        return "Active exploitation risk before patch availability."

    if "cve" in t:
        return "Known vulnerability requiring immediate patching."

    if "malware" in t or "trojan" in t:
        return "Malicious software activity targeting systems or users."

    return "General cybersecurity development with limited immediate impact."


# ----------------------------
# RISK SCORING
# ----------------------------
def risk_score(article):
    title = article["title"].lower()

    score = 0

    if article["severity"] == "CRITICAL":
        score += 5
    elif article["severity"] == "HIGH":
        score += 3
    elif article["severity"] == "MEDIUM":
        score += 2
    else:
        score += 1

    if "ransomware" in title:
        score += 3
    if "zero-day" in title or "0day" in title:
        score += 3
    if "breach" in title or "leak" in title:
        score += 2
    if "cve" in title:
        score += 2

    return score


def top_risks(articles):
    return sorted(articles, key=risk_score, reverse=True)[:3]


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

            # simple severity mapping for display
            severity = "LOW"
            if "ransomware" in title.lower() or "zero-day" in title.lower():
                severity = "CRITICAL"
            elif "breach" in title.lower() or "leak" in title.lower():
                severity = "HIGH"
            elif "patch" in title.lower():
                severity = "MEDIUM"

            articles.append({
                "title": title,
                "link": entry.link,
                "category": category,
                "severity": severity,
                "source": url
            })

    return articles


# ----------------------------
# BUILD EMAIL
# ----------------------------
def build_brief(articles):
    summary = executive_summary(articles)
    html = f"""
   <h2>🛡️ Cyber Intelligence Brief</h2>
   <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}</p>
   <h3> Executive Summary</h3>
   <p>{summary}</p>
   <hr>
    """

    # TOP RISKS
    top = top_risks(articles)

    if top:
        html += "<h3>🔥 Top Risk of the Day</h3><ol>"

        for a in top:
            html += f"""
            <li>
                <b>{a['severity']}</b> — {a['title']}
                <br><i>{summarize(a['title'])}</i>
                <br><a href="{a['link']}">Source</a>
            </li>
            """

        html += "</ol><hr>"

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
                <b>{a['severity']}</b> — {a['title']}
                <br><i>{summarize(a['title'])}</i>
                <br><a href="{a['link']}">Source</a>
            </li>
            """

        html += "</ul>"

    return html
def executive_summary(articles):
    threats = sum(1 for a in articles if a["category"] == "THREATS")
    breaches = sum(1 for a in articles if a["category"] == "BREACHES")
    advisories = sum(1 for a in articles if a["category"] == "ADVISORIES")

    critical = sum(1 for a in articles if a["severity"] == "CRITICAL")
    high = sum(1 for a in articles if a["severity"] == "HIGH")

    summary = "🧠 Executive Summary: "

    if critical > 0:
        summary += f"{critical} critical security events detected, indicating elevated active threat activity. "
    else:
        summary += "No critical incidents observed in the last 24 hours. "

    if threats > breaches:
        summary += "Threat activity dominates the landscape, with ongoing exploitation attempts and malware campaigns. "
    elif breaches > 0:
        summary += "Multiple breach-related incidents indicate continued exposure of sensitive data. "

    if advisories > 0:
        summary += "Several vendor advisories suggest active patching cycles across major platforms. "

    summary += "Organizations should prioritize patching critical vulnerabilities and monitoring for active exploit attempts."

    return summary


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
