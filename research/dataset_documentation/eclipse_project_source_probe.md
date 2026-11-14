# Eclipse Project Source and Licensing Probe

Probe date: 2026-11-11

## Result

The bounded Bugzilla probe did not return usable product or bug data. The
endpoints below returned HTTP 200 with `text/html`, but the body was the Eclipse
temporary-shutdown page rather than the expected Bugzilla REST JSON. Thus the
product names, components, record schemas, and historical activity availability
could not be verified against live records. No bug records or comments were
collected.

| Probe | Request | Result |
|---|---|---|
| Platform product metadata | `GET /rest/product/Platform` | `200 text/html`, temporary-shutdown page |
| PDE product metadata | `GET /rest/product/PDE` | `200 text/html`, temporary-shutdown page |
| Platform minimal bug query | `GET /rest/bug?product=Platform&limit=1&include_fields=id,product,component` | `200 text/html`, temporary-shutdown page |
| PDE minimal bug query | `GET /rest/bug?product=PDE&limit=1&include_fields=id,product,component` | `200 text/html`, temporary-shutdown page |

This is not evidence that the endpoint would return those product names when
operational. The Bugzilla REST documentation describes bug fields and REST
operations, but live history/comment availability must be confirmed after
service recovery. Bugzilla's current issue pages are not replaced with GitHub
Issues in this study because they do not establish the historical Bugzilla
assignment-event stream needed by the research.

## Project and repository evidence

### Eclipse Platform

- The [Eclipse Platform project page](https://projects.eclipse.org/projects/eclipse.platform)
  identifies the project and lists Eclipse Public License 2.0 (EPL-2.0) as a
  project license. File headers and NOTICE files may provide more specific
  terms.
- The [Platform SDK aggregator](https://github.com/eclipse-platform/eclipse.platform.releng.aggregator)
  states that it builds the Eclipse SDK and recommends cloning with recursive
  submodules. Its
  [`.gitmodules` file](https://raw.githubusercontent.com/eclipse-platform/eclipse.platform.releng.aggregator/master/.gitmodules)
  lists `eclipse.platform`, `eclipse.platform.swt`, and `eclipse.platform.ui`
  source repositories, as well as JDT, PDE, and Equinox repositories.
- The [Platform UI repository](https://github.com/eclipse-platform/eclipse.platform.ui)
  identifies EPL-2.0 and says ongoing issue tracking is on GitHub. This is not a
  substitute for the legacy Bugzilla data.
- The submodule list is a repository-candidate inventory, not a confirmed
  Bugzilla-component-to-repository crosswalk. That crosswalk cannot be
  completed until Platform Bugzilla product/component metadata is accessible.

### Eclipse PDE

- The [Eclipse PDE project page](https://projects.eclipse.org/projects/eclipse.pde)
  describes PDE components including UI, API Tools, Build, Incubator, and Doc.
- The [official PDE repository](https://github.com/eclipse-pde/eclipse.pde)
  is public and identifies EPL-2.0. Repository contents and file-level notices
  still need review before redistribution.
- PDE product/component names and historical Bugzilla activity could not be
  verified while the Bugzilla service was returning its maintenance page.

## Licensing and privacy decision

- EPL-2.0 evidence applies to the cited Eclipse source repositories, subject to
  per-file headers and NOTICE files.
- No applicable license for Bugzilla bug text, activity records, or personal
  identifiers was established by this probe. The repository's MIT license does
  not grant rights to those external records.
- Comments remain excluded from the initial collection as approved. Before
  collecting or redistributing Bugzilla records, document the applicable
  service terms, privacy constraints, and any access restrictions. Keep raw
  identifiers out of published artifacts unless a permitted research use is
  established.

## Collection gate

Do not begin bulk Platform/PDE Bugzilla collection until the REST endpoints
return valid JSON and the product/component set and historical activity API are
verified. Then validate the component-to-repository mapping against the SDK
aggregator and project metadata. If the outage persists, use an alternate
archive only after its provenance, completeness, terms, and approval are
confirmed. Keep Platform, PDE, and each repository's raw data separate.

## PowerShell probe command

Run from the repository root to repeat the four small, read-only requests. The
minimal bug queries request only IDs and product/component names; they do not
request summaries, comments, or user identities.

```powershell
$urls = @(
    'https://bugs.eclipse.org/bugs/rest/product/Platform',
    'https://bugs.eclipse.org/bugs/rest/product/PDE',
    'https://bugs.eclipse.org/bugs/rest/bug?product=Platform&limit=1&include_fields=id,product,component',
    'https://bugs.eclipse.org/bugs/rest/bug?product=PDE&limit=1&include_fields=id,product,component'
)
foreach ($url in $urls) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 25
        $shutdown = $response.Content -match 'temporarily shutdown'
        '{0} status={1} shutdown_page={2} content_type={3}' -f `
            $url, $response.StatusCode, $shutdown, $response.Headers['Content-Type']
    }
    catch {
        '{0} error={1}' -f $url, $_.Exception.Message
    }
}
```
