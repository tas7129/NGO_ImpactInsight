"""Flask browser interface for NGO ImpactGuide (no Streamlit required)."""

from __future__ import annotations

import csv
import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, session

from agent import clarification_needed, parse_preferences, search_records


ROOT = Path(__file__).parent
CSV_PATH = ROOT / "data" / "ngo_dataset.csv"
DB_PATH = Path(os.getenv("NGO_DATABASE_PATH", str(ROOT / "data" / "ngo_impactguide.db")))
app = Flask(__name__)
app.secret_key = os.getenv("NGO_SESSION_SECRET", "local-development-key-change-before-hosting")


def get_records() -> list[dict]:
    """Load the curated CSV once into the same local SQLite database used by the app."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ngos (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, causes TEXT NOT NULL,
                locations TEXT NOT NULL, program_types TEXT NOT NULL,
                description TEXT NOT NULL, source_url TEXT NOT NULL,
                source_accessed TEXT, notes TEXT
            )"""
        )
        conn.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        loaded = conn.execute("SELECT value FROM app_meta WHERE key='starter_data_loaded'").fetchone()
        if not loaded:
            with CSV_PATH.open(newline="", encoding="utf-8") as data_file:
                rows = list(csv.DictReader(data_file))
            existing = {row[0].strip().casefold() for row in conn.execute("SELECT name FROM ngos")}
            rows = [row for row in rows if row["name"].strip().casefold() not in existing]
            conn.executemany(
                "INSERT INTO ngos (name, causes, locations, program_types, description, source_url, source_accessed, notes) "
                "VALUES (:name, :causes, :locations, :program_types, :description, :source_url, :source_accessed, :notes)", rows
            )
            conn.execute("INSERT OR REPLACE INTO app_meta (key, value) VALUES ('starter_data_loaded', '1')")
        return [dict(row) for row in conn.execute("SELECT * FROM ngos ORDER BY name")]


def public_record(record: dict) -> dict:
    return {key: record.get(key, "") for key in ("id", "name", "causes", "locations", "program_types", "description", "source_url", "source_accessed", "notes", "score")}


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/assets/<path:filename>")
def asset(filename: str):
    return send_from_directory(ROOT / "assets", filename)


@app.get("/api/organizations")
def organizations():
    records = get_records()
    query = request.args.get("q", "").strip().casefold()
    cause = request.args.get("cause", "").strip().casefold()
    found = []
    for record in records:
        haystack = " ".join(str(record.get(key, "")) for key in ("name", "causes", "locations", "program_types", "description")).casefold()
        tags = [tag.strip().casefold() for tag in record.get("causes", "").split(";")]
        if query and query not in haystack:
            continue
        if cause and cause not in tags:
            continue
        found.append(public_record(record))
    return jsonify({"records": found, "causes": sorted({tag.strip() for row in records for tag in row["causes"].split(";") if tag.strip()})})


@app.post("/api/message")
def message():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("message", "")).strip()
    if not text:
        return jsonify({"error": "Please describe a cause or program."}), 400

    preferences = session.get("preferences", {"cause": "", "program": "", "location": ""})
    awaiting = session.get("awaiting", "")
    preferences = parse_preferences(text, preferences)
    clarification = ""
    normalized = text.casefold().strip()
    if awaiting == "program":
        if normalized in {"no preference", "any", "other"}:
            preferences["program"] = ""
        elif not preferences.get("program"):
            clarification = "I didn't recognize that program. Try learning support, school meals, teaching, healthcare, elder care, or say “no preference.”"
    elif awaiting == "cause" and not preferences.get("cause"):
        clarification = "Please name a cause such as education, children's rights, health, older people, livelihoods, or disaster relief."

    if clarification:
        return jsonify({"kind": "clarification", "reply": clarification, "preferences": preferences, "steps": ["Checked the response against supported causes and programs.", "Asked for a clearer preference because the reply was not recognized."]})

    need = clarification_needed(preferences, already_clarified=bool(awaiting))
    session["preferences"] = preferences
    if need:
        session["awaiting"] = need
        question = (
            "What cause would you like to support? Examples include education, children's rights, health, older people, livelihoods, or disaster relief."
            if need == "cause" else
            "What kind of support interests you—for example learning support, school meals, teaching, healthcare, or elder care? You can also say “no preference.”"
        )
        return jsonify({"kind": "clarification", "reply": question, "preferences": preferences, "steps": ["Parsed your stated preferences using offline rules.", "Decided one follow-up is needed before searching."]})

    session["awaiting"] = ""
    records = search_records(preferences, get_records())
    summary = (
        f"I found {len(records)} organization record(s) matching your preferences. These are relevance matches, not ratings or verification."
        if records else
        "I couldn't find a matching record in this curated dataset. Try broadening or changing your cause, program, or location."
    )
    return jsonify({"kind": "results", "reply": summary, "preferences": preferences, "records": [public_record(row) for row in records], "steps": ["Parsed your cause, program, and location preferences.", f"Searched {len(get_records())} locally stored organization records.", f"Prepared a shortlist of {len(records)} matching records.", "Kept the recommendation grounded in the dataset and included source links."]})


@app.post("/api/reset")
def reset():
    session.pop("preferences", None)
    session.pop("awaiting", None)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
