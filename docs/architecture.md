# Architecture and evaluation

## Architecture

```text
Donor (Streamlit UI)
        |
        v
Agent controller <----> Short-term session state
   |         |
   |         +----> Optional local Ollama (grounded summaries only)
   v
Preference parsing -> NGO search -> Comparison/source display
                              |
                              v
                    Curated SQLite records
```

## Data fields

Each record in `data/ngo_dataset.csv` has organization name, cause tags, broad location tags, program tags, description, source URL, source access date, and a curation note.

## Agent boundary

The controller can clarify, search, compare, and refresh. It cannot donate, contact organizations, certify legitimacy, or guarantee impact. The LLM is optional and only receives retrieved records for summary generation. Search and ranking remain deterministic Python logic.

## Suggested evaluation

Evaluate clear requests, broad requests requiring clarification, changed preferences, no-match requests, missing information, and Ollama/database failures. Record expected and actual results; report source coverage and any unsupported claims in a manually reviewed sample.
