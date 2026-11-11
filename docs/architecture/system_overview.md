# System Architecture

The application is organized around a canonical bug record. Member 1 maps source CSV columns explicitly and prepares the history. The bug similarity module retrieves historical neighbors. Member 2 trains a developer classifier and returns the top five developer IDs, model scores, and profile/similarity evidence. Member 3 combines model relevance with expertise, recency, and optional workload inputs. Member 4 exposes the recommendation contract through FastAPI, a small browser form, and SQLite run logging.

```text
Source CSV + explicit schema
        -> canonical preprocessing -> chronological model evaluation/training
        -> saved model/profile/similarity bundle
New bug -> API -> ML developer ranking -> scoring engine -> SQLite + JSON response
```

The API contract is `POST /api/recommend` with `bug_id`, `title`, `description`, optional product/component/severity/priority, and optional workload by developer ID. It returns ranked candidates with relevance scores, component and product experience, similar bug IDs, workload and recency factors, and a heuristic confidence note.

The system currently has no dataset or trained artifact. Cold-start developers require a separate developer roster input and are not included until that contract is agreed. Workload scores are neutral unless a caller supplies workload values.
