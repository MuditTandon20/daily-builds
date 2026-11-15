# Daily Builds

A free Python tool that checks today's GitHub contributions and, on otherwise inactive days, commits a useful snapshot of public repository maintenance metadata. Automated reports are explicitly labelled as automated.

It runs at **11:30 p.m. Asia/Kolkata**, with retries at 11:40 and 11:50 p.m. A Windows scheduled task runs Python directly; no paid API, AI subscription, hosting, or third-party Python package is needed. Your PC must be awake and online. This is a local automation, not a cloud service.

The guard checks GitHub's contribution collection across the authenticated account, including private activity visible to that account. Existing qualifying commit activity causes a skip. Restricted activity also causes a conservative skip. GitHub may take time to reflect recent contributions, so this is best effort. Contributions on unmerged feature branches may not count toward the profile graph.

On an inactive day, a dated JSON report records public repository descriptions, languages, license presence, issue counts, default branches, and last push times. It never publishes private repository names or contents. Each day's report is created at most once, on the default branch, using the owner's GitHub noreply email and India-time author date. No backdating or empty commits.

## Run

Requires Python 3.10+, Git, and an existing Git Credential Manager login for `MuditTandon20`.

```powershell
python daily_builds.py          # read-only dry run
python daily_builds.py --write  # conditional commit, only 23:30-23:59 IST
python -m unittest discover -s tests -v
```

Credentials are obtained at runtime from Git Credential Manager and never saved in this repository. API errors fail the run rather than being treated as zero contributions. Logs are stored under `%LOCALAPPDATA%/DailyBuilds`.

## Scheduled task

Task name: `Daily Builds - contribution fallback`. Runs as the signed-in Windows user, so that user's Git Credential Manager is available. Windows timezone must remain India Standard Time. Sign in and leave the PC awake and connected during the fallback window. The task requests wake from sleep, but hardware and Windows power settings may prevent it. It cannot wake a shut-down PC.

To disable:

```powershell
Disable-ScheduledTask -TaskName 'Daily Builds - contribution fallback'
```

GitHub's contribution graph can take up to 24 hours to update. This automation cannot guarantee an uninterrupted streak during outages or when the PC is off.
