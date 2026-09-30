# Architecture and evaluation

## Architecture

```text
Donor (Streamlit UI)
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

## Agent boundary

The controller can clarify, search, compare, and refresh. Its high-level action trace is visible to donors. It cannot donate, contact organizations, certify legitimacy, or guarantee impact. The LLM is optional: when configured locally, it helps map natural-language preferences into validated canonical labels and drafts an overview from retrieved records. The tool planner, allowed labels, clarification policy, search, and ranking remain bounded Python logic, which enables offline operation.

## Suggested evaluation

Evaluate clear requests, broad requests requiring clarification, changed preferences, no-match requests, missing information, and Ollama/database failures. Record expected and actual results; report source coverage and any unsupported claims in a manually reviewed sample.
