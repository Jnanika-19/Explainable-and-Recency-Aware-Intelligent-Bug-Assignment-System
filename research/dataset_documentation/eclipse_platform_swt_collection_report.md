# Eclipse Platform SWT Git Collection Report

Collection date: 2026-11-11

## Result

Successfully cloned **only** the Eclipse Platform SWT repository,
`eclipse.platform.swt`, to:

`dataset/external/eclipse.platform.swt`

The earlier attempt using invalid `--filter=blob` failed before creating the
destination. This approved retry used `--filter=blob:none`. No JDT or
`eclipse.platform` files were modified. Eclipse Platform UI and PDE were not
collected.

## Pre-clone checks

- **Destination:** `dataset/external/eclipse.platform.swt` was checked and
  absent immediately before this attempt.
- **Git:** `git version 2.53.0.windows.3`.
- **Official remote:** The aggregator's `.gitmodules` lists
  `eclipse.platform.swt` at
  `https://github.com/eclipse-platform/eclipse.platform.swt.git`, branch
  `master`, matching the user-provided URL.
- **Partial-clone support:** A protocol-v2 `git ls-remote --heads --tags`
  capability probe succeeded (exit code 0). The server advertised
  `fetch=shallow wait-for-done filter`.

## Clone command

```powershell
git clone --filter=blob:none --no-checkout `
  https://github.com/eclipse-platform/eclipse.platform.swt.git `
  dataset\external\eclipse.platform.swt
```

The clone completed successfully (exit code 0). It used no depth limit,
single-branch restriction, or recursive submodule option. The clone has no
working-tree checkout.

## Validation

| Check | Result |
|---|---|
| Remote URL | `origin` fetch/push: `https://github.com/eclipse-platform/eclipse.platform.swt.git` (`blob:none` shown on fetch remote) |
| Default remote HEAD | `refs/remotes/origin/master` |
| Remote branch heads | 62 |
| Symbolic remote HEAD reference | `origin` points to `origin/master` |
| Tags | 12,132 |
| Commits reachable from all local refs | 35,391 |
| Shallow repository | `false` |
| Partial-clone configuration | `remote.origin.promisor=true`; `remote.origin.partialclonefilter=blob:none` |
| Local object storage | 405,019 packed objects; 1 pack; pack size 40.17 MiB; 0 loose objects; 0 garbage |
| Connectivity check | `git fsck --full --connectivity-only --no-reflogs`, with `GIT_NO_LAZY_FETCH=1`; exit code 0; 8,419 output lines, no `error:`, `fatal:`, or `missing` entries |

The branch count excludes the symbolic `origin/HEAD` reference. Counts describe
refs available locally after cloning; they do not prove that the server exposed
hidden or unadvertised refs. The commit count is reachability across local
refs, not just the default branch.

Because the clone used `--no-checkout`, files are not populated in the working
tree. Git status may therefore show tracked paths as absent from the working
tree; do not treat this as an incomplete clone or materialize blobs without
approval.

## Scope and next gate

This is full history for fetched advertised refs, with file-content blobs
omitted initially. It is not a mirror of hidden or unreachable server objects.
Future Git operations that need file contents may trigger lazy blob downloads.

Collection and validation are complete for SWT. Stop here and wait for approval
before collecting Eclipse Platform UI or PDE.
