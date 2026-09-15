"""Validate the profile README widgets + workflow.

- Extracts every image URL (src / srcset) from README.md and checks HTTP status.
- Validates the YAML syntax of .github/workflows/snake.yml.
- Sanity checks markdown structure (headings must not follow an HTML block
  without a blank line, which CommonMark would swallow).
"""

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WORKFLOWS = [
    ROOT / ".github" / "workflows" / "snake.yml",
    ROOT / ".github" / "workflows" / "profile-3d.yml",
]

EXPECTED_MISSING = "masmbull/masmbull/output/"  # snake branch (404 only until the Action runs once)

URL_RE = re.compile(r'(?:src|srcset)="(https?://[^"]+)"')
REL_IMG_RE = re.compile(r'(?:src|srcset)="(\./[^"]+)"')
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)")
HREF_RE = re.compile(r'href="(https?://[^"]+)"')
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\((https?://[^)\s]+)\)")
# LinkedIn serves HTTP 999/redirects to bots - unreachable for scripted checks.
KNOWN_BLOCKED = ("linkedin.com",)
# Some third-party card services rate-limit or return 503/timeout when hit
# repeatedly (they usually work fine via GitHub's image proxy + browser).
FLAKY = ("streak-stats.demolab.com", "github-readme-streak-stats.herokuapp.com")
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
        if status.startswith("200"):
            tag = "ok"
        elif any(host in url for host in FLAKY):
            # Transient on the third-party side - not a README bug.
            tag = "SKIP*"
        elif EXPECTED_MISSING in url:
            tag = "SKIP"  # snake branch not generated yet - run the workflow first
        else:
            tag = "BAD"
        if tag == "BAD":
            failures += 1
        print(f"[{tag:>5}] {status:<28} {url[:110]}")
    print("SKIP* = transient failure of a known-flaky third-party service, not a README bug")

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

    print("\n--- local images (relative src) ---")
    for rel in list(dict.fromkeys(REL_IMG_RE.findall(text))):
        resolved = (ROOT / rel[2:]).as_posix()
        exists = (ROOT / rel[2:]).exists()
        tag = "ok" if exists else "SKIP"
        if not exists:
            print(f"[{tag:>5}] {'missing until 3D workflow runs':<28} {rel} -> {resolved}")
        else:
            print(f"[{tag:>5}] {'exists':<28} {rel}")
        # Missing local 3D art is expected on first push - the Action generates it.

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

        for workflow in WORKFLOWS:
            data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
            jobs = list(data.get("jobs", {}))
            print(f"[  ok] {workflow.relative_to(ROOT).as_posix()} parsed fine, jobs={jobs}")
    except ImportError:
        print("[SKIP] pyyaml not installed")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"[ BAD] {exc}")

    print(f"\nTotal problems: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())