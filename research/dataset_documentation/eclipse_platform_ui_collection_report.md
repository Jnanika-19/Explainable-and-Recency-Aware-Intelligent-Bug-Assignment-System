# Eclipse Platform UI Git Collection Report

Collection date: 2026-11-11

## Result

Successfully cloned **only** the Eclipse Platform UI repository,
`eclipse.platform.ui`, to:

`dataset/external/eclipse.platform.ui`

No JDT, Eclipse Platform, or SWT repository was modified. PDE was not
collected.

## Pre-clone checks

- **Official URL:** The `.gitmodules` file in the
  `eclipse-platform/eclipse.platform.releng.aggregator` repository lists the
  `eclipse.platform.ui` submodule URL as
  `https://github.com/eclipse-platform/eclipse.platform.ui.git`, branch
  `master`. This matches the user-provided URL.
- **Git:** `git version 2.53.0.windows.3`.
- **Destination:** `dataset/external/eclipse.platform.ui` was absent before
  cloning and checked again immediately before the clone.
- **Partial-clone support:** A protocol-v2 `git ls-remote --heads --tags`
  capability probe succeeded (exit code 0). The server advertised
  `fetch=shallow wait-for-done filter`.

## Clone command

```powershell
git clone --filter=blob:none --no-checkout `
  https://github.com/eclipse-platform/eclipse.platform.ui.git `
  dataset\external\eclipse.platform.ui
```

The clone completed successfully (exit code 0). No depth limit,
single-branch restriction, or recursive submodule option was used. The clone
has no working-tree checkout.

## Validation

| Check | Result |
|---|---|
| Remote URL | `origin` fetch/push: `https://github.com/eclipse-platform/eclipse.platform.ui.git` (`blob:none` shown on fetch remote) |
| Default remote HEAD | `refs/remotes/origin/master` |
| Remote branch heads | 61 |
| Tags | 11,912 |
| Commits reachable from all local refs | 48,171 |
| Shallow repository | `false` |
| Partial-clone configuration | `remote.origin.promisor=true`; `remote.origin.partialclonefilter=blob:none` |
| Local object storage | 563,449 packed objects; 1 pack; pack size 69.78 MiB; 0 loose objects; 0 garbage |
| Connectivity check | `git fsck --full --connectivity-only --no-reflogs`, with `GIT_NO_LAZY_FETCH=1`; exit code 0; 10,155 output lines, no `error:`, `fatal:`, or `missing` entries |

Counts describe refs available locally after cloning and do not establish that
the server exposed hidden or unadvertised refs. The commit count is reachability
across local refs, not only the default branch. The integrity check did not
remove any objects.

## Scope and next gate

This is full history for fetched advertised refs, with file-content blobs
omitted initially. It is not a mirror of hidden or unreachable server objects;
later operations requiring file contents may trigger lazy blob downloads.

Collection and validation are complete for Platform UI. Stop here and wait for
approval before collecting PDE.
