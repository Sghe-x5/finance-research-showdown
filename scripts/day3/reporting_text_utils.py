"""Stdlib-only SEC submission/exhibit text helpers for Day 3 audits."""

import html
import re


SCHEDULING_PATTERNS = (
    r"schedules? (?:earnings )?release",
    r"schedules? release of .*results",
    r"will (?:release|report|announce) (?:its )?financial results",
    r"plans? to (?:release|report|announce) (?:its )?financial results",
)
DIVIDEND_PATTERNS = (
    r"declares? (?:a )?(?:quarterly )?(?:cash )?(?:dividend|distribution)",
    r"dividend declaration",
)
ACTUAL_RESULTS_PATTERNS = (
    r"net investment income", r"net asset value(?: per share)?",
    r"NAV per share", r"earnings per share", r"financial highlights",
)
RELEASE_PATTERNS = (
    r"(?:announces?|reports?|reported) .*financial results",
    r"financial results for the .*quarter ended",
    r"preliminary .*net asset value", r"estimated .*net asset value",
)


def normalize_html(raw):
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", raw, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_submission_documents(raw):
    documents = []
    for block in re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", raw, re.I | re.S):
        def field(name):
            match = re.search(rf"<{name}>([^\r\n<]+)", block, re.I)
            return match.group(1).strip() if match else ""

        text_match = re.search(r"<TEXT>(.*)", block, re.I | re.S)
        documents.append({
            "type": field("TYPE"), "filename": field("FILENAME"),
            "description": field("DESCRIPTION"),
            "text": normalize_html(text_match.group(1) if text_match else block),
        })
    return documents


def classify_exhibit_text(text):
    lower = text.lower()
    scheduling = any(re.search(pattern, lower) for pattern in SCHEDULING_PATTERNS)
    dividend = any(re.search(pattern, lower) for pattern in DIVIDEND_PATTERNS)
    actual_metrics = sum(bool(re.search(pattern, lower)) for pattern in ACTUAL_RESULTS_PATTERNS)
    release_language = any(re.search(pattern, lower) for pattern in RELEASE_PATTERNS)
    has_numbers = bool(re.search(r"\$\s?\d|\b\d+\.\d+\b", lower))
    if scheduling and actual_metrics < 2:
        return False, "", "scheduling announcement; future results date only"
    if dividend and actual_metrics < 2:
        return False, "", "dividend/distribution announcement without results or NAV"
    if actual_metrics >= 2 and has_numbers:
        event_type = "8-K_EX-99_RESULTS" if release_language else "8-K_EX-99_NAV"
        return True, event_type, ""
    return False, "", "Item 2.02 exhibit lacks verified quarterly results/NAV metrics"
