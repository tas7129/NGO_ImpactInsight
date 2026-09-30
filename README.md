# NGO ImpactGuide

An offline-first, locally run Agentic AI college project for helping donors discover and compare nonprofit organizations from a curated dataset. It includes a guided donor assistant, a searchable directory with side-by-side comparison, and a local dataset manager. The assistant asks for clarification when needed, searches records, explains preference matches, shows source links and dates, and refreshes suggestions when preferences change. Its “Agent actions this turn” panel makes the selected actions visible without exposing private chain-of-thought.

This application is for decision support. It does not certify organizations, verify their current status, measure donation impact, or process/contact donations. It runs on the student's computer in a browser at a local address; it does not require a hosted backend. After setup, core search, browsing, and data management work without an internet connection. Source links need internet when opened; Ollama is optional.

The interface uses a light, colorful theme. Its community banner is an AI-generated illustration for visual context; it does not depict the listed organizations or their beneficiaries.

## Run locally

Requires Python 3.10 or newer. On your Mac, use `python3.14` explicitly so the system Python 3.9 is not selected. On Windows, create the environment with `py -3.14 -m venv .venv` and activate it with `.venv\\Scripts\\Activate.ps1`.

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run ngo_impactguide.py
```

## Run the standalone webpage (no Streamlit)

The Flask version provides the guided donor assistant and searchable NGO directory in a normal browser page. It uses the same curated CSV/SQLite data and offline agent rules; it does not require Streamlit, an LLM account, external font downloads, or internet access after Flask is installed. The Streamlit version above remains available as a separate interface.

On macOS, open Terminal and run:

```bash
cd ~/Desktop/AgenticAI/NGO_ImpactGuide
python3.14 -m venv .venv-web
source .venv-web/bin/activate
python -m pip install -r requirements-web.txt
python web_app.py
```

Then open **http://127.0.0.1:5000** in Safari, Chrome, or Brave. Keep the Terminal window open while using the page. To stop it, press **Control+C** in Terminal. The next time, run:

```bash
cd ~/Desktop/AgenticAI/NGO_ImpactGuide
source .venv-web/bin/activate
python web_app.py
```

If `python3.14` is not available, use the Python launcher you installed (for example, `python3`), provided it is Python 3.10 or newer. On Windows, create the environment with `py -3 -m venv .venv-web`, activate it with `.venv-web\\Scripts\\Activate.ps1`, then install `requirements-web.txt` and run `python web_app.py`.

This is a local website: the Flask process serves it from your computer. Other people cannot open it from the internet unless you deploy it to a hosting service. The standalone webpage currently includes guided recommendations and directory search; local dataset editing remains in the Streamlit interface.

## One-link evaluation website

The `site/` folder contains the static browser version for evaluators. It opens as a normal webpage and includes the guided assistant, NGO directory search/filtering, comparison of up to three records, an explanation of the agent workflow, project limitations, and report/presentation downloads. It uses only HTML, CSS, JavaScript, and bundled JSON/image/document files. It does not need Python, Flask, Streamlit, Ollama, or a local terminal when hosted.

### Publish it with Cloudflare Pages

Cloudflare Pages can connect to this private GitHub repository and host the static files. The published site is publicly accessible even though this source repository remains private; its webpage code, sample records, report, and presentation can be viewed or downloaded by site visitors. Do not put passwords, API keys, or private records in `site/`.

1. Sign in to Cloudflare and open **Workers & Pages**.
2. Select **Create application**, then **Pages** and **Import an existing Git repository**.
3. Connect GitHub and grant Cloudflare access to the `NGO_ImpactInsight` repository.
4. Select the `main` branch.
5. Set the build command to `exit 0` and the build output directory to `site`.
6. Select **Save and Deploy**. Cloudflare will provide a `*.pages.dev` URL. Open it on your phone or computer to confirm the evaluator view, then share that URL.

Later pushes to `main` update the website automatically. The hosted demo is read-only: donor preferences last for the current page session, and changing the shared NGO dataset requires publishing an updated `site/data/organizations.json`. The optional Ollama model and local database editor are part of the Python edition, not this simple public demo.

The app creates `data/ngo_impactguide.db` from the bundled CSV on first run. New starter records are added once when the app upgrades an existing database; locally edited records are preserved. Added or edited records are stored in this local database. It is ignored by Git; deleting it restores the starter records from the CSV.

## Optional local LLM

The core workflow works offline using a bounded preference vocabulary and decision controller. To add local-model-assisted preference interpretation and grounded summaries, install [Ollama](https://ollama.com), download a model supported by your computer, start Ollama, and set `OLLAMA_MODEL` before launching the app. The model output is constrained to supported preference labels, and search remains deterministic over the local dataset. Example:

```bash
ollama pull qwen2.5:3b
OLLAMA_MODEL=qwen2.5:3b streamlit run ngo_impactguide.py
```

Without Ollama, the app uses deterministic preference parsing and summaries from the retrieved NGO records. The agent still performs clarification, search, comparison, and refresh actions. With Ollama enabled, it interprets natural-language preferences and drafts an overview from retrieved evidence; review factual details in the linked organization sources.

## Data and sources

`data/ngo_dataset.csv` contains 12 starter records. Source links point to organization websites and program pages. Check each page before using the data in a formal submission, record the review date, and update `docs/data_sources.md`. Coverage labels remain broad where current state-level service could not be confirmed. The sample records intentionally avoid impact scores and unverified claims.

## Features

- **Guided assistant:** clarify donor preferences, search records, and refresh suggestions when preferences change; show the tools/actions taken.
- **Browse and compare:** search and filter the local directory, then compare up to three records side by side.
- **Manage local data:** add, edit, or delete NGO records in the local SQLite database.
- **Optional local LLM:** Ollama can normalize natural-language preferences and draft a brief evidence-grounded overview; deterministic rules keep the full workflow available without it.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

The tests cover supported preference aliases, clarification decisions, strict location filtering, database upgrades, end-to-end assistant behavior, and LLM outage fallback. See `docs/test_results.md` for the latest run summary.

## Agent workflow

1. Parse donor preferences from the request and current session.
2. Ask one follow-up question when cause or program intent is too broad.
3. Search the curated SQLite records using structured fields.
4. Rank by transparent preference matches and prepare a comparison.
5. Show the source links, source dates, and missing-data notices.
6. Re-run search when the donor updates a preference.

## Project structure

See `docs/architecture.md` for modules, data fields, scope, and evaluation notes. The report and presentation are available at `docs/NGO_ImpactGuide_Project_Report.docx` and `docs/NGO_ImpactGuide_Presentation_College.pptx`; detailed automated results are in `docs/test_results.md`.
