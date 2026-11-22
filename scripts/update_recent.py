#!/usr/bin/env python3
"""Update the README's recent-activity section from public repositories.

The public events feed is not a usable source: it drops pushes made while a
repository was private and returns PushEvents without commit data. Instead,
list the public repositories by push time and show the latest commit on each
default branch.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

USER = "AshtonVaughan"
SELF_REPO = f"{USER}/{USER}"
README = Path("README.md")
START = "<!-- RECENT_START -->"
END = "<!-- RECENT_END -->"
LIMIT = 6
CANDIDATES = 15
SUBJECT_MAX = 84
# Personal pages and disposable test repositories that are not project work.
SKIP = {"for-keeley", "taralani-countdown", "s0d-canary", "ucp-agent-profile"}
PLACEHOLDER_SUBJECTS = {"initial commit", "first commit"}
MERGE_SUBJECT = re.compile(r"^Merge (pull request|branch) ")
MARKDOWN_SPECIALS = re.compile(r"([\\`*_\[\]<>|])")


def gh_json(path: str) -> Any:
    result = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def fetch_repos() -> list[dict[str, Any]]:
    repos = gh_json(f"users/{USER}/repos?type=owner&sort=pushed&per_page=100")
    return [
        repo
        for repo in repos
        if not repo["fork"]
        and not repo["archived"]
        and not repo["private"]
        and repo["full_name"] != SELF_REPO
        and repo["name"] not in SKIP
    ][:CANDIDATES]


def commit_subject(message: str) -> str:
    """First line of a commit message, or the PR title for a merge commit."""
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    if not lines:
        return ""
    subject = lines[0]
    if MERGE_SUBJECT.match(subject) and len(lines) > 1:
        subject = lines[1]
    if len(subject) > SUBJECT_MAX:
        subject = subject[: SUBJECT_MAX - 3].rstrip() + "..."
    return MARKDOWN_SPECIALS.sub(r"\\\1", subject)


def latest_commit(full_name: str) -> tuple[str, str] | None:
    """Return (date, subject) for the head of the default branch."""
    try:
        commits = gh_json(f"repos/{full_name}/commits?per_page=1")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None  # empty repository or transient failure
    if not commits:
        return None
    commit = commits[0]["commit"]
    subject = commit_subject(commit["message"])
    if not subject or subject.lower() in PLACEHOLDER_SUBJECTS:
        return None  # a repository stub says nothing about recent work
    return commit["committer"]["date"][:10], subject


def format_recent(repos: list[dict[str, Any]]) -> str:
    entries: list[tuple[str, str, str, str]] = []
    for repo in repos:
        found = latest_commit(repo["full_name"])
        if found:
            date, subject = found
            entries.append((date, repo["name"], repo["html_url"], subject))
    entries.sort(key=lambda entry: entry[0], reverse=True)
    rows = [
        f"- `{date}` &nbsp; [{name}]({url}) &nbsp; {subject}"
        for date, name, url, subject in entries[:LIMIT]
    ]
    return "\n".join(rows) if rows else "_nothing public yet_"


def update_readme(content: str) -> bool:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"markers {START} / {END} not found in {README}")
    new_block = f"{START}\n\n{content}\n\n{END}"
    new_text = pattern.sub(lambda _: new_block, text)
    if new_text == text:
        return False
    README.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    changed = update_readme(format_recent(fetch_repos()))
    print("README updated" if changed else "README already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
