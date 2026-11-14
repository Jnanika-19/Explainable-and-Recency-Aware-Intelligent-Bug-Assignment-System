# Reusable Bug Assignment Research Architecture

## Status and boundary

This architecture adds reusable, tested utilities to the existing project
scaffold. It is not an integrated application, trained recommender, or
experiment result. No JDT raw export, assignment-history log, or Bugzilla
service was processed to implement these modules. All repository-aware Git
contribution files remain evidence about code changes, not bug assignments.

## Data flow

```text
Approved issue/assignment events (future JDT phase)
  ├─> label/identity validation ─> expertise + temporal developer evidence
  ├─> assignment lifecycle replay ─> point-in-time workload
  └─> timestamped bug text ─> pre-cutoff TF-IDF retrieval

Repository-scoped Git commits and paths (already collected)
  └─> code activity and component evidence
      └─> cold-start evidence only when identity is independently verified

Feature evidence + availability
  └─> fixed/adaptive feature scorer
      ├─> score contributions and evidence-grounded explanation
      ├─> non-probabilistic evidence summary
      └─> deterministic Top-K ranker
          └─> temporally held-out evaluation and (separate) calibration
```

Identity resolution is a separate manual process. Repository author keys must
remain namespaced. An exact-email or normalized-name candidate is not an
identity confirmation. A candidate identity is never eligible for a Bugzilla
assignment ranking solely because of Git history.

## Module responsibilities and contracts

| Module | Responsibility | Main input | Output |
|---|---|---|---|
| `scoring_engine/cold_start/policy.py` | Classify historical evidence and choose a safe fallback | verified identity state, assignment-event count/completeness, Git evidence count | cold-start status and reasons; Git evidence never substitutes for assignments |
| `ml_model/feature_selection/adaptive.py` | Validate [0,1] signals, remove unavailable evidence, score fixed/adaptive variants, reject outcome columns | feature name → value and evidence quality; explicit base weights | normalized score, feature contributions, omitted features, evidence coverage |
| `scoring_engine/confidence/prediction_confidence.py` | Summarize evidence separately from prediction probability; fit held-out isotonic calibration | signal-quality values; explicit calibration examples | qualitative evidence level or calibrated probability only after a separate valid calibration fit |
| `scoring_engine/final_scoring/explainability.py` | Emit a score decomposition tied to supplied values and evidence | score result, values, evidence statements | per-feature value/weight/contribution/status and overall recommendation status |
| `scoring_engine/recency/point_in_time.py` | Compute a half-life decay from evidence availability strictly before a cutoff | timezone-aware evidence-availability timestamp and prediction cutoff | recent-evidence score or `None` when the timestamp is missing |
| `ml_model/ranking/top_k.py` | Rank eligible candidate IDs and evaluate offline lists | unique candidate IDs, scores, breakdowns; held-out relevant IDs | stable ranked list and Precision@K, Recall@K, MRR |
| `bug_similarity/retrieval/point_in_time.py` | Build a TF-IDF index only from bugs created before a strict cutoff; provide a label-separated logistic baseline interface | bug ID, creation timestamp, text, cutoff; later labeled training pairs | similar/duplicate-candidate retrieval and relationship classes; classifier is not trained/evaluated on project data |
| `scoring_engine/workload/point_in_time.py` | Replay assignment, reassignment, closure, resolution, and reopening events | chronological, timestamped assignment events and history completeness | active-bug count, optional severity-weighted total, event anomalies |
| `scripts/prepare_eclipse_identity_review.py` | Prepare separate unresolved pair review and identity cohorts | existing five-repository candidate and roster CSVs, existing clean JDT map | manual review files; no identity merges or Bugzilla mapping changes |

## Nine-feature integration

1. **Historical expertise:** use validated assignment outcomes by component
   for recommendation expertise. Git paths and commits are a separate code
   expertise proxy and must be identity-linked before association with bugs.
2. **Recency:** derive only from evidence with timestamps strictly earlier
   than the bug prediction cutoff. Prefer assignment time for bug expertise;
   use committer/author time only as a distinct code-activity signal.
3. **Workload:** replay actual assignment lifecycle history. A Git commit
   count is never an active-workload measure.
4. **Explainability:** return the numeric feature value, normalized weight,
   score contribution, and evidence references. Missing signals are explicit.
5. **Cold start:** separate verified new developers from unmatched Git
   contributors and from missing/incomplete assignment history. Unmatched is
   not equivalent to new.
6. **Adaptive selection:** adjust configured weights only for available
   signals and evidence quality. It is an experimental scoring mode, not a
   proven improvement.
7. **Prediction confidence:** evidence coverage is qualitative support, not
   probability. Probability output requires a held-out calibration set.
8. **Duplicate/related bugs:** retrieval index is fitted using only issues
   and text snapshot available before the cutoff. Similarity is not duplicate
   truth; final duplicate resolution is target-only.
9. **Top-K ranking:** rank only eligible, identity-resolved assignment
   candidates and report metrics on a temporally held-out set.

## Output shape

An eventual recommendation response should contain:

```json
{
  "bug_id": "opaque bug identifier",
  "prediction_cutoff": "timezone-aware timestamp",
  "status": "ranked | insufficient_evidence | manual_review",
  "feature_mode": "fixed | adaptive",
  "recommendations": [
    {
      "rank": 1,
      "developer_id": "verified project-scoped identity",
      "score": 0.0,
      "confidence": {
        "status": "uncalibrated | calibrated",
        "probability": null
      },
      "feature_contributions": [],
      "evidence": [],
      "missing_evidence": []
    }
  ],
  "excluded_candidates": []
}
```

The numeric value is illustrative schema only, not a score or performance
claim. Never emit a probability while confidence is uncalibrated.

## Data and privacy boundaries

- Keep project/product and repository identity on every record.
- Keep raw identity evidence in access-restricted research files.
- Do not publish email addresses or identity-review rows.
- Keep primary assignment labels separate from weaker or ambiguous evidence.
- Keep model inputs separate from assignment/duplicate target columns.
- Preserve source timestamps/time zones, source provenance, and completeness
  status through transformations.
