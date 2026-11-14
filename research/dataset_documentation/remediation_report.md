# Controlled Remediation Report

**Date:** 2026-11-13
**Repository:** `Jnanika-19/Explainable-and-Recency-Aware-Intelligent-Bug-Assignment-System`
**Branch:** `feature/jdt-dataset-collection`
**Status:** Local remediation prepared for another read-only pre-commit audit. Approval is still required before any release action.

## Scope and safeguards

All changes below address the findings in the
[second pre-commit audit](second_pre_commit_audit_report.md). No files were
staged, committed, pushed, reset, rebased, amended, or removed. No raw or
processed dataset was edited, regenerated, moved, or overwritten; no extraction,
collection, or dataset-writing script was run. The identity-linked
`jdt_workload_replay_mismatch_analysis.md` was not edited or deleted and remains
excluded from the proposed public release. No stable pseudonymous developer
identifier is reproduced in this report.

## Corrections and files changed

| File | Correction |
|---|---|
| [README.md](../../README.md) | Replaced the `data/` layout references with the actual `dataset/` layout; distinguished broad README folder ownership from the separate four-member dataset handover matrix; documented `.venv-sbert` setup and VS Code interpreter selection; described recency decay as a reusable utility, not an evaluated recommender. |
| [settings.json](../../.vscode/settings.json) | Set the Windows workspace default interpreter to `.venv-sbert\Scripts\python.exe`. |
| [point_in_time.py](../../scoring_engine/workload/point_in_time.py) | A reassignment with omitted severity now retains the bug's previously known severity; an explicit severity still replaces it. |
| [explainability.py](../../scoring_engine/final_scoring/explainability.py) | Added a finite-value and sum-consistency guard so feature contributions reconcile with the supplied `FeatureScore.score`; inconsistent empty-score decompositions are rejected. |
| [point_in_time.py](../../bug_similarity/retrieval/point_in_time.py) | Bound each fitted retriever to a query bug and excluded that bug before TF-IDF fitting. Search now requires a timezone-aware query-text availability timestamp strictly before the prediction cutoff and rejects a different query ID. |
| [__init__.py](../../scoring_engine/recency/__init__.py), [point_in_time.py](../../scoring_engine/recency/point_in_time.py) | Added `recency_decay_score`: exponential decay `2 ** (-age_days / half_life_days)`, with a documented 90-day default half-life, strict pre-cutoff availability, timezone validation, and `None` for missing evidence timestamps. |
| [data_contracts_and_features.md](../../docs/methodology/data_contracts_and_features.md) | Documented query/corpus provenance safeguards and the recency formula, cutoff semantics, and missing-value behavior. |
| [remaining_work_architecture.md](../../docs/architecture/remaining_work_architecture.md) | Added the point-in-time recency utility to the module responsibility map. |
| [test_remaining_work_modules.py](../../tests/unit/test_remaining_work_modules.py) | Added the focused regression tests listed below and updated retriever calls to supply query IDs and text-availability timestamps. |
| [PRE_PUSH_AUDIT.md](../dataset_handover/PRE_PUSH_AUDIT.md) | Added a historical-snapshot label and linked the separate remediation verification. |
| [VALIDATION_RESULTS.md](../dataset_handover/VALIDATION_RESULTS.md) | Labeled the 2026-11-11 dataset and unit-test results as historical; preserved their original outcomes. |
| [FINAL_DATASET_HANDOVER_REPORT.md](../dataset_handover/FINAL_DATASET_HANDOVER_REPORT.md) | Labeled its validation summary as a historical snapshot and removed the direct link to the excluded local-only replay mismatch analysis. |
| [second_pre_commit_audit_report.md](second_pre_commit_audit_report.md) | Labeled the audit findings and results as a 2026-11-11 historical snapshot. |
| This report | Records the remediation, validation, remaining limitations, and proposed release exclusions. |

Historical reports were not rewritten to imply that their earlier results were
newly verified. Their dated findings remain intact; this report records the
separate current code and environment checks.

## Regression tests added

Added to [test_remaining_work_modules.py](../../tests/unit/test_remaining_work_modules.py):

- `test_reassignment_without_severity_preserves_known_severity`
- `test_explanation_rejects_contributions_that_do_not_sum_to_score`
- `test_point_in_time_retrieval_requires_query_text_before_cutoff`
- `test_point_in_time_retrieval_excludes_query_from_fitted_corpus`
- `test_recency_score_orders_newer_evidence_higher`
- `test_recency_score_requires_evidence_strictly_before_cutoff`
- `test_recency_score_returns_missing_for_missing_evidence_timestamp`

The retrieval self-exclusion test also verifies that a token unique to the
query bug is absent from the fitted TF-IDF vocabulary.

## Validation results

| Check | Result |
|---|---|
| Focused module tests: `.\.venv-sbert\Scripts\python.exe -B -m unittest discover -s tests\unit -p "test_remaining_work_modules.py" -v` | **PASS** — 36 tests. |
| Complete unit suite: `.\.venv-sbert\Scripts\python.exe -B -m unittest discover -s tests\unit -p "test_*.py" -v` | **PASS** — 44 tests, 0 failures, 0 errors. |
| Changed Python syntax | **PASS** — 30 changed Python files parsed with the project interpreter's `ast` module. Pylance file syntax checks also reported no syntax errors for the recency module and updated test file. |
| Changed module/script imports | **PASS** — 19 changed non-test Python modules/scripts imported using `.venv-sbert`; no import failures. |
| Retrieval signature compatibility | **PASS** — Pylance found 5 compatible `fit` call sites and 3 compatible `search` call sites after the API change. |
| VS Code/Pylance interpreter and `sklearn` | **PASS** — workspace now selects `.venv-sbert\Scripts\python.exe`; a Pylance runtime snippet imported `sklearn` from that environment, and retrieval diagnostics cleared. |
| VS Code settings JSON | **PASS** — parsed successfully. |
| `git diff --check` | **PASS** for the tracked diff. A separate whitespace scan found existing Markdown hard-break trailing spaces in the historical second audit report; those original lines were preserved. |
| Dataset validation/extraction | **NOT RUN** — no dataset validators, extraction, collection, or writer scripts were executed, and no dataset content was read or changed for this remediation. |

The targeted tests were run before the full suite. No dependency was installed.
The existing dataset audit outcomes were not rerun or re-certified.

## Unresolved issues and release notes

- The retriever and recency transformer remain reusable utilities only. There
  are no historical text-availability snapshots or complete relationship
  labels to support a JDT retrieval evaluation; no integrated recommendation
  flow or project performance evaluation was performed.
- The 90-day recency half-life is a documented default for the transformation,
  not a project-trained or empirically selected parameter. The new utility is
  not yet integrated into a project recommendation pipeline.
- Workload coverage remains partial and depends on caller-supplied
  `history_complete`; the change preserves severity but does not establish a
  complete workload source.
- The mismatch analysis remains local and unredacted. It must stay excluded
  unless its stable pseudonymous per-developer details receive an explicit
  privacy review and release approval.
- The workspace interpreter setting uses the Windows `.venv-sbert` executable
  path. On macOS/Linux, select `.venv-sbert/bin/python` as documented in the
  README.
- The earlier [pre-push audit](../dataset_handover/PRE_PUSH_AUDIT.md) records
  a pre-existing commit-metadata privacy concern. No Git history or remote
  action was taken; review that historical note before any future push.

## Proposed public-release exclusion list

Do not include the following in a proposed public release:

1. [jdt_workload_replay_mismatch_analysis.md](jdt_workload_replay_mismatch_analysis.md) — explicitly excluded, left unchanged, and contains identity-linked per-developer analysis.
2. [`dataset/raw/`](../../dataset/raw/), [`dataset/processed/`](../../dataset/processed/), and [`dataset/external/`](../../dataset/external/) — raw and generated datasets, restricted identity outputs, and local Git clones.
3. [`.venv/`](../../.venv/) and [`.venv-sbert/`](../../.venv-sbert/) — local Python environments; also exclude Python caches and generated model artifacts.
4. Any identity-review source/output, personal contact data, or stable developer/assignee identifiers, regardless of file location.

This is an exclusion recommendation only. No path was staged, and no release
or Git operation was performed. Stop here pending approval.
