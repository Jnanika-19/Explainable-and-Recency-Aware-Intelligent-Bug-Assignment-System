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

## Application status

The Member 4 full-stack foundation is implemented: a responsive dashboard,
bug submission and history, developer profiles, assignment history, and
evidence-aware recommendation rendering. Recommendation output is currently a
clearly labeled demo placeholder; it is not a real ML prediction.

The following project capabilities still require integration or implementation:

- Connect real bug preprocessing and similar-bug retrieval.
- Connect Member 2's trained developer recommender and expertise profiles.
- Connect Member 3's recency, workload, confidence, and scoring engine.
- Populate developer profiles and assignment history from approved project data.

## Technology Stack

- Python for data processing and machine learning.
- pandas, NumPy, SciPy, and scikit-learn for analysis and modeling.
- NLTK for natural language processing experiments.
- FastAPI, Uvicorn, and Pydantic for the backend API.
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

## Run the application

Install dependencies and run the FastAPI backend from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.api.main:app --reload
```

In a second terminal, start the React/Vite frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). API documentation is
available at `http://127.0.0.1:8000/docs`. The SQLite database is stored at
`data/bugwise.db` unless `BUGWISE_DB` specifies another location.

The current recommendation adapter intentionally returns clearly labeled
**DEMO ONLY** placeholders; it is not an ML prediction. Connect Member 2's
recommender and Member 3's scoring engine before interpreting recommendations.
See [Member 4 integration notes](docs/member4/integration.md).

Run checks:

```powershell
pytest tests/integration/test_member4_api.py
cd frontend
npm run build
```