from __future__ import annotations

import csv
import os
import re
import sqlite3
import urllib.error
import urllib.request
import json
from pathlib import Path
from typing import Any

import streamlit as st


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "ngo_dataset.csv"
DB_PATH = DATA_DIR / "ngo_impactguide.db"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "").strip()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat").strip()

FIELDS = ["name", "causes", "locations", "program_types", "description", "source_url", "source_accessed", "notes"]


def connect_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ngos (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            causes TEXT NOT NULL,
            locations TEXT NOT NULL,
            program_types TEXT NOT NULL,
            description TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_accessed TEXT,
            notes TEXT
        )"""
    )
    count = conn.execute("SELECT COUNT(*) FROM ngos").fetchone()[0]
    if count == 0 and CSV_PATH.exists():
        with CSV_PATH.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        conn.executemany(
            "INSERT INTO ngos (name, causes, locations, program_types, description, source_url, source_accessed, notes) VALUES (:name, :causes, :locations, :program_types, :description, :source_url, :source_accessed, :notes)",
            rows,
        )
        conn.commit()
    return conn


def get_all_ngos() -> list[dict[str, Any]]:
    conn = connect_db()
    rows = [dict(row) for row in conn.execute("SELECT * FROM ngos ORDER BY name").fetchall()]
    conn.close()
    return rows


def save_ngo(record: dict[str, str], record_id: int | None = None) -> None:
    conn = connect_db()
    if record_id is None:
        conn.execute(
            "INSERT INTO ngos (name, causes, locations, program_types, description, source_url, source_accessed, notes) VALUES (:name, :causes, :locations, :program_types, :description, :source_url, :source_accessed, :notes)",
            record,
        )
    else:
        conn.execute(
            "UPDATE ngos SET name=:name, causes=:causes, locations=:locations, program_types=:program_types, description=:description, source_url=:source_url, source_accessed=:source_accessed, notes=:notes WHERE id=:id",
            {**record, "id": record_id},
        )
    conn.commit()
    conn.close()


def delete_ngo(record_id: int) -> None:
    conn = connect_db()
    conn.execute("DELETE FROM ngos WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def tags(value: str) -> list[str]:
    return [part.strip().lower() for part in (value or "").split(";") if part.strip()]


def parse_preferences(message: str, current: dict[str, str] | None = None) -> dict[str, str]:
    """Extract simple preference cues; preserve session fields unless explicitly updated."""
    prefs = dict(current or {"cause": "", "location": "", "program": ""})
    text = message.lower().strip()
    cause_terms = ["education", "children", "child rights", "nutrition", "health", "elderly", "older people", "livelihood", "disaster relief", "community development"]
    program_terms = ["tutoring", "learning support", "school meals", "nutrition", "teaching", "classroom education", "healthcare", "elder care", "advocacy", "disaster response", "livelihoods", "material support", "remedial education"]
    locations = ["karnataka", "tamil nadu", "kerala", "maharashtra", "delhi", "mumbai", "bengaluru", "bangalore", "kolkata", "chennai", "india"]

    for term in sorted(cause_terms, key=len, reverse=True):
        if term in text:
            prefs["cause"] = term
            break
    for term in sorted(program_terms, key=len, reverse=True):
        if term in text:
            prefs["program"] = term
            break
    for place in sorted(locations, key=len, reverse=True):
        if place in text:
            prefs["location"] = place
            break
    return prefs


def needs_clarification(prefs: dict[str, str], records: list[sqlite3.Row]) -> bool:
    # Broad cause requests with multiple possible program interpretations get clarification.
    broad = {"education", "children", "health", "elderly", "community development"}
    return bool(prefs.get("cause")) and not prefs.get("program") and prefs.get("cause") in broad and not st.session_state.get("clarified")


def search_ngos(prefs: dict[str, str]) -> list[dict[str, Any]]:
    conn = connect_db()
    records = [dict(row) for row in conn.execute("SELECT * FROM ngos ORDER BY name").fetchall()]
    conn.close()
    matches: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        score = 0
        cause_match = not prefs.get("cause") or any(
            prefs["cause"] in tag or tag in prefs["cause"] for tag in tags(record["causes"])
        )
        program_match = not prefs.get("program") or any(
            prefs["program"] in tag or tag in prefs["program"] for tag in tags(record["program_types"])
        )
        if not cause_match or not program_match:
            continue
        if prefs.get("cause"):
            score += 3
        if prefs.get("program"):
            score += 4
        if prefs.get("location"):
            location = prefs["location"]
            rec_locations = tags(record["locations"])
            if location == "india" and any("india" in tag for tag in rec_locations):
                score += 2
            elif any(location in tag for tag in rec_locations):
                score += 2
            else:
                # A broad “multiple states” label cannot prove operation in an exact state.
                continue
        if score > 0:
            matches.append((score, record))
    matches.sort(key=lambda item: (-item[0], item[1]["name"]))
    return [dict(score=score, **record) for score, record in matches[:5]]


def ollama_summary(prefs: dict[str, str], records: list[dict[str, Any]]) -> str | None:
    if not OLLAMA_MODEL or not records:
        return None
    evidence = [{k: r[k] for k in FIELDS} for r in records]
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": "Explain how the supplied records match the donor's preferences. Use only the supplied records. Do not claim that an NGO is trustworthy, verified, or more impactful. If information is missing, say so. Keep it under 100 words."},
            {"role": "user", "content": json.dumps({"preferences": prefs, "records": evidence}, ensure_ascii=False)},
        ],
        "options": {"temperature": 0.1},
    }
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            body = json.loads(response.read().decode())
        return body.get("message", {}).get("content", "").strip() or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None


def deterministic_explanation(prefs: dict[str, str], records: list[dict[str, Any]]) -> str:
    if not records:
        return "I could not find a matching record in the current curated dataset. You can broaden the cause or location and try again."
    return f"I found {len(records)} organization record(s) that match some of your stated preferences. The comparison below shows which program details and sources are available. A match indicates relevance to your request, not a rating or verification."


def handle_message(message: str) -> None:
    current = st.session_state.preferences
    prefs = parse_preferences(message, current)
    # On a reset/initial prompt, clear clarification status. A follow-up is intentionally marked clarified.
    if st.session_state.awaiting_clarification:
        answer = message.lower()
        program_options = ["school meals", "learning support", "remedial education", "teaching", "classroom education", "nutrition", "healthcare", "advocacy", "elder care", "other"]
        for option in program_options:
            if option in answer:
                prefs["program"] = option
                break
        st.session_state.clarified = True
        st.session_state.awaiting_clarification = False
    else:
        st.session_state.clarified = False

    st.session_state.preferences = prefs
    records = search_ngos(prefs)
    if needs_clarification(prefs, records):
        st.session_state.awaiting_clarification = True
        st.session_state.messages.append({"role": "assistant", "content": "To narrow this down, what kind of support are you most interested in—for example learning support, school meals, or teaching?"})
        return

    explanation = ollama_summary(prefs, records) or deterministic_explanation(prefs, records)
    st.session_state.results = records
    st.session_state.messages.append({"role": "assistant", "content": explanation, "results": records})


st.set_page_config(page_title="NGO ImpactGuide", page_icon="🤝", layout="wide")
st.title("NGO ImpactGuide")
st.caption("A local donor-guidance system for discovering and comparing nonprofit programs.")

with st.sidebar:
    st.subheader("About this prototype")
    st.write("Suggestions reflect donor preferences and the records available here. They are not an NGO rating, certification, or guarantee of impact.")
    st.write("**Dataset:** local SQLite database · editable by the project owner")
    st.write("**LLM:** " + (f"Ollama ({OLLAMA_MODEL})" if OLLAMA_MODEL else "Optional; deterministic summaries active"))
    if st.button("Start a new guidance session"):
        for key in ["messages", "preferences", "results", "awaiting_clarification", "clarified"]:
            st.session_state.pop(key, None)
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.preferences = {"cause": "", "location": "", "program": ""}
    st.session_state.results = []
    st.session_state.awaiting_clarification = False
    st.session_state.clarified = False

page = st.segmented_control(
    "Project area",
    ["Guided assistant", "Browse and compare", "Manage local data"],
    default="Guided assistant",
    key="project_area",
)

if page == "Browse and compare":
    st.subheader("Browse nonprofit records")
    st.write("Search the local dataset, filter by cause, and compare selected organizations.")
    all_records = get_all_ngos()
    all_causes = sorted({tag for record in all_records for tag in tags(record["causes"])})
    left, right = st.columns([2, 1])
    with left:
        query = st.text_input("Search organizations or programs", placeholder="Try education, meals, or an organization name", key="browse_query")
    with right:
        cause_filter = st.selectbox("Cause", ["All causes", *all_causes], key="browse_cause")
    filtered = []
    query_lower = query.strip().lower()
    for record in all_records:
        searchable = " ".join(str(record.get(k, "")) for k in ["name", "causes", "locations", "program_types", "description"]).lower()
        if query_lower and query_lower not in searchable:
            continue
        if cause_filter != "All causes" and cause_filter not in tags(record["causes"]):
            continue
        filtered.append(record)

    st.caption(f"{len(filtered)} organization record(s) found")
    selected_names = st.multiselect("Select up to three organizations to compare", [r["name"] for r in filtered], max_selections=3, key="compare_selection")
    if selected_names:
        chosen = [r for r in filtered if r["name"] in selected_names]
        st.subheader("Side-by-side comparison")
        headers = st.columns(len(chosen))
        for column, record in zip(headers, chosen):
            with column:
                st.markdown(f"#### {record['name']}")
                st.write(record["description"])
                st.markdown(f"**Causes:** {record['causes'].replace(';', ', ')}")
                st.markdown(f"**Programs:** {record['program_types'].replace(';', ', ')}")
                st.markdown(f"**Locations:** {record['locations'].replace(';', ', ')}")
                st.markdown(f"**Source date:** {record['source_accessed'] or 'Not recorded'}")
                st.markdown(f"[Open source]({record['source_url']})")
    for record in filtered:
        with st.expander(record["name"]):
            st.write(record["description"])
            st.markdown(f"**Causes:** {record['causes'].replace(';', ', ')}")
            st.markdown(f"**Programs:** {record['program_types'].replace(';', ', ')}")
            st.markdown(f"**Locations:** {record['locations'].replace(';', ', ')}")
            st.markdown(f"[Open source]({record['source_url']})")

elif page == "Manage local data":
    st.subheader("Manage the local NGO dataset")
    st.warning("This editor is intended for the project owner on a local computer. Review each source before adding or changing records.")
    all_records = get_all_ngos()
    st.caption(f"{len(all_records)} record(s) stored in the local database")
    record_to_edit = st.selectbox("Choose a record to edit (or add a new one)", ["Add a new record", *[r['name'] for r in all_records]], key="edit_record")
    existing = next((r for r in all_records if r["name"] == record_to_edit), None)
    with st.form("ngo_record_form"):
        name = st.text_input("Organization name", value=existing["name"] if existing else "")
        causes = st.text_input("Cause tags (separate with semicolons)", value=existing["causes"] if existing else "")
        locations = st.text_input("Locations served (separate with semicolons)", value=existing["locations"] if existing else "")
        programs = st.text_input("Program types (separate with semicolons)", value=existing["program_types"] if existing else "")
        description = st.text_area("Short description", value=existing["description"] if existing else "")
        source_url = st.text_input("Source URL", value=existing["source_url"] if existing else "")
        source_date = st.text_input("Source access date (YYYY-MM-DD)", value=existing["source_accessed"] if existing else "")
        notes = st.text_area("Data note or limitation", value=existing["notes"] if existing else "")
        submitted = st.form_submit_button("Save record", type="primary")
    if submitted:
        valid_url = source_url.startswith("https://") or source_url.startswith("http://")
        if not all([name.strip(), causes.strip(), locations.strip(), programs.strip(), description.strip()]) or not valid_url:
            st.error("Enter a name, cause, location, program, description, and a valid http(s) source URL.")
        else:
            save_ngo({"name": name.strip(), "causes": causes.strip(), "locations": locations.strip(), "program_types": programs.strip(), "description": description.strip(), "source_url": source_url.strip(), "source_accessed": source_date.strip(), "notes": notes.strip()}, existing["id"] if existing else None)
            st.success("Record saved in the local database.")
            st.rerun()
    if existing and st.button("Delete selected record", type="secondary"):
        delete_ngo(existing["id"])
        st.success("Record deleted.")
        st.rerun()

elif page == "Guided assistant":
    st.write("Tell the assistant what cause or program you care about. It will clarify broad requests, search the local records, and explain available matches.")

    for item in st.session_state.messages:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item["role"] == "assistant" and item.get("results"):
                for record in item["results"]:
                    with st.expander(record["name"]):
                        st.write(record["description"])
                        st.markdown(f"**Causes:** {record['causes'].replace(';', ', ')}")
                        st.markdown(f"**Programs:** {record['program_types'].replace(';', ', ')}")
                        st.markdown(f"**Locations listed:** {record['locations'].replace(';', ', ')}")
                        st.markdown(f"**Source accessed:** {record['source_accessed'] or 'Date not recorded'}")
                        st.markdown(f"[View source]({record['source_url']})")
                        if record.get("notes"):
                            st.caption("Data note: " + record["notes"])

    if not st.session_state.messages:
        st.info("Try: “I want to support education in India” or “I care about older people and healthcare.”")

    prompt = st.chat_input("Describe a cause, location, or program preference")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        handle_message(prompt)
        st.rerun()

    with st.expander("Current session preferences"):
        st.json({k: v or "Not specified" for k, v in st.session_state.preferences.items()})
