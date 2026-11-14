# Eclipse PDE Git Collection Report

Collection date: 2026-11-11

## Result

Successfully cloned **only** the Eclipse PDE repository to:

`dataset/external/eclipse.pde`

No existing JDT, Eclipse Platform, SWT, or UI repository was modified. No
dataset consolidation was performed.

## Pre-clone checks

- **Project root:** repository root (`.`)
- **Git:** `git version 2.53.0.windows.3`.
- **Repository URL:** `https://github.com/eclipse-pde/eclipse.pde.git`.
  The URL was supplied as the official PDE repository and the remote
  successfully advertised Git refs.
- **Destination:** `dataset/external/eclipse.pde` was absent before cloning
  and checked again immediately before the clone.
- **Partial-clone support:** A protocol-v2 `git ls-remote --heads --tags`
  capability probe succeeded (exit code 0). The server advertised
  `fetch=shallow wait-for-done filter`.

## Clone command

```powershell
git clone --filter=blob:none --no-checkout https://github.com/eclipse-pde/eclipse.pde.git dataset/external/eclipse.pde
```

The clone completed successfully (exit code 0). No depth limit,
single-branch restriction, or recursive submodule option was used. The clone
has no working-tree checkout.

## Validation results

| Check | Result |
|---|---|
| Remote URL | `origin` fetch/push: `https://github.com/eclipse-pde/eclipse.pde.git` (`blob:none` shown on fetch) |
| Default remote HEAD | `refs/remotes/origin/master` |
| Remote branch heads | 64 |
| Tags | 10,442 |
| Commits reachable from all local refs | 21,392 |
| Shallow repository | `false` |
| Partial-clone configuration | `remote.origin.promisor=true`; `remote.origin.partialclonefilter=blob:none` |
| Local object storage | 270,682 packed objects; 2 packs; pack size 27.80 MiB; 0 loose objects; 0 garbage |
| Connectivity check | `git fsck --full --connectivity-only --no-reflogs`, with `GIT_NO_LAZY_FETCH=1`; exit code 0; 5,818 output lines, no `error:`, `fatal:`, or `missing` entries |

The branch count excludes the symbolic `origin/HEAD` reference. Counts describe
refs available locally after cloning; they do not prove that the server exposed
hidden or unadvertised refs. The commit count is reachability across local
refs, not only the default branch. The integrity check did not remove objects
or fetch omitted blobs.

## Warnings and limitations

This is full history for fetched advertised refs, with file-content blobs
omitted initially. It is not a mirror of hidden or unreachable server objects;
later operations requiring file contents may trigger lazy blob downloads.

Collection and validation are complete for PDE. Stop here. No dataset
consolidation has begun.
