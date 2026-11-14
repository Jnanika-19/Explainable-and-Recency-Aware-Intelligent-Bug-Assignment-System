# JDT Workload Event Scan Report

Scan date: 2026-11-11 12:13:49Z

## Scope and source

- Source: `dataset/raw/JDT.csv` (read-only, one streaming pass).
- Source size before/after scan: 6,377,569,970 bytes.
- Source last-write time before/after scan: `2024-11-27T08:18:00+00:00`.
- Read fields: bug ID, product, component, creation time, assignee, status, resolution, severity, priority, and `History/Activity Log`. Summary, description, comments, and reporter identity values were not exported.
- Assignee values in derived event output are represented by stable opaque JDT account keys; exact verified identities use the existing JDT-only developer IDs. No name-based identity merging was performed.

## Scan results

- Raw records: 63,266; unique bug IDs: 63,266.
- History rows with non-empty, valid activity lists: 61,386.
- Missing/empty/invalid histories: 1,880.
- Tracked lifecycle changes extracted: 287,917.
- Rows whose final replay matched current raw state: 47,959.
- State-replay mismatch rows: 13,427; incomplete/not-testable rows: 1,880.
- Invalid source-history event timestamps: 0; source-history events before bug creation: 45; duplicate bug IDs: 0; malformed CSV rows: 0.
- The exported tracked-lifecycle event table contains 287,917 unique event keys; no exported tracked event precedes its bug's creation time.
- Text-change metadata events (`summary`/`description` fields) observed: 21,397; text values were not exported.
- Text-change entries with both old/new fields: 21,397; inspect timestamps and field semantics before attempting historical text reconstruction.

### History field counts

| History field | Changes |
|---|---:|
| `alias` | 12 |
| `assigned_to` | 59,791 |
| `attachments.description` | 111 |
| `attachments.filename` | 8 |
| `attachments.isobsolete` | 4,998 |
| `attachments.ispatch` | 158 |
| `attachments.mimetype` | 277 |
| `blocks` | 5,156 |
| `cc` | 80,318 |
| `component` | 15,866 |
| `deadline` | 11 |
| `depends_on` | 5,269 |
| `flagtypes.name` | 8,287 |
| `groups` | 137 |
| `is_cc_accessible` | 8 |
| `is_confirmed` | 37 |
| `is_creator_accessible` | 8 |
| `keywords` | 5,426 |
| `op_sys` | 3,440 |
| `platform` | 2,774 |
| `priority` | 7,007 |
| `product` | 4,376 |
| `qa_contact` | 2,403 |
| `resolution` | 75,426 |
| `see_also` | 18,337 |
| `severity` | 6,192 |
| `status` | 119,259 |
| `summary` | 21,397 |
| `target_milestone` | 51,988 |
| `url` | 66 |
| `version` | 2,587 |
| `whiteboard` | 10,878 |

## Workload decision

**Point-in-time workload not generated.** The scanned history did not meet the completeness/replay criteria. The event and coverage outputs retain the observed evidence, but missing or invalid history prevents reliable active-queue reconstruction; no workload values were guessed.

## Validation and limitations

- Every raw bug row has a coverage record; all parseable lifecycle change events are retained in the event file.
- `scripts/validate_jdt_workload_outputs.py` passed: 63,266 unique coverage bug IDs, 287,917 unique event keys, exact coverage/event-count agreement, no invalid timestamps, no pre-creation exported events, and no orphan events.
- Blank-value audit: `current_resolution` is blank for 4,646 coverage rows; `old_value` is blank for 63,896 event rows and `new_value` for 7,894. These source values were preserved as blank and not imputed; blanks may represent empty/cleared values or missing source values.
- Derived assignee keys are pseudonymous account keys, not person merges. Unmatched email accounts remain separate.
- Current-state replay consistency checks compare the first recorded old value and chronological changes with current product/component/assignee/status/resolution/severity/priority values.
- Historical text-change counts only establish that summary/description field changes were recorded; text bodies and snapshots were not exported or indexed.
- A current export may not prove complete historical coverage merely because replay reaches the current values. Missing history, unresolved aliases, or unrecorded transitions remain limitations.
- Scan elapsed time: 70.5 seconds. Derived-output sizes: 39,003,900 bytes.

## Outputs

- `dataset/processed/jdt_workload/jdt_assignment_lifecycle_events.csv` (32,660,763 bytes)
- `dataset/processed/jdt_workload/jdt_bug_history_coverage.csv` (6,343,137 bytes)
