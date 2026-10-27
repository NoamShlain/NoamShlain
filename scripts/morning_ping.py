"""Send Tomer a morning WhatsApp message and forward his first reply.

Runs inside GitHub Actions (see .github/workflows/morning-ping.yml).
The repo is public, so Actions logs are public too: never print phone
numbers or message contents.
"""

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Jerusalem")
MESSAGE = "היי תומר, בוקר טוב :)\nמתי זמין שנעלה לשיחה?"

WINDOW_START = (6, 0)    # send at a random time between 06:00 ...
WINDOW_END = (6, 30)     # ... and 06:30 Israel time
LATEST_SEND = (6, 45)    # GitHub often starts cron jobs late; still send until 06:45
POLL_SECONDS = 30
WAIT_FOR_REPLY_HOURS = 5.5  # GitHub kills jobs after 6h

ID_INSTANCE = os.environ["GREEN_API_ID_INSTANCE"]
API_TOKEN = os.environ["GREEN_API_TOKEN"]
API_URL = os.environ.get("GREEN_API_URL") or "https://api.green-api.com"
TOMER_CHAT = os.environ["TOMER_PHONE"].lstrip("+") + "@c.us"
MY_PHONE = os.environ.get("MY_PHONE", "").lstrip("+")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
SEND_DAYS = os.environ.get("SEND_DAYS") or "Sun,Mon,Tue,Wed,Thu,Fri,Sat"
FORCE = os.environ.get("FORCE") == "true"


def log(msg):
    print(f"[{datetime.now(TZ):%H:%M:%S}] {msg}", flush=True)


def green(method, body):
    url = f"{API_URL.rstrip('/')}/waInstance{ID_INSTANCE}/{method}/{API_TOKEN}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def message_text(m):
    text = m.get("textMessage") or (m.get("extendedTextMessage") or {}).get("text")
    if text:
        return text
    if m.get("caption"):
        return f"[{m.get('typeMessage')}] {m['caption']}"
    return f"[{m.get('typeMessage', 'message')}]"


def history():
    return green("getChatHistory", {"chatId": TOMER_CHAT, "count": 50})


def todays_ping(start_of_day):
    """The morning message already sent today, if any (makes re-runs safe)."""
    for m in history():
        if (
            m.get("type") == "outgoing"
            and m.get("timestamp", 0) >= start_of_day
            and message_text(m).strip() == MESSAGE.strip()
        ):
            return m
    return None


def notify(reply, reply_time):
    title = f"Tomer replied ({reply_time:%H:%M})"
    if NTFY_TOPIC:
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=reply.encode(),
            headers={"Title": title.encode(), "Tags": "speech_balloon"},
        )
        urllib.request.urlopen(req, timeout=30).close()
        log("Forwarded reply via ntfy")
    if MY_PHONE:
        green("sendMessage", {"chatId": f"{MY_PHONE}@c.us", "message": f"{title}:\n{reply}"})
        log("Forwarded reply via WhatsApp")


def at(now, hm):
    return now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)


def main():
    now = datetime.now(TZ)
    # Two cron entries cover summer/winter time; the other one lands at 04:50 or 06:50.
    if not FORCE and not (at(now, (5, 0)) <= now < at(now, LATEST_SEND)):
        log("Not this run's turn (DST twin), exiting")
        return
    if not FORCE and now.strftime("%a") not in SEND_DAYS.split(","):
        log("Not a send day, exiting")
        return

    start_of_day = int(at(now, (0, 0)).timestamp())
    ping = todays_ping(start_of_day)
    if ping:
        log("Already sent today, only waiting for a reply")
        sent_at = ping["timestamp"]
    else:
        if not FORCE:
            start, end = at(now, WINDOW_START), at(now, WINDOW_END)
            target = start + timedelta(seconds=random.uniform(0, (end - start).total_seconds()))
            if now < target:
                log(f"Sleeping until {target:%H:%M:%S}")
                time.sleep((target - now).total_seconds())
        green("sendMessage", {"chatId": TOMER_CHAT, "message": MESSAGE})
        sent_at = int(time.time()) - 5
        log("Morning message sent")

    deadline = time.time() + WAIT_FOR_REPLY_HOURS * 3600
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            incoming = [
                m for m in history()
                if m.get("type") == "incoming" and m.get("timestamp", 0) >= sent_at
            ]
        except Exception as e:  # transient API errors shouldn't kill a 5h wait
            log(f"Poll failed: {type(e).__name__}")
            continue
        if incoming:
            first = min(incoming, key=lambda m: m["timestamp"])
            notify(message_text(first), datetime.fromtimestamp(first["timestamp"], TZ))
            return
    log("No reply before the deadline")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        # Don't echo the URL: it contains the API token.
        log(f"Green API error: HTTP {e.code}")
        sys.exit(1)
