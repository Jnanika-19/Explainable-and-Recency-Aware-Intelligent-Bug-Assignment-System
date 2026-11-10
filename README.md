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

The Member 4 branch contains the React dashboard, FastAPI APIs, and SQLite
storage for bugs, developers, recommendations, and assignments. Dashboard,
workload, reports, bug status, and assignment history are database-backed.
Developer selection and assignment are manual; the application does not
silently convert an ML ranking into a final assignment.

The backend adapter follows Member 2's documented
`recommend_developers(bug_report, top_k, candidates=...)` contract. The Member 2
source modules and runtime model/history/vectorizer assets are not present on
this branch, so recommendation endpoints report that integration as unavailable
instead of returning fabricated results. Member 3's executable scoring module
is also not present; final assignment scores remain unavailable. See
`docs/member4/integration.md` for required runtime resources and API behavior.

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

The API returns HTTP 503 for recommendation requests until Member 2's source
and model resources are installed. Bug submission is not stored when
recommendation resources are unavailable. Health reports recommendation and
assignment-scoring readiness. Manual assignment endpoints remain available
when developer and bug records exist.

Run checks:

```powershell
pytest tests/integration/test_member4_api.py
cd frontend
npm run build
```