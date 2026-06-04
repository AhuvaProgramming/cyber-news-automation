import feedparser
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://krebsonsecurity.com/feed/",
]
from datetime import datetime, timezone, timedelta

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

            # last 24 hours instead of strict "today"
            if published >= cutoff:
                articles.append(entry.title)

    return articles[:10]
def build_brief(headlines):
    text = f"🛡️ Daily Cyber Brief — {datetime.now().strftime('%Y-%m-%d')}\n\n"

    for i, title in enumerate(headlines, 1):
        text += f"{i}. {title}\n"

    return text


def send_email(content):
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    msg = MIMEText(content)
    msg["Subject"] = "🛡️ Daily Cyber Brief"
    msg["From"] = sender
    msg["To"] = receiver

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)

        print("✅ Email sent successfully")

    except Exception as e:
        print("❌ Email failed:", e)


def main():
    headlines = get_articles()
    brief = build_brief(headlines)

    print(brief)
    send_email(brief)


if __name__ == "__main__":
    main()