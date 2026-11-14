# Data Contracts and Feature Dictionary

All contracts below are proposed interfaces for future approved project data.
The utilities validate small in-memory inputs; they do not parse the multi-GB
raw JDT export or create feature tables from it.

## Shared conventions

- Every timestamp is timezone-aware UTC or converted to UTC at the boundary.
- A prediction at cutoff `t` may use only records with `event_time < t`.
- Identifiers are opaque and project/repository-scoped.
- Missing evidence is represented as missing with a status/reason, never a
  fabricated zero.
- Assignment labels and duplicate outcomes are targets, not model input
  features.
- Git author evidence is not a Bugzilla developer identity without a reviewed
  link; no cross-repository identity merge is automatic.

## Feature inputs

| Feature family | Input fields | Derived value | Missing/quality behavior |
|---|---|---|---|
| Historical expertise | `project_id`, `bug_id`, `component`, verified `developer_id`, assignment event time, label evidence/status | Prior relevant assignment counts/rates by component, calculated before cutoff | Unknown/weak labels remain excluded or separately tiered by pre-registered policy |
| Recency | `developer_id`, evidence type, component/path, evidence-availability timestamp, `prediction_cutoff` | `recency_decay_score`: `2 ** (-age_days / 90)` by default, using timestamps strictly before cutoff | No prior timestamp means unavailable (`None`), not zero expertise; timestamps at/after cutoff are invalid |
| Workload | `event_id`, `bug_id`, `occurred_at`, `event_type`, `developer_id`, optional `severity`, history completeness | Active assigned bug count; optional severity-weighted count | Requires complete history window/baseline. Missing severity prevents weighted total; Git commit volume is prohibited as a substitute |
| Bug text | `bug_id`, `created_at`, query summary/description text | TF-IDF representation and cosine similarity to eligible earlier bugs | Empty text yields no text signal. Index is fitted from pre-cutoff bug documents only |
| Developer activity | repository-scoped Git author key, commit timestamp, component/path, reviewed identity link | Separate code activity / component-path signal | Never treated as bug assignment, workload, or verified candidate eligibility |
| Adaptive score | feature name, normalized value in `[0,1]`, evidence quality in `[0,1]`, configured base weight | Fixed or availability/quality-adjusted weighted score | Omit unavailable signals; if none remain, return no score and insufficient evidence |
| Confidence | held-out prediction score, binary outcome, unique bug ID, prediction and outcome timestamps, split label | Isotonic-calibrated probability after explicit calibration fit | Evidence coverage alone remains qualitative/uncalibrated |
| Ranking | eligible unique developer IDs, score, breakdown, optional explanation; held-out relevant developer IDs | Top-1/3/5 list; Precision@K, Recall@K, MRR | Empty relevant set yields undefined (`None`) recall/MRR; no metrics on training candidates |
| Duplicate/related retrieval | `bug_id`, `created_at`, text, prediction cutoff | Strictly earlier candidate ID and TF-IDF cosine score | Final duplicate resolution is never an input; similarity candidate is not a duplicate label |

## Current module record contracts

### Assignment lifecycle events

`AssignmentEvent(event_id, bug_id, occurred_at, event_type, developer_id,
severity)` accepts `assign`, `reassign`, `close`, `resolve`, and `reopen`.
Events must be unique and chronologically ordered. For a strict cutoff, events
at the cutoff are not included. The caller must state whether history is
complete; anomalies or incomplete source history require manual review.

### Bug retrieval

`BugDocument(bug_id, created_at, text, text_available_at)` intentionally
contains no resolution field. `PointInTimeBugRetriever.fit(documents, *,
cutoff, query_bug_id)` validates IDs and timestamps, binds one query ID, and
filters to both `created_at < cutoff` and `text_available_at < cutoff`.
It excludes the query bug before fitting the TF-IDF vocabulary and fits only
on the remaining subset. `search` requires
the query text's `query_text_available_at` to be strictly before the same
cutoff and to identify the query bug used when fitting. It reports similarity
candidates and IDs, not duplicate truth.

### Recency transformation

`recency_decay_score(evidence_available_at, prediction_cutoff,
half_life_days=90)` computes `2 ** (-age_days / half_life_days)`, where age is
the elapsed time from evidence availability to the prediction cutoff. Both
timestamps must be timezone-aware, and evidence must be available strictly
before the cutoff. The default half-life is 90 days; a more recent event scores
higher, and each half-life halves the score. A missing evidence timestamp
returns `None`, not zero. This is a reusable transformation, not an integrated
recommendation score or evidence that recency improves model performance.

`DuplicateTrainingPair` stores `duplicate_label` separately from
`model_features()`. Only the similarity score is returned as an input feature;
the label is never included in that dictionary.

`RelationshipTrainingPair` supports the separate `duplicate`, `related`, and
`unrelated` targets and also exposes similarity-only input features. The
logistic baseline requires a training set with multiple classes; it has not
been fitted to the local JDT relationships. The 1,810 historical-available
links provide neither a complete negative set nor a validated train/test split.

### Scoring and explanations

Feature signal values and evidence qualities are bounded to `[0,1]`; feature
weights are finite and non-negative. The adaptive mode scales configured
weights by evidence quality, then renormalizes over available features. Fixed
mode uses the configured weights over available features. The score is a
research score, not a probability.

An explanation must match the contribution arithmetic in the score result.
Evidence strings are supplied by the feature producer and must reference
actual input evidence; the explanation generator does not invent bug history.

### Identity review

The current review dataset is under
`dataset/processed/cold_start/eclipse_all_repositories/identity_review/`.
It contains one unresolved unique-pair queue plus separate exact-email and
exact-normalized-name queues (pairs can occur in both), and a repository-
scoped classified cohort file. Candidate pairs carry source names/emails and
explicit review decision, reviewer, review timestamp, and evidence-note
columns. Decision fields begin blank. Cohort labels such as possible
bot/service account, missing email, and no candidate link are review
heuristics, not confirmed identity properties.

## Leakage guards

The feature selector rejects target/outcome field names such as `label`,
`developer_label`, `duplicate_label`, `resolution`, and `assigned_to`. Keep
actual labels in separate evaluation inputs, and audit all derived model
tables against this contract before training. Do not feed assignment changes
or final duplicate status that occur after the prediction cutoff into features.
