# Dataset Handover Package

**Project:** Explainable and Recency-Aware Intelligent Bug Assignment System
**Audit date:** 2026-11-11
**Scope:** Existing local datasets and their collection, preprocessing, validation, and handover status. No collection, model training, or model evaluation was performed for this handover.

## Start here

1. Read [FINAL_DATASET_HANDOVER_REPORT.md](./FINAL_DATASET_HANDOVER_REPORT.md) for the status and decision summary.
2. Read [DATASET_INVENTORY.md](./DATASET_INVENTORY.md) for the main files, locations, and counts.
3. Use [DATA_DICTIONARY.md](./DATA_DICTIONARY.md) to understand the integrated tables and their columns.
4. Review [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md) before treating any data as an input or label.
5. Use [TEAM_HANDOVER_MATRIX.md](./TEAM_HANDOVER_MATRIX.md) to coordinate the next implementation stage.
6. Use [dataset_file_manifest.csv](./dataset_file_manifest.csv) for file sizes, row counts, hashes, source, validation, and sensitivity metadata.

## Dataset access

Dataset paths in this package are relative to the repository root. Existing data remain in `dataset/raw/`, `dataset/processed/`, and `dataset/external/`; this package references them rather than copying them. The 6.38 GB JDT Bugzilla export and Git repository clones were not duplicated.

Start with `dataset/processed/jdt_integrated/` for the separated candidate, target, context, cold-start, duplicate-target, and identity tables. Prefer `jdt_integrated_bug_context_by_bug.csv` over the candidate-expanded context table. Do not join target or evaluation-only columns into prediction-time inputs.

Some data include Bugzilla text, contributor names/emails, account identifiers, or opaque identity mappings. Access is for authorized project work only. Do not place identity metadata in public artifacts or logs. See the manifest sensitivity field and [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).

## Provenance and safe reproduction

The existing dataset documentation under `research/dataset_documentation/` is the provenance record. This handover cross-checks its claims against local files and existing validators. Reproduction commands are listed in [VALIDATION_RESULTS.md](./VALIDATION_RESULTS.md); validation modes were selected to avoid rewriting existing datasets.

The raw `dataset/raw/JDT.csv` file was not reopened or hashed in this audit. Its manifest SHA-256 is copied from the earlier `dataset_availability.md` inventory, while its current size matches that inventory. This avoids repeating a scan of the large source. The raw checksum is therefore marked as previously recorded, not independently reverified in this handover.

Do not rerun scripts that overwrite existing outputs without reviewing their source and taking an approved backup. In particular, existing documentation notes that some legacy builders truncate their output files.
