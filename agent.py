"""Bounded donor-guidance logic separated from the Streamlit interface."""

from __future__ import annotations

import re
from typing import Any


CAUSE_ALIASES = {
    "education": ["education", "educational", "schooling", "learning", "girls' education", "girl child education"],
    "children": ["children", "child", "kids"],
    "child rights": ["child rights", "children's rights", "child protection"],
    "nutrition": ["nutrition", "malnutrition", "food security"],
    "health": ["healthcare", "health care", "health", "medical care", "eye health", "eye care"],
    "elderly": ["older people", "older adults", "senior citizens", "elderly", "seniors"],
    "livelihoods": ["livelihood", "livelihoods", "employment", "job skills", "women's livelihoods", "self employment"],
    "disaster relief": ["disaster relief", "disaster response", "emergency relief"],
    "community development": ["community development", "rural development", "community support"],
    "women": ["women's empowerment", "women empowerment", "women workers", "women's rights"],
    "disability inclusion": ["disability inclusion", "disability rights", "visual impairment", "people with disabilities"],
}

PROGRAM_ALIASES = {
    "learning support": ["learning support", "tutoring", "remedial education", "foundational learning"],
    "girls' education": ["girls' education", "girl child education", "girls education"],
    "school meals": ["school meals", "midday meals", "mid-day meals", "school lunch"],
    "teaching": ["teaching", "classroom education", "classroom teaching"],
    "nutrition": ["nutrition", "nutrition support", "food support"],
    "healthcare": ["healthcare", "health care", "medical care"],
    "eye health": ["eye health", "eye care", "vision care", "sight care"],
    "elder care": ["elder care", "agecare", "aged care"],
    "advocacy": ["advocacy", "rights advocacy"],
    "disaster response": ["disaster response", "disaster relief", "emergency response"],
    "livelihoods": ["livelihood", "livelihoods", "job skills", "employment support"],
    "life skills": ["life skills", "life skills education"],
    "employability skilling": ["employability skilling", "skills training", "job training", "vocational training"],
    "inclusive education": ["inclusive education", "special education"],
    "material support": ["material support", "clothing", "essential supplies"],
}

LOCATION_ALIASES = {
    "india": ["india", "indian"],
    "andhra pradesh": ["andhra pradesh"],
    "arunachal pradesh": ["arunachal pradesh"],
    "assam": ["assam"],
    "bihar": ["bihar"],
    "chhattisgarh": ["chhattisgarh"],
    "goa": ["goa"],
    "gujarat": ["gujarat"],
    "haryana": ["haryana"],
    "himachal pradesh": ["himachal pradesh"],
    "jharkhand": ["jharkhand"],
    "karnataka": ["karnataka"],
    "tamil nadu": ["tamil nadu"],
    "kerala": ["kerala"],
    "maharashtra": ["maharashtra"],
    "madhya pradesh": ["madhya pradesh"],
    "manipur": ["manipur"],
    "meghalaya": ["meghalaya"],
    "mizoram": ["mizoram"],
    "nagaland": ["nagaland"],
    "odisha": ["odisha", "orissa"],
    "punjab": ["punjab"],
    "rajasthan": ["rajasthan"],
    "sikkim": ["sikkim"],
    "telangana": ["telangana"],
    "tripura": ["tripura"],
    "uttar pradesh": ["uttar pradesh"],
    "uttarakhand": ["uttarakhand", "uttaranchal"],
    "west bengal": ["west bengal"],
    "andaman and nicobar islands": ["andaman and nicobar islands"],
    "chandigarh": ["chandigarh"],
    "dadra and nagar haveli and daman and diu": ["dadra and nagar haveli and daman and diu"],
    "delhi": ["delhi", "new delhi"],
    "jammu and kashmir": ["jammu and kashmir"],
    "ladakh": ["ladakh"],
    "lakshadweep": ["lakshadweep"],
    "puducherry": ["puducherry", "pondicherry"],
    "mumbai": ["mumbai"],
    "bengaluru": ["bengaluru", "bangalore"],
    "kolkata": ["kolkata"],
    "chennai": ["chennai"],
}


def _find_alias(text: str, aliases: dict[str, list[str]]) -> str | None:
    candidates = sorted(
        ((alias, canonical) for canonical, values in aliases.items() for alias in values),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for alias, canonical in candidates:
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, flags=re.IGNORECASE):
            return canonical
    return None


def parse_preferences(message: str, current: dict[str, str] | None = None) -> dict[str, str]:
    """Extract supported preference categories while retaining unchanged session values."""
    prefs = dict(current or {"cause": "", "location": "", "program": ""})
    text = message.lower().strip()
    for key, alias_map in (("cause", CAUSE_ALIASES), ("program", PROGRAM_ALIASES), ("location", LOCATION_ALIASES)):
        found = _find_alias(text, alias_map)
        if found:
            prefs[key] = found
    return prefs


def requested_program_matches(requested: str, program_tags: list[str]) -> bool:
    if not requested:
        return True
    canonical = requested.lower()
    requested_aliases = set(PROGRAM_ALIASES.get(canonical, [canonical]))
    normalized_tags = {tag.strip().lower() for tag in program_tags}
    for tag in normalized_tags:
        tag_aliases = set(PROGRAM_ALIASES.get(tag, [tag]))
        if requested_aliases & tag_aliases or canonical in tag or tag in canonical:
            return True
    return False


def search_records(prefs: dict[str, str], records: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    """Filter by every supplied preference and rank transparent field matches."""
    matches: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        cause_tags = [v.strip().lower() for v in (record.get("causes") or "").split(";") if v.strip()]
        program_tags = [v.strip().lower() for v in (record.get("program_types") or "").split(";") if v.strip()]
        location_tags = [v.strip().lower() for v in (record.get("locations") or "").split(";") if v.strip()]
        cause = (prefs.get("cause") or "").lower()
        program = (prefs.get("program") or "").lower()
        location = (prefs.get("location") or "").lower()

        cause_match = not cause or any(cause == tag or cause in tag or tag in cause for tag in cause_tags)
        program_match = requested_program_matches(program, program_tags)
        if not cause_match or not program_match:
            continue

        score = (3 if cause else 0) + (4 if program else 0)
        if location:
            # Explicit places require explicit dataset coverage. “Multiple states” is not enough.
            location_match = any(location == tag or location in tag for tag in location_tags)
            if not location_match:
                continue
            score += 2
        if score:
            matches.append((score, record))

    matches.sort(key=lambda item: (-item[0], str(item[1].get("name", "")).casefold()))
    return [dict(record, score=score) for score, record in matches[:limit]]


def clarification_needed(prefs: dict[str, str], already_clarified: bool) -> str | None:
    """Return a short reason when the agent should ask the donor a follow-up."""
    if already_clarified:
        return None
    if not prefs.get("cause") and not prefs.get("program"):
        return "cause"
    broad_causes = {"education", "children", "health", "elderly", "community development", "livelihoods", "women", "disability inclusion"}
    if prefs.get("cause") in broad_causes and not prefs.get("program"):
        return "program"
    return None
