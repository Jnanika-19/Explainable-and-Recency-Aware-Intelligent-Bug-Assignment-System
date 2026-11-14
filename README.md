# Explainable and Recency-Aware Intelligent Bug Assignment System

## Project Overview

This final-year engineering project is intended to support bug triage by recommending suitable developers for reported software defects. The planned system combines bug similarity, developer expertise, recency-aware signals, workload considerations, and explanations so that recommendations can be reviewed by a human.

## Problem Statement

Assigning a bug to the right developer can require time-consuming manual review of issue descriptions, project history, developer experience, and current workload. This project will investigate an intelligent approach to ranking candidate developers while making the factors behind each recommendation understandable.

## Project Objectives

- Prepare and document data for bug assignment research.
- Explore bug similarity and developer expertise signals.
- Incorporate recency and workload into developer ranking.
- Present recommendations with interpretable supporting factors.
- Provide a modular backend, frontend, and database foundation for later integration.

## Current Implementation Status

The project has substantial JDT data preparation and validated Git history for
JDT, Eclipse Platform, SWT, UI, and PDE. Reusable research utilities now cover
evidence-aware cold-start assessment, fixed/adaptive feature scoring,
confidence calibration interfaces, score explanations, Top-K ranking and
metrics, point-in-time TF-IDF retrieval, assignment-event workload snapshots,
and a strict-cutoff recency-decay transformation.

These are tested building blocks, not an integrated application or trained
bug-assignment model. No recommendation performance, calibrated probability,
or feature improvement is claimed. Platform/PDE Bugzilla assignment data is
not available in the local inventory, and Git commits are not assignment or
workload labels.

See [the architecture overview](docs/architecture/remaining_work_architecture.md),
[the data contracts](docs/methodology/data_contracts_and_features.md), and
[the evaluation protocol](docs/methodology/evaluation_protocol.md).

## Technology Stack

- Python for data processing and machine learning.
- pandas, NumPy, SciPy, and scikit-learn for analysis and modeling.
- NLTK for natural language processing experiments.
- FastAPI, Uvicorn, and Pydantic for the planned backend API.
- Matplotlib for visual analysis.
- pytest for automated tests.
- joblib for model persistence when model artifacts are introduced.

## Team Responsibilities

| Member | Responsibility | Folders |
| --- | --- | --- |
| Member 1 | Data, research, and NLP | `dataset/`, `research/`, `preprocessing/`, `bug_similarity/` |
| Member 2 | Machine learning and developer expertise | `ml_model/` |
| Member 3 | Intelligent assignment and scoring | `scoring_engine/` |
| Member 4 | Full-stack application and integration | `backend/`, `frontend/`, `database/` |
| All members | Documentation and testing | `docs/`, `tests/` |

This table describes broad project folder ownership. Dataset-specific
responsibilities, inputs, limitations, and deliverables are assigned separately
in the [four-member dataset handover matrix](research/dataset_handover/TEAM_HANDOVER_MATRIX.md);
the two tables serve different purposes and are not intended to be a
one-to-one mapping.

## Project Folder Structure

```text
.
+-- dataset/                 # Raw, processed, sample, and external data
+-- research/                # Literature review and dataset documentation
+-- preprocessing/           # Data cleaning and feature preparation
+-- bug_similarity/          # Point-in-time TF-IDF retrieval utilities
+-- ml_model/                # Feature selection and Top-K ranking utilities
+-- scoring_engine/          # Recency, workload, cold-start, confidence, explanations
+-- backend/                 # API, services, and backend models
+-- frontend/                # Public assets and application source
+-- database/                # Schemas and migrations
+-- tests/                   # Unit, integration, and evaluation tests
+-- docs/                    # Architecture, methodology, and reports
+-- .gitignore
+-- README.md
+-- requirements.txt
```

## Installation

Use Python 3.10 or newer. From the repository root, create and activate a virtual environment, then install the listed dependencies:

```bash
python -m venv .venv-sbert
```

On Windows:

```powershell
.venv-sbert\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv-sbert/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Dependencies are listed for setup; they are not installed automatically by this project structure.

In VS Code, select the `.venv-sbert` environment as the Python interpreter
(Windows: `.venv-sbert\Scripts\python.exe`; macOS/Linux:
`.venv-sbert/bin/python`). Use that same environment when running the unit
tests so editor diagnostics and test imports resolve the same dependencies.

## Validation

Run the reusable-module unit tests from the project root:

```powershell
python -m unittest discover -s tests\unit -p "test_*.py" -v
```

There is not yet an application entry point or a trained model to launch.
Integrating these utilities into an evaluated recommender and API/UI remains
future work. See the [remaining-work completion report](research/dataset_documentation/remaining_work_completion_report.md)
for the current feature status and deferred JDT/Bugzilla phase.