"""Print the human-readable text inside each key widget SVG to confirm real data."""

import re
import urllib.request

CHECKS = {
    "profile-details": "https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=masmbull&theme=github_dark",
    "stats": "https://github-profile-summary-cards.vercel.app/api/cards/stats?username=masmbull&theme=github_dark",
    "streak": "https://streak-stats.demolab.com/?user=masmbull&theme=dark&hide_border=true&background=0F2027",
    "header-banner": (
        "https://capsule-render.vercel.app/api?type=waving&color=0:0F2027,50:203A43,100:D4AF37&height=210"
        "&section=header&text=SHOHIBUL%20ANWAR&fontSize=44&fontColor=FFFFFF&fontAlignY=36"
        "&desc=Full-Stack%20Developer&descAlignY=56&descSize=18&animation=fadeIn"
    ),
    "contribution-chart": "https://ghchart.rshah.org/D4AF37/masmbull",
    "skillicons": "https://skillicons.dev/icons?i=ts,js,php,python,html,css,nodejs&theme=dark",
}

for name, url in CHECKS.items():
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    svg = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    texts = [t.strip() for t in re.findall(r">([^<>]{3,40})<", svg) if t.strip()][:12]
    print(f"--- {name} ({len(svg)} bytes) ---")
    print(" | ".join(texts) or "(no text nodes)")
    print()