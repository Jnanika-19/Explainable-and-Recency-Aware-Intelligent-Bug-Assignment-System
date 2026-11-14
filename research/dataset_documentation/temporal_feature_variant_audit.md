# Temporal Feature Variant Checksum and Semantics Audit

This is a read-only audit. No temporal dataset was regenerated or overwritten.

## Variant files

| File | Bytes | SHA-256 | Rows |
|---|---:|---|---:|
| `dataset\processed\cold_start\jdt_bug_developer_temporal_features.csv` | 46318635 | `d9bdf8eeea6ce11d583cbe33dc3d390563a209b2d6d756a4b7d8623f3cd8c622` | 432198 |
| `dataset\processed\cold_start\jdt_bug_developer_temporal_features_strict.csv` | 46318635 | `d9bdf8eeea6ce11d583cbe33dc3d390563a209b2d6d756a4b7d8623f3cd8c622` | 432198 |
| `dataset\processed\cold_start\jdt_bug_developer_temporal_features_inclusive.csv` | 46318635 | `d9bdf8eeea6ce11d583cbe33dc3d390563a209b2d6d756a4b7d8623f3cd8c622` | 432198 |

- Byte-identical by SHA-256: **True**.
- Rows in the temporal generator's exact-email source map: 13. A separate
  account-ID audit conservatively validates 9 and leaves 4 without a
  Bugzilla user ID unresolved.
- Expected bug/developer rows reconstructed from existing processed inputs: 432198.
- Strict variant rows matching reconstructed values: 432198.

## Interpretation

The generator found in the repository writes only the `strict` filename.
Its `bisect_left(timestamps, bug_time)` excludes commits whose committer
timestamp equals bug creation time, so the implemented cutoff is strictly
before bug creation. The file's feature counts are Git code-contribution
proxies for 13 source-map email candidates, not Bugzilla assignment history
or active workload. The separate conservative identity audit verifies only
9 of those candidates; 4 lack a Bugzilla user ID in the available audit.
The base and inclusive filenames have no distinct generator in the inspected
scripts. Preserve all names but treat them as byte-identical copies, not
separately verified strict/inclusive variants.

## Validation

- Reconstructed strict feature rows from the existing primary training
  table, source exact-email map, JDT Git commit/file CSVs, and bulk-commit
  audit, using the existing script's duplicate-patch and cutoff rules.
- Checked all variants' headers, IDs, target domain, nonnegative features,
  nested 30/90/365-day window counts, and nonnegative recency values.
- No raw JDT export was opened; source inputs were existing derived files.

## Result

**PASS**
