#!/usr/bin/env python3
"""Refresh the "Latest activity" block of the profile README.

Replaces everything between <!--RECENT:START--> and <!--RECENT:END-->
with the most recently pushed public, non-fork, non-archived repositories
(plus their latest release tag, when one exists).

Usage: python3 update_readme.py [path/to/README.md]
Env:   GITHUB_REPOSITORY_OWNER (default LuisRibeiroo), GH_TOKEN (optional, raises rate limit)
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "LuisRibeiroo")
README = sys.argv[1] if len(sys.argv) > 1 else "README.md"
TOKEN = os.environ.get("GH_TOKEN")
LIMIT = 5
START, END = "<!--RECENT:START-->", "<!--RECENT:END-->"


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-updater",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise


def recent_repos():
    repos = api(f"/users/{USER}/repos?sort=pushed&per_page=30&type=owner") or []
    keep = [
        r
        for r in repos
        if not r["fork"] and not r["archived"] and r["name"].lower() != USER.lower()
    ]
    return keep[:LIMIT]


def render(repo):
    parts = [f"[**{repo['name']}**]({repo['html_url']})"]
    if repo.get("description"):
        parts.append(repo["description"].strip())
    meta = []
    if repo.get("language"):
        meta.append(f"`{repo['language']}`")
    release = api(f"/repos/{USER}/{repo['name']}/releases/latest")
    if release and release.get("tag_name"):
        meta.append(f"release {release['tag_name']}")
    meta.append(f"pushed {repo['pushed_at'][:10]}")
    return "- " + " — ".join(parts) + " · " + " · ".join(meta)


def main():
    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    if START not in text or END not in text:
        sys.exit(f"markers {START} / {END} not found in {README}")
    block = "\n".join(render(r) for r in recent_repos())
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    new = pattern.sub(lambda _: f"{START}\n{block}\n{END}", text)
    if new != text:
        with open(README, "w", encoding="utf-8") as fh:
            fh.write(new)
        print("README updated")
    else:
        print("README unchanged")


if __name__ == "__main__":
    main()
