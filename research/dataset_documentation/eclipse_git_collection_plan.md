# Eclipse Platform and PDE Git Collection Plan

Prepared: 2026-11-11

## Purpose and constraints

This plan prepares a Git-history collection stage for Eclipse Platform and PDE.
It does not authorize or perform collection.

No network requests, clones, downloads, repository updates, or changes to
existing datasets were performed. The source URL observations below come from
the existing local source-probe documentation; URLs not explicitly linked
there are labeled as inferred and must be confirmed before collection. No
reliable repository-size figures were available in the local documentation, so
no download-size estimate is invented.

## 1. Repository identity and official URL evidence

The source report is
[`eclipse_project_source_probe.md`](./eclipse_project_source_probe.md). It
identifies the Platform SDK aggregator separately from the repositories listed
in its `.gitmodules`.

| Purpose | Repository | URL | Evidence and status |
|---|---|---|---|
| Platform build/release aggregator | `eclipse.platform.releng.aggregator` | `https://github.com/eclipse-platform/eclipse.platform.releng.aggregator` | Explicitly linked in the local source report as the Platform SDK aggregator. |
| Platform component | `eclipse.platform` | `https://github.com/eclipse-platform/eclipse.platform` | The report names this as a `.gitmodules` source repository but does not print its URL. URL is inferred from the organization/repository name; confirm from the aggregator's `.gitmodules` before collection. |
| Platform SWT component | `eclipse.platform.swt` | `https://github.com/eclipse-platform/eclipse.platform.swt` | The report names this as a `.gitmodules` source repository but does not print its URL. URL is inferred; confirm from `.gitmodules` before collection. |
| Platform UI component | `eclipse.platform.ui` | `https://github.com/eclipse-platform/eclipse.platform.ui` | Explicitly linked in the local source report. |
| PDE | `eclipse.pde` | `https://github.com/eclipse-pde/eclipse.pde` | Explicitly linked in the local source report as the official PDE repository. |

**Important naming correction:** “Platform aggregator: `eclipse.platform`” is
ambiguous and, according to the existing report, incorrect. The aggregator is
`eclipse.platform.releng.aggregator`; `eclipse.platform` is one of its
component repositories. The three requested Platform component repository
names are `eclipse.platform`, `eclipse.platform.swt`, and
`eclipse.platform.ui`.

The four requested destination paths are component histories, not the
aggregator:

- `dataset/external/eclipse.platform`
- `dataset/external/eclipse.platform.swt`
- `dataset/external/eclipse.platform.ui`
- `dataset/external/eclipse.pde`

If aggregator history is separately approved and needed for build/release
mapping, store it separately as
`dataset/external/eclipse.platform.releng.aggregator`. Do not place its
contents in `dataset/external/eclipse.platform`.

## 2. Necessity and overlap assessment

The aggregator builds/assembles the Eclipse SDK and its `.gitmodules` lists
multiple repositories, including the three Platform component candidates,
JDT, PDE, and Equinox. This was recorded in the source report; the actual
`.gitmodules` contents and current URLs have not been independently checked in
this offline planning task.

- **For developer expertise, recency, and cold-start signals in source code:**
  collect the relevant component repositories (`eclipse.platform`,
  `eclipse.platform.swt`, and `eclipse.platform.ui`) and PDE
  (`eclipse.pde`) independently. These contain the file-change histories
  needed for project/module contribution features.
- **The aggregator is not a substitute for component repositories.** It
  primarily coordinates build/release inputs and represents submodules as
  gitlinks. It may have valuable release and submodule-pointer history, but
  it does not contain the full component commit histories as ordinary files.
- **The aggregator is not required for initial contributor features** if the
  component repositories and a reviewed component-to-repository mapping are
  available. It is useful as a mapping/build-provenance reference and could be
  added later if release alignment is a requirement.
- Cloning the aggregator with recursive submodules would check out its
  component submodules in addition to the standalone clones. That duplicates
  object storage/worktrees and can pull unrelated JDT, PDE, and Equinox
  repositories. Do not use `--recurse-submodules` for this collection.
- Git does not duplicate component history merely because the aggregator
  contains gitlinks. The avoidable duplication is fetching/checking out the
  submodule repositories a second time inside the aggregator clone.

**Recommendation:** defer the aggregator clone. Collect only the four listed
component repositories, without submodules. Revisit aggregator history only
if a concrete release mapping or repository coverage need is identified.
This keeps the collection aligned to the stated dataset scope and avoids
unnecessary downloads.

## 3. Local storage check

The local `dataset/external/` inventory showed only `eclipse.jdt.core/` and
three unusual files within it, including a Git-history extraction error
artifact. No local `eclipse.platform`, `eclipse.platform.swt`,
`eclipse.platform.ui`, `eclipse.pde`, or Platform aggregator repository was
shown. The JDT Git inventory also describes the existing JDT clone as a
partial `blob:none` clone and warns that its checkout has many missing tracked
paths. It must remain untouched.

This is a non-invasive workspace inventory, not an exhaustive filesystem
search for similarly named repositories elsewhere on the machine. Before any
approved collection, recheck only the four exact destination paths and stop
if any exists; do not overwrite or reuse an unexpected directory without
review.

## 4. History-preserving, storage-conscious strategy

### Recommended clone mode

For each approved component repository:

1. Use a full-history clone with **no `--depth`**, so commit ancestry for the
   advertised branches is retained.
2. Request `--filter=blob:none` to initially omit file-content blobs. Commit
   and tree history is retained; file contents may be fetched lazily later.
3. Use `--no-checkout` to avoid materializing a working tree during history
   collection.
4. Do not use `--single-branch`, `--shallow-since`, or `--shallow-exclude`.
   Preserve all branches advertised by the server, and record which refs were
   advertised at collection time. Ordinary clones do not promise hidden,
   unadvertised refs or unreachable objects.
5. Do not recurse into submodules. The four targets are independent history
   repositories.
6. Confirm the remote accepts partial-clone filtering. If it does not, stop
   and ask before falling back to a full-blob clone; do not silently make a
   potentially much larger download.

Illustrative PowerShell commands, **not executed**, from the repository root
would be:

```powershell
git clone --filter=blob:none --no-checkout `
  https://github.com/eclipse-platform/eclipse.platform.git `
  dataset\external\eclipse.platform

git clone --filter=blob:none --no-checkout `
  https://github.com/eclipse-platform/eclipse.platform.swt.git `
  dataset\external\eclipse.platform.swt

git clone --filter=blob:none --no-checkout `
  https://github.com/eclipse-platform/eclipse.platform.ui.git `
  dataset\external\eclipse.platform.ui

git clone --filter=blob:none --no-checkout `
  https://github.com/eclipse-pde/eclipse.pde.git `
  dataset\external\eclipse.pde
```

The `.git` suffix is optional in clone URLs. These exact commands assume the
inferred Platform component URLs above have first been confirmed from
authoritative repository metadata. The commands intentionally do not include
the aggregator and do not use `--recurse-submodules`.

### What “complete history” means here

This mode preserves full commit ancestry for refs the server advertises and
the clone fetches, while omitting blobs initially. It is not a byte-for-byte
mirror of all server-side objects: hidden/unadvertised refs, unreachable
objects, and server-retained deleted data are not guaranteed. Record this
scope accurately as “full history of fetched advertised refs,” not “all
repository data.”

Partial-clone filtering minimizes initial blob transfer but may not minimize
later transfer if commands access file contents. A later checkout, blame,
diff requiring blobs, or some analysis may cause lazy fetches. Keep the
original filtered clone intact; if a full working tree is later needed, decide
and budget that separately. Avoid checking out every submodule.

## 5. Size and download estimate

No reliable size estimate is present in the local reports. Repository size
depends on history length, large/binary blobs, Git object compression,
advertised refs, server-side filter support, and later lazy fetches.

`--filter=blob:none` should reduce initial transfer by omitting file contents,
but it does not guarantee a particular size or eliminate all later downloads.
Before approval, the repository host's reported size or a dry-run/remote
estimate may be consulted only if network access is authorized. After
collection, record actual pack/object storage with `git count-objects -vH`;
do not treat that local size as the total bytes transferred unless transfer
metrics are separately captured.

## 6. Submodules and coverage

- The existing source report says the Platform SDK aggregator recommends
  recursive submodule handling for building the full SDK and that its
  `.gitmodules` lists Platform, SWT, UI, JDT, PDE, and Equinox repositories.
  That build-oriented advice is not a requirement for this data collection.
- The target component histories should be cloned independently; do not
  initialize submodules from any of them unless repository inspection later
  shows they are required to understand an in-scope component.
- If an approved aggregator clone is added, first record `.gitmodules`,
  gitlink commit IDs, and mappings. Do not recursively fetch submodules.
- Record repository URL, clone date, Git version, branch heads, tags, remote
  refs, filter/promisor configuration, whether shallow, and any warnings about
  missing objects. Reconcile commit counts to the fetched refs and note that
  counts across repositories are not directly additive if commits are shared.
- Git author identity fields may contain personal data. Keep raw Git metadata
  access-controlled and do not publish email/name rosters without privacy
  review. An author key derived from an email or name is a repository-local
  key, not a confirmed cross-project identity.

## 7. Validation commands after approved collection

Run these locally after a clone; they are validation examples and were not
executed. They do not fetch updates. Replace `<repo-path>` with one of the
four destination paths.

```powershell
# Confirm the path is a Git repository and whether it is shallow.
git -C <repo-path> rev-parse --show-toplevel
git -C <repo-path> rev-parse --is-shallow-repository

# Commit counts reachable from all local refs; list fetched remote branches and tags.
git -C <repo-path> rev-list --all --count
git -C <repo-path> branch --remotes
git -C <repo-path> tag --list

# Record remotes, object storage, and partial-clone settings.
git -C <repo-path> remote --verbose
git -C <repo-path> count-objects -vH
git -C <repo-path> config --get-regexp '^remote\..*\.(promisor|partialclonefilter)$'

# Integrity/connectivity check. Disable lazy fetching so validation does not
# silently make additional network requests in a partial clone.
$env:GIT_NO_LAZY_FETCH = '1'
git -C <repo-path> fsck --full --connectivity-only --no-reflogs
Remove-Item Env:GIT_NO_LAZY_FETCH
```

Expected checks and interpretation:

- `--is-shallow-repository` should print `false`.
- `rev-list --all --count` should be recorded as the count reachable from
  fetched local refs. This does not prove that the server exposed every
  historical or hidden ref.
- Remote branches and tags should be saved in the collection manifest. A
  default clone fetches advertised branch heads and tags reachable under
  normal Git clone rules; compare with host metadata if complete ref coverage
  is a requirement.
- `count-objects -vH` reports local loose/packed object storage. A filtered
  clone should have promisor/filter configuration; a missing config entry
  should trigger review rather than an assumption that filtering worked.
- `fsck` must be interpreted with partial-clone promisor semantics. Do not
  classify intentionally omitted promisor blobs as corruption. Investigate
  any broken commits/trees or missing non-promised objects. The no-lazy-fetch
  setting is intended to prevent validation from fetching omitted objects.
- Capture command output and errors in a per-repository validation record;
  do not rely on a single count as proof of full upstream completeness.

## 8. Use of Git histories for the project features

- **Historical expertise:** aggregate changed files/commits by repository and
  mapped component. Treat this as code-contribution expertise, not as proof of
  Bugzilla assignment expertise. Maintain repository and component mapping
  provenance.
- **Recency:** compute activity windows relative to the bug prediction cutoff,
  using a documented choice of author timestamp versus committer timestamp.
  Exclude commits not available by that cutoff; retain both timestamps so the
  choice can be audited.
- **Cold-start evidence:** construct a project/repository-scoped contributor
  roster, including first/last observed contribution and history coverage.
  Contributors with no reviewed issue-tracker identity remain
  `unknown/unlinked`; Git history alone cannot prove they are new developers
  or link them to a Bugzilla assignee.
- Git alone does not provide bug text, assignment transitions, active
  workload, or verified bug-fix labels. These datasets remain blocked pending
  a separately approved source for historical Platform/PDE bug and assignment
  data. Do not infer labels from commit messages without a validated,
  time-aware link methodology.

## 9. Approval gates before collection

Before any clone/download:

1. Confirm the inferred `eclipse.platform` and `eclipse.platform.swt` URLs
   from the aggregator's authoritative `.gitmodules` or project-owned
   repository metadata.
2. Confirm whether the aggregator itself is required; current recommendation
   is to defer it because it is not needed for component commit-history
   features and recursive submodules would duplicate/expand collection.
3. Approve the four exact destinations, repository list, `blob:none` filter,
   no-checkout policy, branch/ref coverage definition, and no-submodule rule.
4. Approve handling of Git author names/emails and storage/retention of raw
   histories.
5. Recheck that the exact destinations do not exist. Stop on any collision;
   never overwrite the existing JDT repository or its outputs.

## Current conclusion

The local source report supports collecting three separate Platform component
histories and the PDE history. It distinguishes the Platform SDK aggregator
(`eclipse.platform.releng.aggregator`) from the `eclipse.platform` component.
The aggregator appears unnecessary for the initial developer-evidence
collection and should not be cloned recursively. A full-history,
`blob:none`, `--no-checkout`, non-recursive clone is the recommended
storage-conscious approach, subject to server filter support and approval.
Reliable size estimates are unavailable. No collection has been performed;
wait for approval before cloning.
