# Eclipse Dataset Completion Plan

Prepared: 2026-11-11

## Purpose and decision boundary

This plan describes how to complete the mini-project dataset for Eclipse JDT,
Eclipse Platform, and Eclipse PDE while preserving existing work and avoiding
cross-project label or identity contamination. It is an assessment and roadmap,
not approval to collect data.

No downloads, network requests, Bugzilla retries, extraction runs, or dataset
changes were performed to prepare this plan. No existing JDT data or scripts
should be overwritten. Any future collection requires approval and a successful
source, terms, and privacy gate.

## Evidence labels

- **Verified locally** means supported by files or reports currently in this
  workspace. Existing counts are taken from the read-only inventory report and
  were not recomputed for this plan.
- **Verified in a project/source report** means recorded in
  `eclipse_project_source_probe.md`; it is not an independent live check.
- **Not verified / assumption** identifies information that needs source
  inspection or approval before it is treated as fact.

## 1. Existing JDT audit

### 1.1 Files and datasets present

The local dataset tree contains JDT data only. The inventory is documented in
[`dataset_availability.md`](./dataset_availability.md).

**Raw input**

- `dataset/raw/JDT.csv` — Bugzilla export, approximately 6.08 GiB. It includes
  bug fields, current assignee/status/resolution, history/activity log,
  comments, and duplicate links. The availability report did not count its rows
  because it exceeds the report's CSV row-count limit.

**Processed JDT products at `dataset/processed/`**

- Assignment examples and text: `jdt_training_primary.csv`,
  `jdt_training_secondary_review.csv`, `jdt_bug_text_cleaned.csv`.
- Assignment evidence and profiles: `jdt_assignment_label_audit.csv`,
  `developer_profile_summary.csv`, `developer_component_expertise.csv`,
  `developer_identity_audit.csv`, `possible_developer_aliases.csv`, and
  `known_entry_developer_profiles.csv`.
- Duplicate relationships: `duplicate_pairs.csv`,
  `duplicate_pairs_historical_available.csv`, and
  `duplicate_pairs_with_families.csv`.
- Packaged copy: `member1_dataset_files/` contains a README and copies of the
  assignment audit, primary and secondary training files, developer profiles,
  expertise, identity audit, aliases, known-entry profiles, and duplicate
  families. `member1_dataset_files.zip` packages that subset. Treat these as
  copies, not independent data sources; verify checksums before using them.

**JDT Git and cold-start products at `dataset/processed/cold_start/`**

- Git inventory: `jdt_git_commits.csv`,
  `jdt_git_commit_files.csv`, and `jdt_git_developer_roster.csv`.
- Identity matching and review: `git_bugzilla_exact_email_matches.csv`,
  `git_bugzilla_exact_email_matches_clean.csv`,
  `git_bugzilla_candidate_matches.csv`,
  `git_bugzilla_candidate_review.csv`, and
  `git_unmatched_identity_review.csv`.
- Contribution summaries: `git_verified_developer_commit_events.csv`,
  `git_verified_developer_summary.csv`,
  `git_verified_developer_component_expertise.csv`, and
  `git_verified_developer_adjusted_contributions.csv`.
- Commit audit and per-bug temporal features:
  `git_bulk_commit_audit.csv`,
  `jdt_bug_developer_temporal_features.csv`,
  `jdt_bug_developer_temporal_features_inclusive.csv`, and
  `jdt_bug_developer_temporal_features_strict.csv`.

The base inventory records 33,246 primary examples, 607 secondary-review
examples, 63,266 assignment-audit rows, 10,875 duplicate pairs, and 1,810
historically available duplicate pairs. It records 32,484 Git commits, 279,322
commit-file records, a 254-key Git author roster, 13 clean exact-email
Bugzilla-to-Git identities, 1,418 verified developer commit events, and
432,198 strict bug/developer feature rows. These are inventory-reported values,
not results of a new scan.

`dataset/external/eclipse.jdt.core/` also has three unusual, non-source files
listed in the inventory, including an artifact whose name reports a Git
history extraction error. The inventory describes the local Git metadata as
32,484 commits across available refs, not shallow, but a `blob:none` partial
clone with 10,859 tracked paths reported deleted in its checkout. **Do not
assume this checkout or its available refs are a complete, verified upstream
source snapshot.** Preserve it and the derived outputs.

No local files or directories matching Platform or PDE were found in the
workspace inventory/search. In particular, there are no Platform/PDE raw
Bugzilla exports, processed training datasets, or checked-out source
repositories represented in `dataset/`. The source-probe and retry reports
are documentation, not collected Platform/PDE datasets.

### 1.2 Completed extraction and validation work

Evidence in the generated files and existing scripts indicates these JDT steps
have already been performed:

1. Parsed Bugzilla activity history and audited assignment-label evidence,
   distinguishing direct assignment from weaker previous-assignee-only cases;
   retained a secondary-review set rather than merging it into the primary
   labels.
2. Built primary and secondary training tables with bug text, project/product,
   component, severity, priority, creation time, label event time/type,
   evidence type, JDT-entry time, and history status.
3. Audited assignment timing and developer-label/profile quality; created
   developer and component profile tables, identity audits, and known-entry
   profiles.
4. Extracted duplicate links, constructed connected duplicate families, and
   prepared a creation-time-filtered historical-availability subset.
5. Extracted Git commit metadata, file paths and first-path-segment component
   labels; created an author roster and reviewed large commits/verified
   identical patches.
6. Matched Git authors to Bugzilla identities using exact email matches and
   kept normalized-name matches as review candidates rather than confirmed
   identities. Unmatched authors are explicitly marked
   `unmatched_unknown_not_confirmed_cold_start`.
7. Built contribution summaries, component expertise and strict temporal
   features from verified identities. The strict feature script uses commit
   committer timestamps and excludes contributions at or after bug creation.
8. Added a dataset availability inventory with paths, sizes, checksums, CSV
   headers, and eligible row counts. Existing scripts include checks for
   training labels/duplicates, duplicate references and summaries, assignment
   timing, developer labels, identities, and Git commits.

This is evidence that artifacts and validation code exist, not proof that every
check was rerun successfully in this planning task. No scripts or expensive
checks were run.

### 1.3 JDT gaps against the nine features

| Feature | JDT evidence already present | Remaining gap |
|---|---|---|
| Historical developer expertise | Assignment profiles and component expertise; Git contribution summaries for verified identities. | Validate component mappings and contribution quality; improve coverage beyond 13 exact-email identities without treating aliases as confirmed. Git path-derived expertise is not equivalent to bug assignment expertise. |
| Recency-aware recommendation | Strict per-bug features include historical commits/files, 30/90/365-day activity, and days since latest contribution. | Reconcile author versus committer time policy; document point-in-time cutoffs and compare inclusive/strict variants; coverage remains restricted to verified identities and available Git history. |
| Workload-aware scoring | Assignment events exist in raw history and assignment audit captures evidence. | No normalized, time-varying active queue or workload-at-cutoff table. Reconstruct from assignment transitions, cancellations/resolutions, and prediction cutoffs before claiming workload features. |
| Explainable recommendations | Feature inputs and evidence/provenance fields exist. | No integrated ranked recommendation output or explanation record attributing score contributions; explanation quality requires user-facing evaluation. |
| Cold-start handling | Git author roster, unmatched identity review, and verified identity subset are available. | Define cold-start cohorts and fallback behavior; unmatched is unknown, not proof of a new developer. Validate handling of new bugs, new developers, and sparse-history candidates. |
| Adaptive feature selection | Multiple feature families exist as research inputs. | No adaptive-versus-fixed feature/weight comparison or validation protocol is documented in the dataset inventory. |
| Prediction confidence | Evidence strength and identity statuses are available as data quality indicators. | No calibrated recommendation confidence, calibration set, or calibration evaluation. Evidence strength must not be presented as statistical confidence. |
| Duplicate and related bug detection | Duplicate pairs, families, and historical-availability subset exist. | Build point-in-time related-bug features that exclude future reports/links; evaluate retrieval/detection. Existing links/families alone are not prediction-time safe. |
| Top-K developer ranking | Candidate/label and expertise inputs support future ranking. | No integrated Top-K recommender, ranking metrics, temporal holdout evaluation, or baseline comparison is present in the inventory. |

## 2. Platform and PDE source investigation

### 2.1 Verified source evidence

The local probe in
[`eclipse_project_source_probe.md`](./eclipse_project_source_probe.md) records
the following, and its retry record is in
[`bugzilla_retry_results.md`](./bugzilla_retry_results.md):

- The four bounded Platform/PDE Bugzilla REST requests returned HTTP 200 with
  `text/html` containing the Eclipse temporary-shutdown page, not REST JSON.
  The retry report records the same outcome. No Platform/PDE bug records or
  comments were collected.
- Platform's SDK aggregator repository and its `.gitmodules` are identified
  as sources for a candidate repository inventory. The report names
  `eclipse.platform`, `eclipse.platform.swt`, and `eclipse.platform.ui`, and
  notes that JDT, PDE, and Equinox repositories are also listed there.
  **These are candidates, not a verified Bugzilla-component-to-repository
  crosswalk.**
- The report identifies `eclipse-pde/eclipse.pde` as the official public PDE
  source repository. It describes PDE project areas as including UI, API
  Tools, Build, Incubator, and Doc; live Bugzilla product/component metadata
  was not verified.
- The report records EPL-2.0 evidence for cited source projects/repositories,
  subject to file headers and notices. This does not establish terms for
  Bugzilla records, contributor identifiers, or redistribution.
- The report says Platform UI identifies current issue tracking on GitHub, but
  GitHub issues do not replace the legacy Bugzilla assignment-event history
  required for this study.

### 2.2 What Git can and cannot provide

**Can provide, if repositories and history are approved and complete enough:**

- Commit author/committer timestamps, names/emails as recorded, commit IDs and
  subjects; changed paths; repository/module/component context; developer
  contribution counts; and time-windowed recency signals.
- Expertise proxies based on changed modules/files and activity over time.
  This supports code-contribution expertise, not necessarily triage or
  assignment expertise.
- A Git-only roster for contributors with no verified issue-tracker identity,
  suitable for an explicitly unknown/unlinked cohort rather than an asserted
  person identity.

**Cannot establish by itself:**

- Bug report text, severity/priority, report creation dates, product/component
  taxonomy as used by Bugzilla, assignee transitions, assignment decision
  events, open-queue workload, reporter identities, or duplicate relationships.
- That a commit author equals a Bugzilla assignee, that a commit fixes a
  particular bug, or that similarly named/email-addressed developers are the
  same person.
- Complete project history from a partial clone or selected branch/ref list.

Git histories for Platform and PDE are therefore useful contribution and
recency evidence but do not fill the missing bug/assignment dataset. Before
collection, record repository URLs, default and release branches/tags, commit
range, submodules, history gaps, bot/merge/cherry-pick handling, and license
notices. Do not equate GitHub issue assignments after a tracker transition with
historical Bugzilla assignments without a verified crosswalk and comparable
event semantics.

### 2.3 Missing data and collection readiness

For both Platform and PDE, missing locally are the source checkout/history,
bug reports, product/component metadata, normalized assignment history,
developer identity audit and reviewed Git-to-tracker identity links,
prediction-time workload state, duplicate/related-bug links, and project-level
validation outputs.

The known source blocker is Bugzilla availability: the REST responses were
shutdown HTML. Do not infer the existence, completeness, or current
accessibility of a usable archive. If Bugzilla remains unavailable, any
alternate archive is a separate proposal requiring provenance, coverage,
terms/privacy review, and approval before use.

For Platform specifically, first verify product/component metadata and map it
to the Platform SDK aggregator/submodules. For PDE, verify the live product and
component list and reconcile it to `eclipse-pde/eclipse.pde` modules. Do not
collect all aggregator repositories merely because they appear in a submodule
list.

## 3. Nine-feature coverage by Eclipse component

Status meanings: **Partial** means relevant source tables exist but the
feature-ready data or evaluation is incomplete; **Not covered** means no
local component dataset/evidence was found; **Blocked** means a necessary
source or prerequisite is unavailable. Future Platform/PDE capabilities are
proposals, not collected facts.

| Feature | JDT (verified local status) | Platform (local status / route) | PDE (local status / route) |
|---|---|---|---|
| Historical developer expertise | **Partial** — assignment and Git component profiles exist; Git matching is verified only for 13 identities. | **Not covered / blocked for issue-based expertise** — collect approved Git history for code expertise; tracker labels and component mapping remain blocked. | **Not covered / blocked for issue-based expertise** — collect approved PDE Git history; tracker labels and component mapping remain blocked. |
| Recency-aware recommendation | **Partial** — strict temporal Git features exist for matched identities. | **Not covered** — Git commit timestamps can support recency after history completeness and component mapping are validated. | **Not covered** — same Git-based route, with a PDE-specific roster and cutoff. |
| Workload-aware scoring | **Gap** — event evidence exists, but no active workload-at-cutoff reconstruction. | **Not covered / blocked** — requires assignment state transitions and status/closure history. Git alone is insufficient. | **Not covered / blocked** — same requirement; Git alone is insufficient. |
| Explainable recommendations | **Gap** — feature evidence exists, but no integrated score/explanation records. | **Not covered** — needs common score-component and evidence provenance outputs after data collection. | **Not covered** — same. |
| Cold-start handling | **Partial** — roster and unmatched review exist; unknown identities must not be called confirmed cold-start people. | **Not covered** — construct project-scoped Git roster and unresolved identity cohort. | **Not covered** — construct PDE-scoped roster and unresolved identity cohort. |
| Adaptive feature selection | **Gap** — no adaptive-versus-fixed comparison found. | **Not covered** — requires evaluation after sufficient labeled history. | **Not covered** — requires evaluation after sufficient labeled history. |
| Prediction confidence | **Gap** — no calibrated confidence data/evaluation found. | **Not covered** — collect labels first; confidence calibration is a model/evaluation stage. | **Not covered** — same. |
| Duplicate and related bug detection | **Partial** — duplicate pairs/families and historical subset exist; no point-in-time related-bug feature table found. | **Not covered / blocked** — requires historical duplicate links/bug data; Git similarity alone is not a verified duplicate label. | **Not covered / blocked** — same. |
| Top-K developer ranking | **Gap** — no integrated recommender or Top-K evaluation found. | **Not covered** — requires valid labels, project-scoped candidate sets, and temporal evaluation. | **Not covered** — same. |

The status table rates existing data readiness, not whether the application
features are implemented. The README describes these as project goals and says
the application/model are not yet implemented.

## 4. Dataset integration proposal

Use a shared schema with explicit project and source namespaces. Do not merge
developer identities or assignment labels merely because names, emails, or
component strings match.

### 4.1 Core tables

| Table | Suggested key and core fields | Integrity rule |
|---|---|---|
| `project_catalog` | `project_id` (`eclipse.jdt`, `eclipse.platform`, `eclipse.pde`), display name, source/tracker metadata, collection version. | `project_id` is required on every row; never infer it from a developer or bug ID. |
| `component_catalog` | `(project_id, component_id)`, source-native component name, normalized component, repository/module mapping, mapping evidence/status. | Keep source-native names and mapping provenance; mappings can be `unverified` until reviewed. |
| `bug_report` | `(project_id, source_system, source_bug_id)`, component, created/updated times, status, severity/priority, permitted text fields, source snapshot/version. | Bug IDs are scoped by project and source; no cross-project ID joins. Keep comments out unless separately approved. |
| `assignment_event` | `(project_id, source_system, source_bug_id, event_id)`, event time, old/new assignee source IDs, event type, actor source ID if permitted, raw evidence reference, parser status. | Assignment labels come only from observed event evidence. Preserve unknown, inbox, removed, and reassigned states; never substitute current assignee for first assignment. |
| `developer_identity` | `(project_id, identity_namespace, source_identity_id)`, source system, normalized private key/reference, display/pseudonym, identity status. | Default to project-scoped identities. Avoid putting raw personal data in published outputs. |
| `identity_link` | source-scoped identity pair, match method, evidence, reviewer/status, timestamp. | Cross-project person links are opt-in, reviewed, and separate from project-local keys; exact email can be evidence but should still be privacy-reviewed. Name similarity is a candidate only. |
| `git_commit` / `git_commit_file` | `(project_id, repository_id, commit_id)`; author and committer timestamps, source identity key, subject; file path and mapped component. | Preserve source repo and original timestamp semantics. Separate author-time and committer-time analyses. Track extraction range/completeness. |
| `duplicate_link` | source-scoped duplicate and canonical bug keys, link type/time, provenance and observed-at time. | Treat as a directed, time-aware relationship; do not make future links/features available before their observation time. |
| `developer_feature_snapshot` | bug key, candidate project-scoped identity, prediction cutoff, feature window, expertise/recency/workload features, evidence coverage. | Features must be computable from evidence available strictly before cutoff; record unknown/missing separately from zero. |
| `ranking_evaluation` | project, split/cutoff, candidate set definition, label policy, metric, baseline/model version, confidence/calibration method. | Split temporally and by project-aware identity rules; report per-project results before pooled results. |

### 4.2 Label and identity safeguards

1. Retain the current JDT labels and artifacts as immutable source-versioned
   inputs. Any new normalized outputs are separate derived datasets.
2. Keep JDT, Platform, and PDE source IDs distinct and composite-keyed. A person
   working across projects may have three local identities unless a separate,
   approved identity-link review establishes a connection.
3. Store assignment event history and label adjudication separately. Use
   first eligible direct assignment as one possible training target only after
   cutoff policy review; retain previous-assignee-only/ambiguous evidence in a
   separate tier, as JDT does.
4. Preserve source evidence, event time, availability/observation time, parser
   status, and transformation version. Exclude post-cutoff information from
   features, including later duplicate links and later Git activity.
5. Never classify unmatched Git authors as confirmed people or confirmed new
   developers. Keep them `unknown/unlinked`.
6. Define a shared feature contract, but compute component expertise within
   project/repository mappings. Do not collapse unrelated same-named components
   across projects.

## 5. Ordered execution roadmap

This sequence is conditional. The present user request authorizes planning
only; each source collection stage requires approval before any download or
request.

### Phase 0 — Freeze and define gates

1. Preserve all existing JDT files, scripts, and Git metadata; record the
   current inventory/checksums as the baseline. Do not rerun expensive
   extraction scripts just to recreate that baseline.
2. Approve an exact prediction task and cutoff policy: first assignment versus
   reassignment, treatment of inbox/unassigned, eligible components, and
   temporal split.
3. Review collection terms, privacy, permitted fields, retention, and
   publication rules. Keep comments excluded unless explicitly reviewed.
4. Set project-specific source/version namespaces and component mapping
   review criteria before collection.

### Phase 1 — Complete JDT without disrupting the baseline

1. Inspect existing JDT audit outputs and script logic; do not regenerate
   existing tables. Resolve any open label, timestamp, identity, or Git
   history questions in separate review outputs.
2. Specify and validate an assignment-event/workload reconstruction using
   events available at each prediction cutoff. Handle reopened, closed,
   unassigned, and reassigned bugs explicitly; compare reconstructed states to
   observable status/assignee evidence.
3. Validate temporal features for strict cutoff, timezone parsing, author vs.
   committer timestamps, history completeness, and verified patch deduplication.
   Retain the existing strict version and create any alternatives separately.
4. Build prediction-time-filtered related-bug/duplicate features and ensure
   future duplicate reports and links cannot leak into a prediction.
5. Define project-scoped candidate sets and a temporally held-out Top-K
   baseline. Report Recall@K/MRR or other approved ranking metrics and
   per-project confidence intervals where sample size permits.
6. Evaluate fixed versus adaptive feature selection, explanation fidelity,
   cold-start cohorts, and confidence calibration. Do not claim these features
   as complete until separate validation criteria pass.

### Phase 2 — Platform source and collection (after approval)

1. Gate on Bugzilla REST returning valid expected JSON for product/component
   metadata and a minimal bug sample. Current evidence says this gate fails.
   If it remains unavailable, stop and submit any alternate archive proposal
   for approval; do not silently substitute GitHub issues.
2. Confirm Platform product/component names, historical activity availability,
   permitted fields, and source terms. Create a reviewed mapping from each
   selected Bugzilla component to a Platform repository/module; start with
   aggregator candidates `eclipse.platform`, `eclipse.platform.swt`, and
   `eclipse.platform.ui` only where mapping is evidenced.
3. After the source gate, collect only the approved bounded historical bug
   fields and assignment events. Keep comments excluded. Record paging,
   temporal coverage, missing history, source timestamps, and extraction
   version; do not infer missing assignment events.
4. Separately obtain approved Git history for the mapped repositories and
   record refs/range, submodules, completeness, author/committer timestamps,
   file paths, and repository-specific contributor identities.
5. Validate bugs/events/components and Git extraction independently; review
   exact-email identity links and keep candidate/name-only links unresolved.
6. Build Platform-only expertise/recency/workload inputs and temporal
   evaluation splits before integrating with other projects.

### Phase 3 — PDE source and collection (after approval)

1. Apply the same Bugzilla availability and terms gate independently for PDE.
   Current evidence says the bounded REST requests returned shutdown HTML.
2. Confirm PDE product/component taxonomy and map it to the relevant modules
   in `eclipse-pde/eclipse.pde`; do not assume project-page area names map
   directly to Bugzilla components.
3. After approval, collect approved bounded bug fields and assignment
   transitions, excluding comments unless explicitly approved. Record event
   history completeness and source version.
4. Separately obtain approved PDE Git history with repository/ref coverage and
   extraction provenance. Keep the PDE roster and raw Git keys separate from
   JDT and Platform.
5. Validate event/label consistency, component mappings, identity review,
   Git-history completeness, and point-in-time feature availability.
6. Build PDE-only expertise/recency/workload inputs and temporal evaluation
   splits before integration.

### Phase 4 — Integrate and validate all three

1. Map each project into the common schema while preserving source-native
   fields, IDs, event histories, project-local identity keys, and provenance.
2. Run cross-project checks for key collisions, duplicate rows, invalid
   timestamps, unmapped components, ambiguous labels, and accidental
   identity merges. Reject pooled labels that lack project/source evidence.
3. Compare per-project and pooled feature distributions and ranking results.
   Use project-stratified reporting; do not let the larger JDT corpus hide
   Platform/PDE data sparsity or source bias.
4. Evaluate all nine features separately: expertise, recency, workload,
   explanation, cold-start behavior, adaptive selection, confidence
   calibration, duplicate/related detection, and Top-K ranking.
5. Publish a new versioned integrated dataset and validation report only after
   source terms/privacy review and approval. Do not replace existing JDT
   artifacts.

## Required validations before claiming completion

- **Source/provenance:** approved source and terms; source snapshot/version;
  coverage dates/refs; extraction errors and known omissions documented.
- **Bug/label quality:** unique composite bug keys; valid timestamp ordering;
  assignment transitions consistent with source evidence; primary versus
  ambiguous labels separated; no current-assignee-only label substitution.
- **Component integrity:** all normalized mappings reviewed and traceable to
  source-native component and repository/module.
- **Identity:** exact and manual links reviewed with evidence; candidate name
  matches remain unconfirmed; project-local identifiers preserved; privacy
  minimization applied.
- **Git:** commit and file counts reconciled to selected refs; author and
  committer times validated; bots/merges/cherry-picks/patch duplicates handled
  transparently; incomplete history marked.
- **Temporal leakage:** strict pre-cutoff feature availability tested for
  every feature family, including workload and duplicate/related links.
- **Feature-specific:** workload replay matches assignment state; explanations
  reproduce score contributions; confidence is calibrated on held-out data;
  cold-start cohort definitions are tested; adaptive/fixed comparison is
  controlled; duplicate detection and Top-K ranking use temporal holdouts.
- **Integration:** source-scoped keys and labels do not collide; per-project
  results are reported before any pooled metric; raw JDT baseline remains
  unchanged.

## Expected gaps after source collection

Even with approved Platform/PDE Bugzilla and Git data, collection alone will
not complete the system's nine features. Modeling and evaluation work will
still be required for prediction-time workload, integrated explainable
recommendations, cold-start behavior definitions, adaptive feature selection,
confidence calibration, point-in-time duplicate/related-bug retrieval, and
Top-K ranking. Git contribution expertise and recency will remain proxies for
bug-triage expertise; identity coverage and incomplete histories will remain
limitations. If assignment history or duplicate metadata is not available
from an approved source, workload and duplicate-related features must remain
explicitly unavailable for that project rather than be inferred.

## Current conclusion

JDT is substantially prepared but still has feature-readiness and temporal
validation gaps. Platform and PDE have not been collected locally; both remain
blocked on a usable, approved bug/assignment-history source. Their official
Git repositories are promising sources for contribution and recency evidence,
but Git alone cannot supply bug reports, assignment labels, or workload state.
The next step is approval of the staged gates and collection scope—not
collection itself.
