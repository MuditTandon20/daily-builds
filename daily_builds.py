"""Free, dependency-free GitHub contribution guard and public repository audit."""
import argparse
import base64
from datetime import datetime, time, timedelta, timezone
import json
import os
import subprocess
import urllib.error
import urllib.request

IST = timezone(timedelta(hours=5, minutes=30))
OWNER = "MuditTandon20"
REPO = f"{OWNER}/daily-builds"


def credentials():
    result = subprocess.run(
        ["git", "credential", "fill"],
        input=f"protocol=https\nhost=github.com\nusername={OWNER}\n\n",
        text=True, capture_output=True, check=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"},
        timeout=30,
    )
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if not fields.get("password"):
        raise RuntimeError("No saved GitHub credential. Sign in with Git Credential Manager.")
    return fields["password"]


class GitHub:
    def __init__(self, token):
        self.token = token

    def request(self, path, data=None, method=None):
        request = urllib.request.Request(
            "https://api.github.com" + path,
            data=json.dumps(data).encode() if data is not None else None,
            method=method,
            headers={"Authorization": "Bearer " + self.token,
                     "User-Agent": "daily-builds", "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)


def day_start(now):
    return datetime.combine(now.astimezone(IST).date(), time(), IST)


def contribution_count(api, now):
    query = """query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) { contributionsCollection(from:$from, to:$to) {
        totalCommitContributions restrictedContributionsCount
      } }
    }"""
    result = api.request("/graphql", {"query": query, "variables": {
        "login": OWNER, "from": day_start(now).isoformat(), "to": now.isoformat()}})
    if result.get("errors"):
        raise RuntimeError("GitHub contribution query failed; refusing to assume zero activity.")
    collection = result["data"]["user"]["contributionsCollection"]
    return collection["totalCommitContributions"] + collection["restrictedContributionsCount"]


def repositories(api):
    result = []
    page = 1
    while True:
        batch = api.request(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        result.extend(batch)
        if len(batch) < 100:
            return result
        page += 1


def audit(repos):
    """Report only public metadata; never publish private repository names."""
    return [{"repository": repo["full_name"], "url": repo["html_url"],
             "description": repo.get("description"), "language": repo.get("language"),
             "archived": repo["archived"], "fork": repo["fork"],
             "default_branch": repo["default_branch"],
             "has_license": repo.get("license") is not None,
             "open_issues": repo["open_issues_count"], "last_push": repo.get("pushed_at")}
            for repo in sorted(repos, key=lambda repo: repo["full_name"].lower())
            if not repo["private"]]


def report_path(now):
    return f"reports/{now.astimezone(IST).date().isoformat()}.json"


def exists(api, path):
    try:
        api.request(f"/repos/{REPO}/contents/{path}")
        return True
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise


def run(api, now, write=False):
    # A late retry must never create a contribution for the next day.
    local = now.astimezone(IST)
    if write and local.time() < time(23, 30):
        print("Outside the 23:30-23:59 IST window; skipped.")
        return
    profile = api.request("/user")
    if profile["login"].lower() != OWNER.lower():
        raise RuntimeError("Saved GitHub account does not match the configured owner.")
    count = contribution_count(api, now)
    if count:
        print(f"{local.date()}: {count} qualifying contribution(s) already recorded; skipped.")
        return
    path = report_path(now)
    if exists(api, path):
        print("Today's report already exists; skipped.")
        return
    report = {"date": str(local.date()), "timezone": "Asia/Kolkata",
              "generated_at": now.isoformat(), "automated": True,
              "purpose": "Public repository maintenance snapshot",
              "repositories": audit(repositories(api))}
    if not write:
        print(f"Dry run: would commit {path} with {len(report['repositories'])} public repositories.")
        return
    # Check again immediately before the write to reduce races with manual work.
    current = datetime.now(IST)
    if current.date() != local.date() or contribution_count(api, current):
        print("Date changed or a contribution arrived during the audit; skipped.")
        return
    identity = {"name": profile.get("name") or OWNER,
                "email": f"{profile['id']}+{OWNER}@users.noreply.github.com",
                "date": current.isoformat()}
    result = api.request(f"/repos/{REPO}/contents/{path}", {
        "message": f"chore: automated public repository audit for {local.date()}",
        "content": base64.b64encode((json.dumps(report, indent=2) + "\n").encode()).decode(),
        "author": identity, "committer": identity,
    }, method="PUT")
    print("Committed " + result["commit"]["html_url"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Commit only in the daily fallback window")
    args = parser.parse_args()
    run(GitHub(credentials()), datetime.now(IST), write=args.write)
