# Test results

Last recorded run: 2026-09-28, Python 3.14.7, `python -m unittest discover -s tests -v`.

## Automated results

| Area | Cases | Passed | Failed | Result |
|---|---:|---:|---:|---|
| Preference aliases and session updates | 4 | 4 | 0 | Pass |
| Clarification and matching rules | 5 | 5 | 0 | Pass |
| Streamlit end-to-end assistant, browse/compare, data manager, migration, and fallback | 6 | 6 | 0 | Pass |
| **Total** | **15** | **15** | **0** | **Pass** |

The UI scenarios cover a broad education request and clarification, synonym handling for tutoring, preference update to Karnataka, a vague request that requires a cause, side-by-side comparison, adding a local record, fallback when the local Ollama endpoint is unavailable, and upgrading an existing SQLite database without deleting a pre-existing user record.

## Limits of this evaluation

- The tests use a curated sample dataset; they do not establish that the dataset is comprehensive.
- Source URLs and descriptions were reviewed for the starter records, but link availability is not checked automatically by the test suite.
- The unavailable-Ollama test verifies fallback behavior. It does not test generated output from an installed local model.
- No donor usability study or donation outcome evaluation has been conducted.

For a college report, present these as software test results and keep planned or unperformed manual checks separate.
