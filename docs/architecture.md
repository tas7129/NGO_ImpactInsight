# Architecture and evaluation

## Local application architecture

```text
Donor (Streamlit browser UI)
        |
        v
Agent workflow (agent.py) <----> Session preferences and conversation
   |          |        |
   |          |        +----> Optional Ollama summary (retrieved records only)
   |          v
   |      Preference alias parsing and clarification policy
   v
Search and ranking (all supplied filters must match)
        |
        v
SQLite records <----> Local dataset editor
        |
        v
Comparison cards, source links, dates, and agent-action trace
```

## Data fields

Each record in `data/ngo_dataset.csv` has organization name, cause tags, broad location tags, program tags, description, source URL, source access date, and a curation note. `agent.py` contains testable preference parsing, clarification policy, alias mapping, and strict preference filtering; `ngo_impactguide.py` contains the Streamlit UI, local SQLite repository, and optional Ollama integration.

## One-link static evaluation site

The `site/` folder is a separate, static browser version designed for an evaluator to open from a hosted link. It requires no Streamlit, Flask, Python runtime, account, or backend database for the donor-facing demo.

```text
Evaluator's browser
       |
       v
Static page (site/index.html + style.css)
       |
       +----> Agent workflow (site/app.js)
       |         |-- retain preferences for the current page session
       |         |-- clarify broad or missing requests
       |         |-- choose search or follow-up action
       |         +-- show the actions taken
       |
       +----> Local JSON data (site/data/organizations.json)
       |         |-- guided shortlist
       |         +-- browse, filter, compare up to 3
       |
       +----> Public source links and project report/presentation
```

The static edition is read-only. Preference matching and shortlist generation run in browser JavaScript using bounded rules. The optional Ollama model, database editor, and persistent shared data belong to the Python edition and are not exposed by the hosted demo. Public page assets and the sample dataset can be read by anyone who can access the hosted URL.

## Agent boundary

The controller can clarify, search, compare, and refresh. Its high-level action trace is visible to donors. It cannot donate, contact organizations, certify legitimacy, or guarantee impact. The LLM is optional: when configured locally, it helps map natural-language preferences into validated canonical labels and drafts an overview from retrieved records. The tool planner, allowed labels, clarification policy, search, and ranking remain bounded Python logic, which enables offline operation.

## Suggested evaluation

Evaluate clear requests, broad requests requiring clarification, changed preferences, no-match requests, missing information, and Ollama/database failures. Record expected and actual results; report source coverage and any unsupported claims in a manually reviewed sample.
