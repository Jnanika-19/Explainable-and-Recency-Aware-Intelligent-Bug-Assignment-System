# Known Limitations and Safe-Use Rules

## Coverage and provenance

- JDT is the only project here with Bugzilla report/assignment labels and activity evidence. Platform, SWT, UI, and PDE data are Git histories and contribution records only.
- Platform/PDE Bugzilla collection remains blocked: the four previously documented product-metadata and minimal-bug requests returned HTTP 200 shutdown HTML, not REST JSON. No further requests were made.
- The raw JDT export has 63,266 bugs. Existing history replay passed for 47,959, mismatched for 13,427, and was incomplete/not testable for 1,880. Passing replay is not proof of complete history.
- The partial workload is **not complete developer workload**. It uses 228 strict eligible histories from a 4,542-bug replay-clean verified-assignment candidate subset; 4,314 candidates did not qualify. Unobserved bugs may still be in a real developer queue. Do not report queue totals or infer zero workload from absent evidence.

## Developer identity

- Nine JDT identities passed the conservative exact-email/single-user audit. Four exact-email entries lack Bugzilla user-ID evidence; 72 name-based candidates remain unverified. The unresolved review queue has 76 rows.
- No identities are merged from names alone. Preserve ambiguous accounts and repository-scoped Git keys.
- Bot/service flags are heuristics, not proof of a human account.
- Git commits, files, authors, or component activity do not establish Bugzilla assignment history, assignment eligibility, or successful bug fixes.
- Identity files contain personal/account data. Restrict access; do not expose raw email, name, or account mappings in model logs or public reports.

## Temporal validity and leakage

- The base, strict, and inclusive-named temporal CSVs share SHA-256 `d9bdf8eeea6ce11d583cbe33dc3d390563a209b2d6d756a4b7d8623f3cd8c622`. Strict regeneration matched all 432,198 rows with `committer_timestamp < bug_creation_time`. The base and inclusive filenames are byte-identical copies; do not claim independent inclusive semantics.
- Export-time product/component/severity/priority values and same-component counts lack established as-of timing. They are marked ineligible as model inputs.
- Bug text has no historical snapshot-availability timestamp. Current cleaned text could contain post-cutoff edits; do not build historical retrieval from it.
- Candidate eligibility is conservative. Out-of-pool target labels are not negative examples. Preserve `known_entry` and `provisional` tiers.

## Duplicate, related-bug, and evaluation scope

- The 1,810 historically available duplicate relationships are positive targets, not a complete evaluation dataset. They do not supply defensible negatives or related-bug classes.
- No project TF-IDF representation, cosine similarity, point-in-time retriever, related-pair label, or negative-pair set is available.
- Final duplicate resolution is not an input feature.
- A model or evaluation must separately define candidate coverage, label tiers, temporal splits, and out-of-pool behavior. This package does not evaluate any model.

## Missing values and repeated rows

- Missingness is retained as meaningful or unresolved evidence; it is not filled with guessed values. Examples include no prior assignment/contribution, no eligible active partial workload, out-of-pool target IDs, and missing text snapshot times.
- `jdt_integrated_bug_context_metadata.csv` intentionally repeats each bug/cutoff context across nine candidate rows. Prefer `jdt_integrated_bug_context_by_bug.csv`.
- `git_bugzilla_exact_email_matches.csv` includes one exact duplicate row. Prefer its separate cleaned candidate file for review; do not treat either as verified identity.
- The nine `member1_dataset_files/` CSVs and ZIP are package copies of earlier outputs, not additional observations.

## Model-stage readiness

Several inputs are suitable for controlled implementation, but the complete nine-feature dataset is not ready for a final model or performance claims. Workload, cold-start ground truth, confidence calibration data, historical duplicate text, and Platform/PDE issue data remain incomplete or blocked. Do not fabricate scores, probabilities, queue values, identities, or missing labels.
