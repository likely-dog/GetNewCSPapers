import json
import re
from pathlib import Path
from typing import Optional, Tuple

VENUE_MAP_PATH = Path("getnewcspapers/venue/ccf_venues.json")


def load_venue_map():
    with open(VENUE_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_from_comment(comment: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not comment:
        return None, None, None
    text = comment.lower()
    m = re.search(r"(under review at|submitted to|在审|投稿至)\\s*([a-zA-Z&\\-\\s]+)\\s*(\\d{4})?", text)
    if not m:
        return None, None, None
    name = m.group(2).strip()
    year = m.group(3) if m.group(3) else None
    return name, year, "under_review"


def map_ccf_level(venue_name: Optional[str]):
    if not venue_name:
        return None, None
    m = load_venue_map()
    key = venue_name.strip()
    key_upper = key.upper()
    for k, v in m.items():
        if k.upper() == key_upper:
            return v["level"], v["direction"]
    return None, None
