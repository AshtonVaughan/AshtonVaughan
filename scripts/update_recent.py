#!/usr/bin/env python3
"""Update the README's recent-activity section from GitHub events."""
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


def fetch_events() -> list[dict[str, Any]]:
    result = subprocess.run(
        ["gh", "api", f"users/{USER}/events/public", "--paginate"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def format_events(events: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    seen: set[tuple[str, str]] = set()
    for ev in events:
        if len(rows) >= LIMIT:
            break
        repo = ev["repo"]["name"]
        if repo == SELF_REPO:
            continue
        kind = ev["type"]
        if kind == "PushEvent":
            commits = ev["payload"].get("commits", [])
            if not commits:
                continue
            msg = commits[-1]["message"].splitlines()[0][:90]
            key = (repo, msg)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                f"- `push`     [{repo}](https://github.com/{repo}) - {msg}"
            )
        elif kind == "ReleaseEvent":
            release = ev["payload"].get("release") or {}
            tag = release.get("tag_name", "")
            rows.append(
                f"- `release`  [{repo}](https://github.com/{repo}) {tag}"
            )
        elif kind == "PullRequestEvent" and ev["payload"].get("action") == "opened":
            pr = ev["payload"]["pull_request"]
            num = pr["number"]
            title = pr["title"][:90]
            rows.append(
                f"- `PR`       [{repo}#{num}](https://github.com/{repo}/pull/{num}) {title}"
            )
        elif (
            kind == "CreateEvent"
            and ev["payload"].get("ref_type") == "repository"
        ):
            rows.append(
                f"- `new`      [{repo}](https://github.com/{repo}) created"
            )
    body = "\n".join(rows) if rows else "_no public activity yet_"
    return f"```text\n{body}\n```"


def update_readme(content: str) -> bool:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END), re.DOTALL
    )
    new_block = f"{START}\n\n{content}\n\n{END}"
    new_text = pattern.sub(new_block, text)
    if new_text == text:
        return False
    README.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    events = fetch_events()
    formatted = format_events(events)
    update_readme(formatted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
