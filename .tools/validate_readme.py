"""Validate the profile README widgets + workflow.

- Extracts every image URL (src / srcset) from README.md and checks HTTP status.
- Validates the YAML syntax of .github/workflows/snake.yml.
- Sanity checks markdown structure (headings must not follow an HTML block
  without a blank line, which CommonMark would swallow).
"""

import asyncio
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "snake.yml"

EXPECTED_MISSING = "masmbull/masmbull/output/"  # snake branch until the Action runs

URL_RE = re.compile(r'(?:src|srcset)="(https?://[^"]+)"')
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)")
HREF_RE = re.compile(r'href="(https?://[^"]+)"')
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\((https?://[^)\s]+)\)")
# LinkedIn serves HTTP 999/redirects to bots - unreachable for scripted checks.
KNOWN_BLOCKED = ("linkedin.com",)
HTML_BLOCK_START = re.compile(r"^\s*<(img|picture|div|table|source|a)\b", re.IGNORECASE)


def tag_balance_errors(text: str) -> list[str]:
    """Report unclosed/extra HTML container tags (ignores self-closing <img ... />)."""
    errors = []
    for tag in ("div", "table", "tr", "td", "picture", "a"):
        opens = len(re.findall(rf"<{tag}[\s>]", text, re.IGNORECASE))
        closes = len(re.findall(rf"</{tag}>", text, re.IGNORECASE))
        if opens != closes:
            errors.append(f"<{tag}> open={opens} close={closes}")
    return errors


def markdown_structure_errors(text: str) -> list[str]:
    errors = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            prev = lines[i - 1] if i else ""
            if prev.strip() and not prev.strip().startswith("#"):
                errors.append(f"line {i + 1}: heading lacks a blank line before it -> {line.strip()!r}")
    return errors


def http_status(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (README validator)"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read()
            return f"{resp.status} len={len(body)}"
    except Exception as exc:  # noqa: BLE001 - report any failure
        return f"FAIL {exc}"


def main() -> int:
    text = README.read_text(encoding="utf-8")
    urls = list(dict.fromkeys(URL_RE.findall(text) + MD_IMG_RE.findall(text)))
    print(f"Found {len(urls)} unique image URLs in {README.relative_to(ROOT)}\n")

    failures = 0
    for url in urls:
        status = http_status(url)
        tag = "SKIP" if EXPECTED_MISSING in url else ("ok" if status.startswith("200") else "BAD")
        if tag == "BAD":
            failures += 1
        print(f"[{tag:>4}] {status:<28} {url[:110]}")

    print("\n--- outbound links (href) ---")
    links = list(dict.fromkeys(HREF_RE.findall(text) + MD_LINK_RE.findall(text)))
    for url in links:
        if any(blocked in url for blocked in KNOWN_BLOCKED):
            print(f"[SKIP] locked for bots (authwall)   {url[:110]}")
            continue
        status = http_status(url)
        tag = "ok" if status.startswith("200") else "BAD"
        if tag == "BAD":
            failures += 1
        print(f"[{tag:>4}] {status:<28} {url[:110]}")

    print("\n--- markdown structure ---")
    errors = markdown_structure_errors(text)
    for err in errors:
        print(f"[BAD] {err}")
    if not errors:
        print("[  ok] no heading/blank-line issues")

    balance = tag_balance_errors(text)
    for err in balance:
        print(f"[BAD] unbalanced tag: {err}")
    if not balance:
        print("[  ok] HTML tags balanced")
    errors += balance
    failures += len(errors)

    print("\n--- workflow YAML ---")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        jobs = list(data.get("jobs", {}))
        print(f"[  ok] parsed fine, jobs={jobs}")
    except ImportError:
        print("[SKIP] pyyaml not installed")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"[ BAD] {exc}")

    print(f"\nTotal problems: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())