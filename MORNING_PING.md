# Morning ping to Tomer

Every morning, at a random time between 06:00 and 06:30 (Israel time), a GitHub Action
sends Tomer this WhatsApp message from your own number:

> היי תומר, בוקר טוב :)
> מתי זמין שנעלה לשיחה?

Then it checks the chat every 30 seconds and forwards **only his first reply** to you.
After that it stops, so nothing else from the chat gets forwarded. If he doesn't reply
within about 5.5 hours, it gives up for the day.

## One-time setup

1. **Connect WhatsApp to Green API** (it links to your number the same way WhatsApp Web does)
   - Sign up at https://green-api.com and create a free "Developer" instance.
   - Scan the QR code with WhatsApp → *Linked devices*.
   - Copy `idInstance`, `apiTokenInstance`, and `apiUrl` from the console.
2. **Get phone notifications (recommended)**: install the **ntfy** app (iOS/Android) and
   subscribe to a long random topic name, e.g. `noam-tomer-8f3k2q9x`. Anyone who knows the
   name can read it, so make it hard to guess.
3. **Add repo secrets** in GitHub → Settings → Secrets and variables → Actions → *Secrets*:

   | Secret | Example |
   |---|---|
   | `GREEN_API_ID_INSTANCE` | `7103123456` |
   | `GREEN_API_TOKEN` | `abc123...` |
   | `GREEN_API_URL` | `https://7103.api.greenapi.com` |
   | `TOMER_PHONE` | `972501234567` (country code, no `+`, no leading 0) |
   | `NTFY_TOPIC` | `noam-tomer-8f3k2q9x` |
   | `MY_PHONE` | *(optional)* your number. The reply is also sent to your own WhatsApp "You" chat |

4. *(Optional)* To skip some days, add a **variable** (Variables tab) named `SEND_DAYS`, e.g.
   `Sun,Mon,Tue,Wed,Thu`. By default it runs every day.
5. Merge this into `main`. Scheduled workflows only run from the default branch.

## Testing

Actions → *Morning ping to Tomer* → *Run workflow* → tick **force**. It sends the message
right away. (It never sends twice in one day, so test with your own number in `TOMER_PHONE` first.)

## Good to know

- GitHub cron isn't exact. Runs are sometimes 10–30 minutes late, so the job starts at
  05:50. If it starts after 06:45, it skips that day.
- GitHub disables scheduled workflows after 60 days with no commits to the repo. If that
  happens, re-enable it in the Actions tab.
- The repo is public, so the logs are public too. The script never logs phone numbers or
  message text, and everything sensitive is stored in secrets.
