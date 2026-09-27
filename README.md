# NGO ImpactGuide

An offline-first, locally run Agentic AI college project for helping donors discover and compare nonprofit organizations from a curated dataset. It includes a guided donor assistant, a searchable directory with side-by-side comparison, and a local dataset manager. The assistant asks for clarification when needed, searches records, explains preference matches, shows source links and dates, and refreshes suggestions when preferences change.

This application is for decision support. It does not certify organizations, verify their current status, measure donation impact, or process/contact donations. It runs on the student's computer in a browser at a local address; it does not require a hosted backend. After setup, core search, browsing, and data management work without an internet connection. Source links need internet when opened; Ollama is optional.

## Run locally

Requires Python 3.10 or newer. On your Mac, use `python3.14` explicitly so the system Python 3.9 is not selected. On Windows, create the environment with `py -3.14 -m venv .venv` and activate it with `.venv\\Scripts\\Activate.ps1`.

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run ngo_impactguide.py
```

The app creates `data/ngo_impactguide.db` from the bundled CSV on first run. Added or edited records are stored in this local database. It is ignored by Git; deleting it restores the starter records from the CSV.

## Optional local LLM

The core workflow does not depend on an LLM. To enable grounded, locally generated summaries, install [Ollama](https://ollama.com), download a model supported by your computer, start Ollama, and set `OLLAMA_MODEL` to the local model name before launching the app. Example:

```bash
ollama pull qwen2.5:3b
OLLAMA_MODEL=qwen2.5:3b streamlit run ngo_impactguide.py
```

Without Ollama, the app uses a deterministic summary generated from the retrieved NGO records. It never asks the model to invent NGO facts.

## Data and sources

`data/ngo_dataset.csv` contains a small starter dataset. Source links point to organization websites and were selected as starting points for student review. Check each page before using the data in a formal submission, record the review date, and update `data_sources.md`. The sample records intentionally avoid impact scores and unverified claims.

## Features

- **Guided assistant:** clarify donor preferences, search records, and refresh suggestions when preferences change.
- **Browse and compare:** search and filter the local directory, then compare up to three records side by side.
- **Manage local data:** add, edit, or delete NGO records in the local SQLite database.
- **Optional local LLM:** Ollama can generate brief grounded explanations; deterministic summaries work without it.

## Agent workflow

1. Parse donor preferences from the request and current session.
2. Ask one follow-up question when cause or program intent is too broad.
3. Search the curated SQLite records using structured fields.
4. Rank by transparent preference matches and prepare a comparison.
5. Show the source links, source dates, and missing-data notices.
6. Re-run search when the donor updates a preference.

## Project structure

See `docs/architecture.md` for modules, data fields, scope, and evaluation notes.
