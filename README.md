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

## Planned Main Features

The following are project goals; they are not implemented yet:

- Bug report preprocessing and feature preparation.
- Similar bug retrieval.
- Developer profile and expertise modeling.
- Recency-aware, workload-aware candidate scoring.
- Confidence information and explainable assignment recommendations.
- API and user interface for reviewing recommendations.

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
| Member 1 | Data, research, and NLP | `data/`, `research/`, `preprocessing/`, `bug_similarity/` |
| Member 2 | Machine learning and developer expertise | `ml_model/` |
| Member 3 | Intelligent assignment and scoring | `scoring_engine/` |
| Member 4 | Full-stack application and integration | `backend/`, `frontend/`, `database/` |
| All members | Documentation and testing | `docs/`, `tests/` |

## Project Folder Structure

```text
.
+-- data/                    # Raw, processed, and external data
+-- research/                # Literature review and dataset documentation
+-- preprocessing/           # Data cleaning and feature preparation
+-- bug_similarity/          # Similarity modeling and retrieval
+-- ml_model/                # Profiles, features, training, evaluation, ranking
+-- scoring_engine/          # Recency, workload, cold-start, confidence, scoring
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
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Dependencies are listed for setup; they are not installed automatically by this project structure.

## How to Run

The module interfaces and initial app shell are implemented. Training and measured recommendation quality still require a real dataset and a schema mapping.

1. Inspect the dataset headers and map actual source columns in `research/dataset_documentation/schema.json` (see `ml_model/README.md`).
2. Run training and evaluation with `python -m ml_model.train_model --data data/processed/bugs.csv --schema research/dataset_documentation/schema.json`.
3. Start the API and browser form with `uvicorn backend.api.main:app --reload`, then open `http://127.0.0.1:8000`.
4. Run `pytest` after installing dependencies and adding/receiving the team's test cases.

The repository currently contains no dataset or trained model, so recommendation requests return HTTP 503 until the training command succeeds. No results or accuracy claims are supplied in advance.
