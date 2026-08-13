"""One-off SEC company-search helper for non-traded BDC CIKs."""

import os
import re
import time
from urllib.parse import urlencode

import requests


NAMES = [
    "Blackstone Private Credit Fund",
    "HPS Corporate Lending Fund",
    "Ares Strategic Income Fund",
    "Blue Owl Credit Income",
]


def main():
    user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if "@" not in user_agent:
        raise SystemExit("Set SEC_USER_AGENT to a descriptive value with a contact email.")
    headers = {"User-Agent": user_agent}
    for name in NAMES:
        query = urlencode({"action": "getcompany", "company": name, "type": "10-Q"})
        response = requests.get(
            "https://www.sec.gov/cgi-bin/browse-edgar?" + query,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        matches = re.findall(r"CIK=(\d+)[^\"]*\"[^>]*>([^<]+)", response.text, re.I)
        print(name, matches[:5])
        time.sleep(0.15)


if __name__ == "__main__":
    main()
