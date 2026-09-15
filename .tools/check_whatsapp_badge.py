"""Verify the WhatsApp badge variants render the phone number correctly."""

import re
import urllib.request

CANDIDATES = {
    "plus-encoded": "https://img.shields.io/badge/WhatsApp-%2B62%20823%203653%204192-25D366?style=for-the-badge&logo=whatsapp&logoColor=white",
    "plus-literal": "https://img.shields.io/badge/WhatsApp-+62%20823%203653%204192-25D366?style=for-the-badge&logo=whatsapp&logoColor=white",
    "plain-digits": "https://img.shields.io/badge/WhatsApp-62823%203653%204192-25D366?style=for-the-badge&logo=whatsapp&logoColor=white",
    "wa-link": "https://wa.me/6282336534192",
}

for name, url in CANDIDATES.items():
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=45)
        body = resp.read()
        print(f"--- {name}: HTTP {resp.status} ({len(body)} bytes) ---")
        if "svg" in body[:400].decode("utf-8", "replace"):
            svg = body.decode("utf-8", "replace")
            texts = [t for t in re.findall(r">([^<>]+)<", svg) if t.strip()][:6]
            print("rendered text:", " | ".join(texts))
            print("contains '+62 823':", "+62 823" in svg, "| contains '+62+823':", "+62+823" in svg)
        print()
    except Exception as exc:  # noqa: BLE001
        print(f"--- {name}: FAIL {exc} ---\n")