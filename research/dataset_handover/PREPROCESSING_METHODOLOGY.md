# Preprocessing Methodology and Provenance

This note summarizes existing transformations; it does not rerun collection or alter data.

## Sources

- **JDT Bugzilla:** existing `dataset/raw/JDT.csv` export. The prior documented scan read it once as a streaming source to extract lifecycle changes and per-bug coverage. This handover did not reopen it.
- **Eclipse Git:** local histories for JDT Core, Platform, Platform SWT, Platform UI, and PDE. The combined extractor used locally reachable refs, did not fetch or check out blobs, included root commits, and used first-parent merge diffs. Renames are represented as delete/add evidence.
- **JDT labels/text/duplicates:** existing processed exports and cleaning scripts under `scripts/`, with provenance and validation details in `research/dataset_documentation/`.

## Assignment labels and candidate features

Primary labels are split by the existing label audit into `known_entry` and `provisional` evidence tiers. The 607-row secondary review file remains separate. Candidate features are generated using strictly prior direct-assignment events and Git activity; a prediction cutoff excludes events at or after the cutoff. The chronological split is by bug so all candidates belonging to a bug remain together.

The candidate pool uses nine conservatively verified JDT identities. The 29,177 targets outside this pool are not negative labels. Assignment history is an observed-history measure, not complete active workload.

## Git and identity evidence

Git author keys are repository-scoped. Exact-email and normalized-name matches outside the conservative JDT map remain review candidates, not person merges. The JDT verified identity map requires exact-email evidence, a single audited Bugzilla user ID, matching JDT roster evidence, and no existing bot/service heuristic flag. These conditions do not prove an account is a human.

Git commit/path counts and recency are code-contribution evidence only. They are not confirmed Bugzilla assignments, assignment experience, fallback eligibility, or workload.

## Temporal feature variants

The temporal generator uses `committer_timestamp < bug_creation_time`. Strict output was reconstructed from existing processed inputs for all 432,198 rows. The base, strict, and inclusive-named CSVs are byte-identical; only strict generation semantics are established. No files were regenerated to address the naming discrepancy.

## Workload evidence

Lifecycle events came from the prior one-pass extraction. Replay compared reconstructed tracked-field history with export-time current state: 47,959 passed, 13,427 mismatched, and 1,880 histories were incomplete/not testable.

The experimental partial workload uses the authorized 4,542-bug replay-clean candidate subset and strict state-seed/event-chain checks. Only 228 histories qualified. Every workload output is explicitly `partial`, uses verified developer identities, and excludes events at or after the prediction cutoff. The separate resolution sidecar attributes 225 observed changes. Unknown or absent bugs are not assumed to be absent from a developer's real queue; severity weighting is unsupported.

## Duplicate and related-bug data

The historical duplicate preparation retains 1,810 positive pairs as evaluation-only targets. Original bug creation precedes the duplicate report. Current cleaned text has no per-version availability timestamp; therefore point-in-time retrieval, TF-IDF/cosine scores, related labels, and defensible negative pairs were not generated. Final duplicate-resolution information is not a model input.

## Integrated tables

`scripts/build_jdt_integrated_dataset.py` integrates validated candidate features and partial workload, while keeping targets, evaluation scenarios, context, duplicate targets, and identity metadata separate. Export-time context remains flagged as temporally unverified. The candidate-expanded context file is retained; the normalized bug/cutoff version is preferred. Status fields represent availability/readiness, not fabricated scores, probabilities, explanations, or rankings.

See the source reports linked from [FINAL_DATASET_HANDOVER_REPORT.md](./FINAL_DATASET_HANDOVER_REPORT.md) for the detailed provenance chain and validation rules.
