# Eclipse Platform Git Collection Report

Collection date: 2026-11-11

## Result

Successfully cloned **only** the Eclipse Platform component repository
`eclipse.platform` to:

`dataset/external/eclipse.platform`

No other repositories were cloned. The existing JDT repository and datasets
were not modified.

## Pre-clone checks

- **Authoritative URL:** The `.gitmodules` file in the
  `eclipse-platform/eclipse.platform.releng.aggregator` repository lists the
  submodule path `eclipse.platform` with URL
  `https://github.com/eclipse-platform/eclipse.platform.git` and branch
  `master`. This confirms the exact source URL used below.
- **Destination:** `dataset/external/eclipse.platform` did not exist before
  cloning. The command also checked the exact destination again immediately
  before running and would refuse if it had appeared.
- **Git:** `git version 2.53.0.windows.3`.
- **Partial-clone support:** A protocol-v2 `git ls-remote --heads --tags`
  capability probe succeeded (exit code 0). The server advertised
  `fetch=shallow wait-for-done filter`, confirming support for filtering.

## Clone command

```powershell
git clone --filter=blob:none --no-checkout `
  https://github.com/eclipse-platform/eclipse.platform.git `
  dataset\external\eclipse.platform
```

The clone completed successfully (exit code 0). It used no depth limit,
single-branch restriction, or recursive submodule option. The clone has no
working-tree checkout.

## Clone validation

| Check | Result |
|---|---|
| Remote URL | `origin` fetch/push: `https://github.com/eclipse-platform/eclipse.platform.git` (`blob:none` shown on fetch remote) |
| Default remote HEAD | `refs/remotes/origin/master` |
| Remote branches | 73 branch heads, plus the `origin/HEAD -> origin/master` symbolic reference |
| Tag refs | 10,297 |
| Commits reachable from all local refs | 46,304 |
| Shallow repository | `false` |
| Partial-clone configuration | `remote.origin.promisor=true`; `remote.origin.partialclonefilter=blob:none` |
| Local object storage | 511,387 packed objects; 1 pack; pack size 52.65 MiB; 0 loose objects; 0 garbage |
| Connectivity/integrity command | `git fsck --full --connectivity-only --no-reflogs`, with `GIT_NO_LAZY_FETCH=1`; exit code 0 |

The `fsck` output included dangling commit/tree objects, but no missing-object
or connectivity failure was reported and the command exited successfully.
Dangling objects were not removed.

The branch and tag counts refer to refs available locally after this clone.
They do not prove the server exposed hidden or unadvertised refs. The commit
count is reachability across local refs, not a count for only the default
branch.

## Scope and next gate

This is a full-history clone of fetched advertised refs with blobs omitted
initially; it is not a mirror of hidden/unreachable server objects. Later
operations requiring file contents may trigger lazy blob downloads.

Stop after this repository as requested. SWT, UI, and PDE have not been
collected. Wait for explicit approval before starting any of them.
