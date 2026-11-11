# JDT Member 2 Preprocessing Decisions

## Inputs and outputs

The preprocessing workflow reads these original `data/raw/` files without
writing to them:

- `jdt_training_primary.csv`
- `developer_profile_summary.csv`
- `developer_component_expertise.csv`

The profile and component expertise files are used only for identity and
aggregate reconciliation. They are not model features because they include
assignments from after the training cutoff.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m ml_model.preprocess_jdt
```

The workflow writes these local artifacts to `data/processed/`:

- `jdt_known_entry_preprocessed.csv`
- `jdt_provisional_exploratory.csv`
- `jdt_known_entry_train.csv`
- `jdt_known_entry_test.csv`
- `jdt_test_temporal_expertise.csv`
- `jdt_preprocessing_report.json`

The processed-data directory is ignored by Git under the existing repository
rules. The source scripts and this documentation are maintained under
`ml_model/` and `docs/member2/`.

## Ground truth and invalid-row checks

Only rows with `label_type=known_entry` are written as supervised targets.
`provisional` rows go to a separate file with the assignment renamed
`assigned_developer_exploratory`; the training script requires `known_entry`
on every train/test row. It does not read the provisional file.

The workflow validates required columns and all timestamps, unique bug IDs,
nonblank developer IDs, `assignment_added` event type, direct assignment
evidence, readable history, JDT product, and chronological consistency.
Known-entry `jdt_entry_time` must be between bug creation and the assignment
event. A failed validation raises an error instead of silently repairing or
dropping an assignment.

The profile and expertise aggregates reconcile to all 33,246 primary rows:
335 developer identities match exactly after normalization, profile counts
match known/provisional counts, component counts reconcile, and component
shares sum to 1. There are no duplicate primary bug IDs, duplicate profile
identities, or duplicate expertise developer-component pairs.

## Text and missing values

Titles and descriptions use the existing BugWise HTML/text cleaner. The source
stores escaped line breaks, so the Member 2 preprocessing restores escaped
line endings before filtering long stack-trace lines. Empty text is retained as
an empty string for TF-IDF; rows are not discarded for missing descriptions.
This yields 4 empty descriptions and no empty titles in the 1,651 verified
records.

The provisional exploratory file contains 8 empty titles and 231 empty
descriptions after cleaning. These do not enter supervised training.

## Identity and time handling

Developer IDs are trimmed and Unicode NFC-normalized while preserving case.
Case-folding is intentionally not performed because
`Lars.Vogel@vogella.com` and `lars.vogel@vogella.com` are separate exact IDs in
all three inputs. Original label spelling is preserved alongside normalized
`developer_id` in the processed files.

All timestamps are parsed as timezone-aware UTC and serialized in ISO 8601 UTC
format. Prediction time is `creation_time`; the assignment label becomes
available at `label_event_time`.

## Leakage-safe chronological split

The 80/20 chronological boundary on verified rows is
`2010-04-09T07:54:03Z`.

- Training includes only bugs created before the cutoff **and** assignment
  events recorded before the cutoff.
- Test includes verified bugs created at or after the cutoff.
- 22 bugs created before the cutoff are excluded because their assignment
  events were not known by the cutoff.
- This produces 1,298 training rows across 79 developer classes and 331 test
  rows.
- Test has 143 rows whose assigned developer appeared in training and 188 rows
  whose assigned developer was unseen in training.

`jdt_test_temporal_expertise.csv` contains candidate-level counts, component
counts/shares, and recency values for each test bug. Each value is rebuilt from
verified assignment events strictly earlier than that bug's creation timestamp.
The table does not contain the test target and is not an input to the text-only
baselines.

The existing profile and expertise aggregates are not used in training or
evaluation features. The baseline uses only cleaned title and description;
developer ID, bug ID, component, severity, priority, label fields, and
timestamps are excluded from model inputs.

## Known limitations

The supplied files do not contain version timestamps for title and description
changes. The split and target labels are chronological, but it is not possible
to prove that every supplied text value is exactly the version visible at bug
creation time. Treat the results as a leakage-controlled baseline on the
provided text, with point-in-time feature availability still requiring
confirmation from source history.
