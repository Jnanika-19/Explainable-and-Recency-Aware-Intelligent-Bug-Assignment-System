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

Application and model implementation steps are **upcoming**. There is not yet an application entry point or a trained model to run.

After implementation, the intended workflow is:

1. Place approved source data in `data/raw/` (large raw files are excluded from Git).
2. Implement preprocessing, similarity retrieval, model training, and scoring modules.
3. Add backend and frontend entry points and document their run commands here.
4. Run the test suite with `pytest` once tests have been added.

Until those implementation steps are complete, there is no project application command to launch.