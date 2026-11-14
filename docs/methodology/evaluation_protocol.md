# Model Evaluation Protocol

No system metrics are reported in this document. The implemented utilities
have only synthetic unit-test validation; they have not been evaluated on
JDT, Platform, SWT, UI, or PDE assignment outcomes.

## Shared temporal protocol

1. Freeze a documented cutoff policy and feature availability rule before
   examining test outcomes. For a bug at time `t`, feature evidence must be
   strictly earlier than `t`.
2. Split bugs chronologically into training, validation, calibration, and
   final test periods. Keep duplicate families or near-duplicate clusters
   grouped within a single split where such groups are available.
3. Fit text vocabularies, feature scaling, candidate policies, adaptive
   selection, and model parameters on training data only. Select settings on
   validation data only.
4. Use a distinct calibration period for confidence calibration. Do not reuse
   final test outcomes for calibration or tuning. Record bug IDs and temporal
   boundaries for every split.
5. Report results separately for each project/repository and label tier.
   Never pool JDT, Platform, PDE, or repository identities without verified
   project-scoped links and a prespecified evaluation design.
6. Preserve an insufficient-evidence outcome. Exclude such cases from model
   metrics only under a declared coverage policy; report recommendation
   coverage alongside conditional performance.

## Feature-specific evaluation

### Historical expertise and recency

Compare assignment-history baselines with component-aware and recency-aware
variants on the same temporal test bugs and same eligible candidates. Ensure
the feature profile is rebuilt only from events before each cutoff. Report
coverage and results by evidence tier, project, and cold-start cohort.

### Workload

Replay actual assignment/reassignment/closure histories and validate snapshots
against hand-audited small cases. Compare workload-aware ranking to the same
base ranking without workload. Check that events at or after cutoff do not
change the earlier snapshot. Do not use Git commit volume as workload.

### Adaptive feature selection

Run fixed and adaptive scoring on identical temporal splits and candidate
sets. Freeze base weights and adaptive evidence-quality rules using training
and validation only. Report recommendation coverage, ranking metrics, and
per-feature availability. Do not claim improvement based on a single split or
synthetic tests.

### Prediction confidence

Fit calibration only on a separate calibration period with unique bugs and
both outcomes. On the untouched final test, report Brier score, log loss,
calibration curve, and reliability by confidence bin, in addition to ranking
quality. Calibration output must not be described as confidence unless its
test-set calibration is evaluated and documented.

### Explainability

Check that every score contribution equals normalized weight times the
displayed feature value and that contributions sum to the score. Audit
evidence references against source records and confirm unavailable signals
are listed as missing rather than described as positive evidence.

### Cold start

Define test cohorts using identity and history evidence as of each cutoff.
Separate explicitly verified new identities, insufficient assignment history,
unmatched Git contributors, ambiguous identity candidates, and missing source
history. Do not infer the “new” cohort from a missing identity link.

### Top-K ranking

Report Precision@1/3/5, Recall@1/3/5, and MRR from unique ranked candidate
lists and temporally held-out relevant assignees. State the candidate universe,
label tier, and treatment of unrankable bugs. Include coverage and compare with
frequency/component baselines.

### Duplicate and related-bug retrieval

Build each retrieval index only from bugs created before the query cutoff.
Keep related-bug retrieval quality distinct from duplicate classification.
Evaluate retrieval at K with temporal holdout and family grouping. Exclude
final duplicate-resolution fields and future links from query-time inputs.
The existing 1,810 historical-available duplicate relationships are not a
complete positive/negative labeled evaluation set.

## Required validation evidence

- Required columns, types, nonempty IDs, unique keys, and time zones.
- Chronological assignment events and reproducible point-in-time snapshots.
- No target/label/resolution columns in model input tables.
- No candidate bug created at or after the retrieval cutoff.
- No identity joining by name similarity alone.
- Metrics plus data coverage, label tier, and split provenance.
- Confidence calibration and ranking evaluation on separate final test data.
